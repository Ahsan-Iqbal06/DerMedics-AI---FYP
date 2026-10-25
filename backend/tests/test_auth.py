from tests.conftest import PASSWORD, register, skin_image


def test_register_login_me_refresh_logout(client):
    tokens = register(client, email="Flow@Example.com")
    assert tokens["user"]["email"] == "flow@example.com"

    r = client.post("/api/auth/login", json={"email": "flow@example.com", "password": PASSWORD})
    assert r.status_code == 200
    access, refresh = r.json()["access_token"], r.json()["refresh_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200 and me.json()["full_name"] == "Hasnain Iqbal"

    r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    new_refresh = r2.json()["refresh_token"]

    # Reusing a rotated refresh token revokes every session.
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": new_refresh}).status_code == 401


def test_logout_revokes_refresh(client):
    tokens = register(client, email="logout@example.com")
    assert client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_duplicate_email_rejected(client):
    register(client, email="dup@example.com")
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Someone", "email": "DUP@example.com", "password": PASSWORD,
              "confirm_password": PASSWORD, "accept_terms": True},
    )
    assert r.status_code == 409


def test_weak_password_and_mismatch(client):
    base = {"full_name": "Ali Khan", "email": "weak@example.com", "accept_terms": True}
    r = client.post("/api/auth/register", json={**base, "password": "password", "confirm_password": "password"})
    assert r.status_code == 422 and "uppercase" in r.json()["detail"]
    r = client.post("/api/auth/register", json={**base, "password": PASSWORD, "confirm_password": PASSWORD + "x"})
    assert r.status_code == 422 and "do not match" in r.json()["detail"]


def test_wrong_password_and_unknown_email_same_error(client):
    register(client, email="known@example.com")
    a = client.post("/api/auth/login", json={"email": "known@example.com", "password": "Wrong!Pass1"})
    b = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong!Pass1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_login_rate_limited(client):
    codes = [
        client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"}).status_code
        for _ in range(6)
    ]
    assert codes[-1] == 429


def test_change_password_revokes_sessions(client):
    tokens = register(client, email="change@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/api/auth/change-password", headers=h,
                    json={"current_password": PASSWORD, "new_password": "N3w!Password"})
    assert r.status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "change@example.com", "password": "N3w!Password"}).status_code == 200


def test_protected_routes_require_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/reports").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_avatar_upload_and_remove(client):
    tokens = register(client, email="avatar@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert tokens["user"]["avatar_url"] is None

    r = client.post("/api/auth/me/avatar", headers=h, files={"image": ("me.png", skin_image("PNG", size=600), "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url.startswith("/uploads/avatars/") and url.endswith(".jpg")
    assert client.get(url).status_code == 200
    assert client.get("/api/auth/me", headers=h).json()["avatar_url"] == url

    bad = client.post("/api/auth/me/avatar", headers=h, files={"image": ("x.txt", b"nope", "text/plain")})
    assert bad.status_code == 422

    r = client.delete("/api/auth/me/avatar", headers=h)
    assert r.status_code == 200 and r.json()["avatar_url"] is None
    assert client.get(url).status_code == 404
