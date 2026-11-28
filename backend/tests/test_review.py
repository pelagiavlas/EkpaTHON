"""Human review of AI content, anonymous reports, and the teacher summary with a minimum count."""

import pytest

from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf


@pytest.fixture
def section(client, monkeypatch):
    monkeypatch.delenv("REVIEW_MODE", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    course = client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()
    doc = client.post(f"/api/courses/{course['id']}/documents",
                      files={"file": ("k3.pdf", build_pdf(CHAPTER), "application/pdf")}).json()
    return client, next(s["id"] for s in doc["sections"] if s["number"] == "3.4")


def test_ai_made_content_starts_as_draft(section):
    client, sid = section
    study = client.get(f"/api/sections/{sid}/study").json()
    assert study["review_status"] == "ai_draft" and study["reviewed_by"] is None


def test_report_is_stored_anonymously(section):
    client, sid = section
    r = client.post(f"/api/sections/{sid}/reports", json={"kind": "unclear", "block_index": 2, "comment": " "})
    assert r.status_code == 201 and r.json()["message"] == "Ευχαριστούμε. Θα το δει κάποιος."
    assert client.post(f"/api/sections/{sid}/reports", json={"kind": "spam"}).status_code == 422


def test_review_screen_is_off_by_default(section):
    client, _ = section
    assert client.get("/api/review/sections").status_code == 403
    assert client.get("/api/features").json()["review"] is False


def test_reviewer_approves_and_can_undo(section, monkeypatch):
    client, sid = section
    monkeypatch.setenv("REVIEW_MODE", "true")
    drafts = client.get("/api/review/sections").json()
    item = next(i for i in drafts if i["section_id"] == sid)
    assert item["original"][0].startswith("Από τον τύπο") and item["blocks"]
    approved = client.post(f"/api/review/sections/{sid}/approve", json={"reviewed_by": "Μονάδα Προσβασιμότητας"}).json()
    assert approved["status"] == "reviewed"
    study = client.get(f"/api/sections/{sid}/study").json()
    assert study["review_status"] == "reviewed" and study["reviewed_by"] == "Μονάδα Προσβασιμότητας"
    assert sid not in [i["section_id"] for i in client.get("/api/review/sections").json()]
    assert client.post(f"/api/review/sections/{sid}/reopen").json()["status"] == "ai_draft"


def test_reports_list_has_no_student_data(section, monkeypatch):
    client, sid = section
    monkeypatch.setenv("REVIEW_MODE", "true")
    client.post(f"/api/sections/{sid}/reports", json={"kind": "wrong", "comment": "Το 99% δεν το καταλαβαίνω"})
    rows = client.get("/api/review/reports").json()
    assert rows[0]["kind_label"] == "Νομίζω ότι είναι λάθος"
    assert set(rows[0]) == {"id", "section", "kind", "kind_label", "block_index", "word", "comment", "created_at"}


def test_teacher_summary_needs_a_minimum_count(section, monkeypatch):
    client, sid = section
    for _ in range(3):
        client.post(f"/api/sections/{sid}/reports", json={"kind": "unclear"})
    monkeypatch.setenv("REVIEW_MODE", "true")
    real = client.get("/api/review/summary").json()
    assert real["min_count"] == 5 and real["rows"] == []  # 3 < 5: nothing shown
    demo = client.get("/api/review/summary", params={"demo": True}).json()
    assert demo["demo_threshold"] and demo["rows"] == [{"section": "3.4 Η επίδραση του μεγέθους του δείγματος", "unclear": 3}]


def test_features_unsafe_things_are_off(client):
    f = client.get("/api/features").json()
    assert f["help_now"] is True and f["alerts"] is False and f["forum"] is False
