import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import (
    DUMMY_HASH,
    auth_rate_limiter,
    create_access_token,
    create_reset_token,
    decode_reset_token,
    hash_password,
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
    VerifyResetCodeIn,
)
from app.services.classifier import InvalidImageError, load_image
from app.services.email import send_reset_code

router = APIRouter(prefix="/auth", tags=["auth"])


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
        access_token=create_access_token(user.id),
        refresh_token=raw,
        expires_in=s.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(auth_rate_limiter)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(
        full_name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        country=body.country.strip() or "Pakistan",
        city=body.city.strip(),
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limiter)])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Always run a hash verification so response time doesn't reveal whether the email exists.
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
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
        img = load_image(await image.read())
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


# ---------- Forgot password: email code -> verify -> new password ----------

RESET_MAX_ATTEMPTS = 5
RESET_RESEND_SECONDS = 60
GENERIC_RESET_MESSAGE = "If an account exists for this email, we've sent a 6-digit code to it."


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


@router.post("/forgot-password", response_model=MessageOut, status_code=202, dependencies=[Depends(reset_rate_limiter)])
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    """Emails a one-time code. Always answers the same way, so it can't be used to discover accounts."""
    s = get_settings()
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not user.is_active:
        return MessageOut(message=GENERIC_RESET_MESSAGE)
    latest = db.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user.id).order_by(PasswordReset.id.desc())
    )
    if latest and not latest.consumed and datetime.now(UTC) - _aware(latest.created_at) < timedelta(seconds=RESET_RESEND_SECONDS):
        return MessageOut(message=GENERIC_RESET_MESSAGE)  # a code was sent moments ago
    # Only the newest code is valid.
    db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.consumed.is_(False))
               .values(consumed=True))
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PasswordReset(
        user_id=user.id,
        code_hash=reset_code_hash(user.id, code),
        expires_at=datetime.now(UTC) + timedelta(minutes=s.password_reset_minutes),
        created_at=datetime.now(UTC),
    ))
    db.commit()
    send_reset_code(user.email, user.full_name.split(" ")[0], code, s.password_reset_minutes)
    return MessageOut(message=GENERIC_RESET_MESSAGE)


@router.post("/verify-reset-code", response_model=ResetTokenOut, dependencies=[Depends(reset_rate_limiter)])
def verify_reset_code(body: VerifyResetCodeIn, db: Session = Depends(get_db)):
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "That code is invalid or has expired. Request a new one.")
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise invalid
    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.consumed.is_(False))
        .order_by(PasswordReset.id.desc())
    )
    if reset is None or _aware(reset.expires_at) < datetime.now(UTC):
        raise invalid
    if reset.attempts >= RESET_MAX_ATTEMPTS:
        reset.consumed = True
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many incorrect attempts. Request a new code.")
    if not hmac.compare_digest(reset.code_hash, reset_code_hash(user.id, body.code)):
        reset.attempts += 1
        left = RESET_MAX_ATTEMPTS - reset.attempts
        if left == 0:
            reset.consumed = True
        db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Incorrect code. {left} attempt{'s' if left != 1 else ''} left." if left else
            "Too many incorrect attempts. Request a new code.",
        )
    reset.verified_at = datetime.now(UTC)
    db.commit()
    return ResetTokenOut(reset_token=create_reset_token(user.id, reset.id))


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
    reset.consumed = True
    # Sign out everywhere: whoever knew the old password loses access.
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
