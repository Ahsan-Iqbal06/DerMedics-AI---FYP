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
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models import RefreshToken, User
from app.schemas import (
    ChangePasswordIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserOut,
    UserUpdate,
)
from app.services.classifier import InvalidImageError, load_image

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


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
