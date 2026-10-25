from tests.conftest import register, skin_image


def analyze(client, auth, data, consent="true"):
    return client.post(
        "/api/analysis",
        headers=auth,
        files={"image": ("skin.jpg", data, "image/jpeg")},
        data={"body_area": "Face / neck", "symptoms": "Redness", "consent": consent},
    )


def test_full_pipeline_confident(client, auth):
    r = analyze(client, auth, skin_image())
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["status"] == "ai"
    assert a["is_demo"] is True
    assert a["confidence"] >= 0.6
    assert a["description"]["overview"]
    assert a["medicines"], "medicine suggestions expected for confident result"
    assert a["dermatologists"], "dermatologist recommendations expected"
    assert a["dermatologists"][0]["city"] == "Abbottabad"
    assert a["llm_source"] == "knowledge_base"

    # Same photo -> same demo prediction
    assert analyze(client, auth, skin_image()).json()["predicted_label"] == a["predicted_label"]


def test_blurry_flat_image_is_inconclusive(client, auth):
    a = analyze(client, auth, skin_image(flat=True)).json()
    assert a["status"] == "inconclusive"
    assert a["medicines"] == []
    assert a["description"] is None


def test_requires_consent_and_valid_image(client, auth):
    assert analyze(client, auth, skin_image(), consent="false").status_code == 400
    assert analyze(client, auth, b"not an image").status_code == 422
    assert analyze(client, auth, skin_image(size=50)).status_code == 422


def test_reports_flow_and_pdf(client, auth):
    a = analyze(client, auth, skin_image()).json()
    inc = analyze(client, auth, skin_image(flat=True)).json()

    r = client.post("/api/reports", headers=auth, json={"analysis_id": a["id"], "subject_type": "myself"})
    assert r.status_code == 201, r.text
    assert r.json()["subject_name"] == "Hasnain Iqbal"

    bad = client.post("/api/reports", headers=auth, json={"analysis_id": inc["id"], "subject_type": "someone_else"})
    assert bad.status_code == 422
    r2 = client.post(
        "/api/reports",
        headers=auth,
        json={"analysis_id": inc["id"], "subject_type": "someone_else", "subject_name": "Ahmed Iqbal",
              "subject_age": 15, "relationship": "Sibling", "health_notes": "No allergies"},
    )
    assert r2.status_code == 201

    assert len(client.get("/api/reports", headers=auth).json()) == 2
    statuses = [i["status"] for i in client.get("/api/reports?filter=inconclusive", headers=auth).json()]
    assert statuses == ["inconclusive"]
    assert len(client.get("/api/reports?q=ahmed", headers=auth).json()) == 1

    pdf = client.get(f"/api/reports/{r.json()['id']}/pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    dash = client.get("/api/dashboard", headers=auth).json()
    assert dash["analyses_count"] == 2 and dash["reports_count"] == 2
    assert dash["recent_activity"]


def test_reports_are_private(client, auth):
    a = analyze(client, auth, skin_image()).json()
    rid = client.post("/api/reports", headers=auth, json={"analysis_id": a["id"], "subject_type": "myself"}).json()["id"]
    other = register(client, email="other@example.com")
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/reports/{rid}", headers=h).status_code == 404
    assert client.get(f"/api/analysis/{a['id']}", headers=h).status_code == 404


def test_dermatologist_search(client, auth):
    res = client.get("/api/dermatologists?city=Lahore", headers=auth).json()
    assert res[0]["city"] == "Lahore"
    res = client.get("/api/dermatologists?city=Karachi&condition=psoriasis", headers=auth).json()
    assert res[0]["name"] == "Dr. Nida Hussain"
    res = client.get("/api/dermatologists?lat=33.70&lng=73.04", headers=auth).json()
    assert res[0]["city"] == "Islamabad" and res[0]["distance_km"] < 5
