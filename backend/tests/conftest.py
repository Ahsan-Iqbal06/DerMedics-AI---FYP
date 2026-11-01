import io
import os
import re
import tempfile

_tmp = tempfile.mkdtemp(prefix="dermedics-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["LLM_API_KEY"] = ""
os.environ["MODEL_PATH"] = ""
os.environ["GOOGLE_PLACES_KEY"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["JWT_SECRET"] = "test-only-secret-0123456789abcdefghijklmnopqrstuvwxyz"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.core.security import (  # noqa: E402
    analysis_rate_limiter,
    auth_rate_limiter,
    login_guard,
    refresh_rate_limiter,
    reset_rate_limiter,
)
from app.main import app  # noqa: E402
from app.services.email import DEV_OUTBOX  # noqa: E402
from seed import seed  # noqa: E402

seed()

PASSWORD = "Str0ng!Pass"


@pytest.fixture(autouse=True)
def _reset_limiter():
    for limiter in (auth_rate_limiter, reset_rate_limiter, refresh_rate_limiter, analysis_rate_limiter, login_guard):
        limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def register(client, email="hasnain@example.com", city="Abbottabad"):
    r = client.post(
        "/api/auth/register",
        json={
            "full_name": "Hasnain Iqbal",
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "phone": "0300 123 4567",
            "country": "Pakistan",
            "city": city,
            "accept_terms": True,
        },
    )
    assert r.status_code == 201, r.text
    # Activate the account with the emailed code, which also signs in.
    msg = next(m for m in reversed(DEV_OUTBOX) if m["to"] == email.lower())
    code = re.search(r"\b(\d{6})\b", msg["text"]).group(1)
    r = client.post("/api/auth/verify-email", json={"email": email, "password": PASSWORD, "code": code})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def auth(client):
    tokens = register(client, email=f"user{os.urandom(4).hex()}@example.com")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def skin_image(fmt="JPEG", size=400, flat=False) -> bytes:
    img = Image.new("RGB", (size, size), (205, 150, 130))
    if not flat:
        d = ImageDraw.Draw(img)
        for i in range(0, size, 23):
            d.ellipse((i, (i * 7) % size, i + 18, (i * 7) % size + 18), fill=(170, 60, 60))
            d.line((0, i, size, (i * 3) % size), fill=(120, 90, 80), width=2)
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def auth_headers_for(client, email: str) -> dict:
    tokens = register(client, email=email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
