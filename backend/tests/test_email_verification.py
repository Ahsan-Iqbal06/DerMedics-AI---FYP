import re

from app.services.email import DEV_OUTBOX
from tests.conftest import PASSWORD

SIGNUP = {"full_name": "Sara Khan", "phone": "03001234567", "password": PASSWORD, "confirm_password": PASSWORD,
          "accept_terms": True}


def latest_code(email: str, subject_word: str = "Confirm") -> str:
    msg = next(m for m in reversed(DEV_OUTBOX) if m["to"] == email and subject_word in m["subject"])
    return re.search(r"\b(\d{6})\b", msg["text"]).group(1)


def test_signup_needs_the_emailed_code_before_sign_in(client):
    r = client.post("/api/auth/register", json={**SIGNUP, "email": "sara@example.com"})
    assert r.status_code == 201 and "access_token" not in r.json()
    code = latest_code("sara@example.com")

    r = client.post("/api/auth/login", json={"email": "sara@example.com", "password": PASSWORD})
    assert r.status_code == 403 and r.headers["x-error-code"] == "email_not_verified"

    bad = client.post("/api/auth/verify-email", json={"email": "sara@example.com", "password": PASSWORD,
                                                       "code": "000000" if code != "000000" else "111111"})
    assert bad.status_code == 400 and "attempts left" in bad.json()["detail"]
    r = client.post("/api/auth/verify-email", json={"email": "sara@example.com", "password": PASSWORD, "code": code})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "sara@example.com", "password": PASSWORD}).status_code == 200


def test_code_alone_is_not_enough_without_the_password(client):
    client.post("/api/auth/register", json={**SIGNUP, "email": "nopass@example.com"})
    code = latest_code("nopass@example.com")
    r = client.post("/api/auth/verify-email", json={"email": "nopass@example.com", "password": "Wr0ng!Pass", "code": code})
    assert r.status_code == 401


def test_squatted_unverified_email_can_be_reclaimed_by_its_owner(client):
    # Someone signs up with an address they don't own and never verifies it...
    client.post("/api/auth/register", json={**SIGNUP, "email": "owner@example.com", "password": "Squ4tter!Pass",
                                            "confirm_password": "Squ4tter!Pass"})
    # ...the real owner can still sign up; the squatter's code and password no longer work.
    squatter_code = latest_code("owner@example.com")
    r = client.post("/api/auth/register", json={**SIGNUP, "email": "owner@example.com"})
    assert r.status_code == 201
    assert client.post("/api/auth/verify-email", json={"email": "owner@example.com", "password": "Squ4tter!Pass",
                                                        "code": squatter_code}).status_code == 401
    r = client.post("/api/auth/verify-email", json={"email": "owner@example.com", "password": PASSWORD,
                                                     "code": latest_code("owner@example.com")})
    assert r.status_code == 200
    # Once verified, the address is taken.
    assert client.post("/api/auth/register", json={**SIGNUP, "email": "owner@example.com"}).status_code == 409


def test_resend_and_signup_code_cannot_reset_password(client):
    client.post("/api/auth/register", json={**SIGNUP, "email": "resend.v@example.com"})
    assert client.post("/api/auth/resend-verification", json={"email": "resend.v@example.com"}).status_code == 202
    assert client.post("/api/auth/resend-verification", json={"email": "ghost@example.com"}).status_code == 404
    code = latest_code("resend.v@example.com")
    r = client.post("/api/auth/verify-reset-code", json={"email": "resend.v@example.com", "code": code})
    assert r.status_code == 400  # a sign-up code is not a password-reset code


def test_password_reset_also_verifies_the_email(client):
    client.post("/api/auth/register", json={**SIGNUP, "email": "via.reset@example.com"})
    client.post("/api/auth/forgot-password", json={"email": "via.reset@example.com"})
    token = client.post("/api/auth/verify-reset-code", json={
        "email": "via.reset@example.com", "code": latest_code("via.reset@example.com", "reset")}).json()["reset_token"]
    new = "N3w!Passw0rd"
    assert client.post("/api/auth/reset-password", json={"reset_token": token, "new_password": new,
                                                         "confirm_password": new}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "via.reset@example.com", "password": new}).status_code == 200
