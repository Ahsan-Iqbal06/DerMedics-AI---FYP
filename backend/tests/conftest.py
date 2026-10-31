import io
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="dermedics-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["LLM_API_KEY"] = ""
os.environ["MODEL_PATH"] = ""
os.environ["GOOGLE_PLACES_KEY"] = ""
os.environ["SMTP_HOST"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.core.security import auth_rate_limiter, reset_rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from seed import seed  # noqa: E402

seed()

PASSWORD = "Str0ng!Pass"


@pytest.fixture(autouse=True)
def _reset_limiter():
    auth_rate_limiter.reset()
    reset_rate_limiter.reset()


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
            "country": "Pakistan",
            "city": city,
            "accept_terms": True,
        },
    )
    assert r.status_code == 201, r.text
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
