import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, read_upload
from app.core.config import get_settings
from app.core.security import (
    DUMMY_HASH,
    auth_rate_limiter,
    create_access_token,
    create_reset_token,
    decode_reset_token,
    hash_password,
    login_guard,
    refresh_rate_limiter,
    hash_refresh_token,
    new_refresh_token,
    reset_code_hash,
    reset_rate_limiter,
    verify_password,
)
from app.db.session import get_db
from app.models import PasswordReset, RefreshToken, User
from app.schemas import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    ResetTokenOut,
    TokenOut,
    UserOut,
    UserUpdate,
    VerifyEmailIn,
    VerifyResetCodeIn,
)
from app.services.classifier import InvalidImageError, load_image
from app.services.email import send_reset_code, send_verification_code

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


def _issue_tokens(db: Session, user: User) -> TokenOut:
    s = get_settings()
    raw, hashed = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(UTC) + timedelta(days=s.refresh_token_days),
        )
    )
    db.commit()
    return TokenOut(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=raw,
        expires_in=s.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=MessageOut, status_code=201, dependencies=[Depends(auth_rate_limiter)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Creates the account and emails a code; the account can sign in once /verify-email confirms it."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.email_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    if user is None:
        user = User(email=body.email)
        db.add(user)
    # An unverified account may be someone else typing this address: the latest sign-up replaces it, and only the
    # person who knows its password AND reads the inbox can activate it.
    user.full_name = body.full_name
    user.phone = body.phone
    user.password_hash = hash_password(body.password)
    user.country = body.country.strip() or "Pakistan"
    user.city = body.city.strip()
    db.commit()
    db.refresh(user)
    _send_code(db, user, "verify", force=True)
    return MessageOut(message=f"We've sent a 6-digit code to {user.email}. Enter it to activate your account.")


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limiter)])
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    login_guard.check(email)
    user = db.scalar(select(User).where(User.email == email))
    # Always run a hash verification so response time doesn't reveal whether the email exists.
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        login_guard.failed(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    login_guard.succeeded(email)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")
    if not user.email_verified:
        _send_code(db, user, "verify")
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"Please verify your email first. We've sent a 6-digit code to {user.email}.",
                            headers={"X-Error-Code": NOT_VERIFIED})
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(refresh_rate_limiter)])
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if token.revoked:
        # Reuse of a rotated token suggests theft: revoke every session of this user.
        db.execute(update(RefreshToken).where(RefreshToken.user_id == token.user_id).values(revoked=True))
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please sign in again")
    expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please sign in again")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or disabled")
    token.revoked = True
    return _issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    if token:
        token.revoked = True
        db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(user)
    return user


AVATAR_SIZE = 512


def _avatar_dir():
    d = get_settings().upload_dir / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _remove_avatar_file(user: User) -> None:
    if user.avatar_path:
        (_avatar_dir() / user.avatar_path).unlink(missing_ok=True)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    image: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        img = load_image(await read_upload(image))
    except InvalidImageError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e))
    # Centre-crop to a square and store a small JPEG; the original upload is not kept.
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((AVATAR_SIZE, AVATAR_SIZE))
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(_avatar_dir() / name, "JPEG", quality=88)
    _remove_avatar_file(user)
    user.avatar_path = name
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _remove_avatar_file(user)
    user.avatar_path = None
    db.commit()
    db.refresh(user)
    return user


# ---------- One-time email codes: sign-up verification and forgot password ----------

CODE_MAX_ATTEMPTS = 5
CODE_RESEND_SECONDS = 60
CODES_PER_HOUR = 5  # with 5 guesses per code, at most 25 guesses an hour against a 1-in-a-million code
NOT_REGISTERED_MESSAGE = "No account is registered with this email. Check the spelling or create an account."
NOT_VERIFIED = "email_not_verified"  # sent as the X-Error-Code header so the app can open the code screen


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:3]}***@{domain}"


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _send_code(db: Session, user: User, purpose: str, force: bool = False) -> None:
    """Emails a fresh 6-digit code; older codes for the same purpose stop working. Within 60 s of the last code
    nothing new is sent (that code is still valid) unless `force` is set."""
    s = get_settings()
    now = datetime.now(UTC)
    latest = db.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.purpose == purpose)
        .order_by(PasswordReset.id.desc())
    )
    if not force and latest and not latest.consumed and now - _aware(latest.created_at) < timedelta(seconds=CODE_RESEND_SECONDS):
        log.info("%s code for %s: already sent less than %ss ago", purpose, _mask(user.email), CODE_RESEND_SECONDS)
        return
    recent = db.scalar(select(func.count()).select_from(PasswordReset).where(
        PasswordReset.user_id == user.id, PasswordReset.purpose == purpose,
        PasswordReset.created_at > now - timedelta(hours=1)))
    if recent >= CODES_PER_HOUR:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many codes requested for this account. Please try again in an hour.")
    db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.purpose == purpose,
                                           PasswordReset.consumed.is_(False)).values(consumed=True))
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PasswordReset(
        user_id=user.id,
        purpose=purpose,
        code_hash=reset_code_hash(user.id, code, purpose),
        expires_at=now + timedelta(minutes=s.password_reset_minutes),
        created_at=now,
    ))
    db.commit()
    send = send_verification_code if purpose == "verify" else send_reset_code
    try:
        send(user.email, user.full_name.split(" ")[0], code, s.password_reset_minutes)
    except Exception:
        log.exception("Could not send %s email", purpose)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "We couldn't send the email right now. Please try again in a minute.")
    log.info("%s code sent to %s", purpose, _mask(user.email))


def _check_code(db: Session, user: User | None, purpose: str, code: str) -> PasswordReset:
    """Returns the matching unused code, or raises; each code allows 5 wrong guesses."""
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "That code is invalid or has expired. Request a new one.")
    if user is None:
        raise invalid
    entry = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.purpose == purpose, PasswordReset.consumed.is_(False))
        .order_by(PasswordReset.id.desc())
    )
    if entry is None or _aware(entry.expires_at) < datetime.now(UTC):
        raise invalid
    if entry.attempts >= CODE_MAX_ATTEMPTS:
        entry.consumed = True
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many incorrect attempts. Request a new code.")
    if not hmac.compare_digest(entry.code_hash, reset_code_hash(user.id, code, purpose)):
        entry.attempts += 1
        left = CODE_MAX_ATTEMPTS - entry.attempts
        if left == 0:
            entry.consumed = True
        db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Incorrect code. {left} attempt{'s' if left != 1 else ''} left." if left else
            "Too many incorrect attempts. Request a new code.",
        )
    return entry


@router.post("/verify-email", response_model=TokenOut, dependencies=[Depends(reset_rate_limiter)])
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_db)):
    """Activates a new account with the emailed code and signs the user in."""
    user = db.scalar(select(User).where(User.email == body.email))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if user.email_verified:
        return _issue_tokens(db, user)  # e.g. the code was entered twice; just sign in
    entry = _check_code(db, user, "verify", body.code)
    entry.consumed = True
    entry.verified_at = datetime.now(UTC)
    user.email_verified = True
    user.last_login_at = datetime.now(UTC)
    db.commit()
    log.info("Email verified for %s", _mask(user.email))
    return _issue_tokens(db, user)


@router.post("/resend-verification", response_model=MessageOut, status_code=202,
             dependencies=[Depends(reset_rate_limiter)])
def resend_verification(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_REGISTERED_MESSAGE)
    if user.email_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "This email is already verified. Please sign in.")
    _send_code(db, user, "verify")
    return MessageOut(message=f"We've sent a 6-digit code to {user.email}.")


@router.post("/forgot-password", response_model=MessageOut, status_code=202,
             dependencies=[Depends(reset_rate_limiter)])
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    """Emails a one-time code to the account's registered address. Rate-limited per IP and per account."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        log.info("Password reset requested for %s: no account with this email", _mask(body.email))
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_REGISTERED_MESSAGE)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")
    _send_code(db, user, "reset")
    return MessageOut(message=f"We've sent a 6-digit code to {user.email}.")


@router.post("/verify-reset-code", response_model=ResetTokenOut, dependencies=[Depends(reset_rate_limiter)])
def verify_reset_code(body: VerifyResetCodeIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    entry = _check_code(db, user, "reset", body.code)
    entry.verified_at = datetime.now(UTC)
    db.commit()
    return ResetTokenOut(reset_token=create_reset_token(user.id, entry.id))


@router.post("/reset-password", status_code=204, dependencies=[Depends(reset_rate_limiter)])
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    user_id, reset_id = decode_reset_token(body.reset_token)
    reset = db.get(PasswordReset, reset_id)
    if reset is None or reset.user_id != user_id or reset.consumed or reset.verified_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset has already been used. Request a new code.")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Account not found or disabled")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    user.email_verified = True  # the emailed code proved they own the address
    reset.consumed = True
    # Sign out everywhere: whoever knew the old password loses access.
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()


@router.post("/change-password", status_code=204, dependencies=[Depends(auth_rate_limiter)])
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
