"""«Δεν ξέρω αυτή τη λέξη» and «Οι λέξεις μου»."""

import pytest

from app.content.mock import MockProvider
from app.content.rules import explain_word
from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf


def test_glossary_finds_any_form_without_accents_or_capitals():
    assert explain_word("ΔΕΙΓΜΑΤΟΣ").term == "δείγμα"
    assert explain_word("«διάστημα εμπιστοσύνης»,").term == "διάστημα εμπιστοσύνης"
    assert explain_word("καρέκλα") is None


def test_mock_provider_prefers_the_section_glossary():
    from app.content.provider import SectionInput

    section = SectionInput("3.4", "Η επίδραση του μεγέθους του δείγματος", [])
    assert MockProvider().explain_word("ακριβής", section).gloss == "πολύ κοντά στον σωστό αριθμό"


@pytest.fixture
def section(client):
    course = client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()
    doc = client.post(f"/api/courses/{course['id']}/documents",
                      files={"file": ("k3.pdf", build_pdf(CHAPTER), "application/pdf")}).json()
    return client, next(s["id"] for s in doc["sections"] if s["number"] == "3.4")


def test_known_word_gets_its_simple_explanation(section):
    client, sid = section
    r = client.post(f"/api/sections/{sid}/words", json={"word": "δείγματος,"}).json()
    assert r["found"] and r["word"] == "δείγματος" and r["term"] == "δείγμα" and r["gloss"]


def test_unknown_word_is_honest_and_goes_to_the_reviewer(section, monkeypatch):
    client, sid = section
    r = client.post(f"/api/sections/{sid}/words", json={"word": "τετραπλασιασμός"}).json()
    assert not r["found"] and r["message"].startswith("Δεν έχουμε ακόμα εξήγηση για αυτή τη λέξη")
    monkeypatch.setenv("REVIEW_MODE", "true")
    report = client.get("/api/review/reports").json()[0]
    assert report["kind_label"] == "Δεν ξέρω αυτή τη λέξη" and report["word"] == "τετραπλασιασμός"


def test_my_words_one_row_per_word_and_removable(section):
    client, sid = section
    for w in ("δείγμα", "δείγματος", "τετραπλασιασμός"):
        client.post(f"/api/sections/{sid}/words", json={"word": w})
    words = client.get("/api/words").json()
    assert [w["term"] or w["word"] for w in words] == ["τετραπλασιασμός", "δείγμα"]
    client.delete(f"/api/words/{words[1]['id']}")
    assert [w["word"] for w in client.get("/api/words").json()] == ["τετραπλασιασμός"]


def test_empty_word_is_rejected(section):
    client, sid = section
    assert client.post(f"/api/sections/{sid}/words", json={"word": " «» "}).status_code == 422
