"""The demo data tells the story we promise in the presentation."""

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.routers.progress import build_progress
from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf
from scripts.seed_demo import seed


def test_demo_story(engine):
    with Session(engine) as session:
        seed(session)
        progress = build_progress(session, date.today())
    stats = next(c for c in progress.courses if c.name == "Στατιστική")
    psych = next(c for c in progress.courses if c.name == "Κοινωνική Ψυχολογία")

    assert progress.simulated is True
    levels = {s.label: s.level for ch in stats.chapters for s in ch.sections}
    assert levels["2.1 Σημειακή εκτίμηση και δειγματοληπτικό σφάλμα"] == 3
    assert {s.level for ch in psych.chapters for s in ch.sections} == {1}
    assert len(stats.level_history) == 6
    before, now = stats.weeks
    assert now.hints_per_question < before.hints_per_question
    assert "λιγότερη βοήθεια" in stats.message


def test_live_upload_after_demo_offers_level_3_for_known_topics(client, engine):
    with Session(engine) as session:
        seed(session)
    course = next(c for c in client.get("/api/courses").json() if c["name"] == "Στατιστική")
    doc = client.post(f"/api/courses/{course['id']}/documents",
                      files={"file": ("k3.pdf", build_pdf(CHAPTER), "application/pdf")}).json()
    by_number = {s["number"]: s for s in doc["sections"]}
    assert {by_number[n]["level"] for n in ("3.1", "3.2", "3.3", "3.4")} == {1}  # nothing applied silently
    assert by_number["3.1"]["has_proposal"] and by_number["3.2"]["has_proposal"]
    assert not by_number["3.3"]["has_proposal"] and not by_number["3.4"]["has_proposal"]
    assert client.get(f"/api/sections/{by_number['3.4']['id']}/study").json()["demo"] is True
