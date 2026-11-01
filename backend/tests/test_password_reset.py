import re

from app.services.email import DEV_OUTBOX
from tests.conftest import PASSWORD, register

NEW_PASSWORD = "Br4nd!NewPass"


def last_code(email: str) -> str:
    msg = next(m for m in reversed(DEV_OUTBOX) if m["to"] == email)
    return re.search(r"\b(\d{6})\b", msg["text"]).group(1)


def test_full_reset_flow(client):
    tokens = register(client, email="forgot@example.com")
    r = client.post("/api/auth/forgot-password", json={"email": "Forgot@Example.com"})
    assert r.status_code == 202
    code = last_code("forgot@example.com")

    r = client.post("/api/auth/verify-reset-code", json={"email": "forgot@example.com", "code": code})
    assert r.status_code == 200, r.text
    reset_token = r.json()["reset_token"]

    r = client.post("/api/auth/reset-password",
                    json={"reset_token": reset_token, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
    assert r.status_code == 204, r.text

    # Old password no longer works, new one does, and old sessions were signed out.
    assert client.post("/api/auth/login", json={"email": "forgot@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "forgot@example.com", "password": NEW_PASSWORD}).status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401

    # A reset can only be used once.
    r = client.post("/api/auth/reset-password",
                    json={"reset_token": reset_token, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
    assert r.status_code == 400


def test_unknown_email_is_rejected_and_no_email_sent(client):
    before = len(DEV_OUTBOX)
    r = client.post("/api/auth/forgot-password", json={"email": "nobody-here@example.com"})
    assert r.status_code == 404 and "No account" in r.json()["detail"]
    assert len(DEV_OUTBOX) == before


def test_code_goes_to_each_users_own_email(client):
    register(client, email="first.user@example.com")
    register(client, email="second.user@example.com")
    r = client.post("/api/auth/forgot-password", json={"email": "Second.User@example.com"})
    assert r.status_code == 202 and "second.user@example.com" in r.json()["message"]
    assert not any(m["to"] == "first.user@example.com" and "reset" in m["subject"] for m in DEV_OUTBOX)
    code = last_code("second.user@example.com")
    # The code only works for the account it was sent to.
    assert client.post("/api/auth/verify-reset-code",
                       json={"email": "first.user@example.com", "code": code}).status_code == 400
    assert client.post("/api/auth/verify-reset-code",
                       json={"email": "second.user@example.com", "code": code}).status_code == 200


def test_register_saves_phone_and_rejects_bad_numbers(client):
    tokens = register(client, email="phone.user@example.com")
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    assert me["phone"] == "03001234567"
    r = client.post("/api/auth/register", json={
        "full_name": "Bad Phone", "email": "bad.phone@example.com", "password": PASSWORD,
        "confirm_password": PASSWORD, "phone": "12ab", "accept_terms": True})
    assert r.status_code == 422 and "phone" in r.json()["detail"]


def test_wrong_code_attempts_are_limited(client):
    register(client, email="attempts@example.com")
    client.post("/api/auth/forgot-password", json={"email": "attempts@example.com"})
    code = last_code("attempts@example.com")
    wrong = "000000" if code != "000000" else "111111"
    for left in (4, 3, 2, 1):
        r = client.post("/api/auth/verify-reset-code", json={"email": "attempts@example.com", "code": wrong})
        assert r.status_code == 400 and f"{left} attempt" in r.json()["detail"]
    r = client.post("/api/auth/verify-reset-code", json={"email": "attempts@example.com", "code": wrong})
    assert "Too many" in r.json()["detail"]
    # Even the right code is now refused; a new code is needed.
    assert client.post("/api/auth/verify-reset-code",
                       json={"email": "attempts@example.com", "code": code}).status_code == 400


def test_weak_or_mismatched_new_password_rejected(client):
    register(client, email="weaknew@example.com")
    client.post("/api/auth/forgot-password", json={"email": "weaknew@example.com"})
    token = client.post("/api/auth/verify-reset-code",
                        json={"email": "weaknew@example.com", "code": last_code("weaknew@example.com")}).json()["reset_token"]
    r = client.post("/api/auth/reset-password", json={"reset_token": token, "new_password": "short", "confirm_password": "short"})
    assert r.status_code == 422
    r = client.post("/api/auth/reset-password",
                    json={"reset_token": token, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD + "x"})
    assert r.status_code == 422 and "do not match" in r.json()["detail"]


def test_bad_code_format_and_forged_token(client):
    r = client.post("/api/auth/verify-reset-code", json={"email": "x@example.com", "code": "12ab"})
    assert r.status_code == 422
    r = client.post("/api/auth/reset-password",
                    json={"reset_token": "not-a-token", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
    assert r.status_code == 400


def test_resend_is_rate_limited_per_user(client):
    register(client, email="resend@example.com")
    client.post("/api/auth/forgot-password", json={"email": "resend@example.com"})
    first = last_code("resend@example.com")
    count = sum(m["to"] == "resend@example.com" for m in DEV_OUTBOX)
    client.post("/api/auth/forgot-password", json={"email": "resend@example.com"})  # within 60 s
    assert sum(m["to"] == "resend@example.com" for m in DEV_OUTBOX) == count
    assert last_code("resend@example.com") == first
