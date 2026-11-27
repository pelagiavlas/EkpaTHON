from scripts.pdfgen import build_image_only_pdf, build_pdf

PDF = build_pdf([
    ("h1", "1 Εισαγωγή"),
    ("p", "Η στατιστική μελετά δεδομένα."),
    ("h2", "1.1 Μέση τιμή"),
    ("p", "Η μέση τιμή είναι το άθροισμα διά το πλήθος."),
])


def upload(client, course_id, data=PDF, name="kef1.pdf"):
    return client.post(f"/api/courses/{course_id}/documents", files={"file": (name, data, "application/pdf")})


def make_course(client):
    return client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()["id"]


def test_upload_creates_sections(client, tmp_path):
    course = make_course(client)
    r = upload(client, course)
    assert r.status_code == 201
    doc = r.json()["document"]
    assert [(s["number"], s["title"]) for s in doc["sections"]] == [("1", "Εισαγωγή"), ("1.1", "Μέση τιμή")]
    assert len(list(tmp_path.glob("*.pdf"))) == 1  # stored locally only

    study = client.get(f"/api/sections/{doc['sections'][1]['id']}/study").json()
    assert study["original"] == ["Η μέση τιμή είναι το άθροισμα διά το πλήθος."]


def test_same_pdf_twice_is_not_duplicated(client):
    course = make_course(client)
    first = upload(client, course).json()["document"]
    second = upload(client, course).json()["document"]
    assert first["id"] == second["id"]
    assert len(client.get(f"/api/courses/{course}/documents").json()) == 1


def test_scanned_pdf_message(client):
    r = upload(client, make_course(client), build_image_only_pdf())
    assert r.status_code == 422
    assert r.json()["detail"] == "Αυτό το PDF είναι φωτογραφία, δοκίμασε άλλο."


def test_not_a_pdf_message(client):
    r = upload(client, make_course(client), b"just text", "notes.txt")
    assert r.status_code == 422
    assert "PDF" in r.json()["detail"]


def test_delete_document_removes_file(client, tmp_path):
    course = make_course(client)
    doc = upload(client, course).json()["document"]
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert list(tmp_path.glob("*.pdf")) == []
    assert client.get(f"/api/sections/{doc['sections'][0]['id']}/study").status_code == 404


def test_upload_to_missing_course(client):
    assert upload(client, 999).status_code == 404


def test_unknown_api_path_is_404(client):
    assert client.get("/api/nothing-here").status_code == 404
