from app.services.email import DEV_OUTBOX
from tests.conftest import PASSWORD, auth_headers_for, register, skin_image


def test_skin_photos_are_private_to_their_owner(client):
    owner = auth_headers_for(client, "photo.owner@example.com")
    other = auth_headers_for(client, "photo.other@example.com")
    r = client.post("/api/analysis", headers=owner, data={"consent": "true"},
                    files={"image": ("skin.jpg", skin_image(), "image/jpeg")})
    assert r.status_code == 201, r.text
    url = r.json()["image_url"]
    assert url.startswith("/api/files/analyses/")
    assert client.get(url, headers=owner).status_code == 200
    assert client.get(url, headers=other).status_code == 404
    assert client.get(url).status_code == 401
    assert client.get("/uploads/" + url.rsplit("/", 1)[1]).status_code == 404  # no public folder any more
    assert client.get("/api/files/analyses/..%2F..%2F.env", headers=owner).status_code == 404


def test_password_change_signs_out_existing_access_tokens(client):
    tokens = register(client, email="version@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/api/auth/change-password", headers=h,
                    json={"current_password": PASSWORD, "new_password": "An0ther!Pass"})
    assert r.status_code == 204
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_account_locks_after_repeated_wrong_passwords(client):
    from app.core.security import auth_rate_limiter
    register(client, email="lock@example.com")
    for _ in range(10):
        auth_rate_limiter.reset()  # simulate attempts spread over many IPs
        assert client.post("/api/auth/login", json={"email": "lock@example.com", "password": "Wrong!Pass1"}).status_code == 401
    auth_rate_limiter.reset()
    r = client.post("/api/auth/login", json={"email": "lock@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_reset_codes_are_capped_per_hour(client):
    from datetime import UTC, datetime, timedelta

    from app.db.session import SessionLocal
    from app.models import PasswordReset
    from app.core.security import reset_rate_limiter
    register(client, email="cap@example.com")
    for _ in range(5):
        reset_rate_limiter.reset()
        assert client.post("/api/auth/forgot-password", json={"email": "cap@example.com"}).status_code == 202
        with SessionLocal() as db:  # skip the 60 s resend wait
            for row in db.query(PasswordReset).all():
                row.created_at = row.created_at - timedelta(seconds=61) if row.created_at else datetime.now(UTC)
            db.commit()
    r = client.post("/api/auth/forgot-password", json={"email": "cap@example.com"})
    assert r.status_code == 429


def test_email_escapes_names(client):
    from app.services.email import send_reset_code
    send_reset_code("x@example.com", '<a href="https://evil.example">Click</a>', "123456", 15)
    assert DEV_OUTBOX[-1]["to"] == "x@example.com"


def test_pdf_handles_markup_in_user_text(client):
    h = auth_headers_for(client, "pdf.markup@example.com")
    a = client.post("/api/analysis", headers=h, data={"consent": "true", "symptoms": "itchy <b unclosed & red"},
                    files={"image": ("skin.jpg", skin_image(), "image/jpeg")}).json()
    rep = client.post("/api/reports", headers=h, json={
        "analysis_id": a["id"], "subject_type": "someone_else", "subject_name": "Ali <i>", "subject_age": 30,
        "relationship": "Brother", "health_notes": "<font size=999>"}).json()
    r = client.get(f"/api/reports/{rep['id']}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"
