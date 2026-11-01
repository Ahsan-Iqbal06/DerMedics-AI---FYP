import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_hasher = PasswordHasher()

PASSWORD_RULES = [
    (r".{8,}", "at least 8 characters"),
    (r"[A-Z]", "an uppercase letter"),
    (r"[a-z]", "a lowercase letter"),
    (r"\d", "a number"),
    (r"[^A-Za-z0-9]", "a special character"),
]


def password_problems(password: str) -> list[str]:
    return [msg for pattern, msg in PASSWORD_RULES if not re.search(pattern, password)]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# A valid hash to verify against when the user doesn't exist, so login timing doesn't leak which emails are registered.
DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


DEFAULT_SECRET = "change-me-to-a-long-random-string"


def check_secret() -> None:
    """Refuse to start with a guessable signing key: anyone who knows it can forge sign-in tokens."""
    secret = get_settings().jwt_secret
    if secret == DEFAULT_SECRET or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET in backend/.env must be a random string of at least 32 characters. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )


def create_access_token(user_id: int, version: int = 0) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "ver": version,  # bumped on password change/reset, which invalidates older access tokens
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> tuple[int, int]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return int(payload["sub"]), int(payload.get("ver", 0))


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw token for the client, sha256 hash to store)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class RateLimiter:
    """Simple in-memory sliding-window limiter keyed by client IP."""

    def __init__(self, max_calls: int, per_seconds: int):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.calls[key]
        while window and now - window[0] > self.per_seconds:
            window.popleft()
        if len(window) >= self.max_calls:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many attempts. Please wait a minute and try again.",
            )
        window.append(now)

    def reset(self) -> None:
        self.calls.clear()


class LoginGuard:
    """Locks an email after repeated wrong passwords, whichever IPs they come from (the IP limiter alone can be
    spread across many addresses)."""

    def __init__(self, max_failures: int = 10, lock_seconds: int = 15 * 60):
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self.failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, email: str) -> deque[float]:
        window = self.failures[email]
        now = time.monotonic()
        while window and now - window[0] > self.lock_seconds:
            window.popleft()
        return window

    def check(self, email: str) -> None:
        if len(self._recent(email)) >= self.max_failures:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many incorrect attempts for this account. Try again in 15 minutes or reset your password.",
            )

    def failed(self, email: str) -> None:
        self._recent(email).append(time.monotonic())

    def succeeded(self, email: str) -> None:
        self.failures.pop(email, None)

    def reset(self) -> None:
        self.failures.clear()


login_guard = LoginGuard()
auth_rate_limiter = RateLimiter(max_calls=5, per_seconds=60)
refresh_rate_limiter = RateLimiter(max_calls=30, per_seconds=60)
# Each analysis runs the model and a paid LLM call.
analysis_rate_limiter = RateLimiter(max_calls=10, per_seconds=60)
# Covers forgot + verify + reset together; wrong codes are separately capped at 5 per code.
reset_rate_limiter = RateLimiter(max_calls=10, per_seconds=60)


def reset_code_hash(user_id: int, code: str, purpose: str = "reset") -> str:
    """Keyed hash of an emailed code, so a leaked database can't be brute-forced offline. The purpose is mixed in,
    so a sign-up code can never be used as a password-reset code."""
    s = get_settings()
    return hmac.new(s.jwt_secret.encode(), f"{purpose}:{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def create_reset_token(user_id: int, reset_id: int) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "rid": reset_id, "type": "reset", "iat": now, "exp": now + timedelta(minutes=10)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_reset_token(token: str) -> tuple[int, int]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link has expired. Please request a new code.")
    if payload.get("type") != "reset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token")
    return int(payload["sub"]), int(payload["rid"])
