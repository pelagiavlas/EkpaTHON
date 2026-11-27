"""The whole flow through the API: upload, study, questions, hints, fading, progress, supporter."""

import json

import pytest

from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf

PDF = build_pdf(CHAPTER)


@pytest.fixture
def setup(client):
    course = client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()
    upload = client.post(
        f"/api/courses/{course['id']}/documents", files={"file": ("kef3.pdf", PDF, "application/pdf")}
    ).json()
    sections = {s["number"]: s["id"] for s in upload["document"]["sections"]}
    return client, course, upload, sections


def set_level(client, course_id, level):
    return client.post(f"/api/courses/{course_id}/level", json={"level": level, "reason": "manual"}).json()


def first_question(client, section_id):
    data = client.get(f"/api/sections/{section_id}/questions").json()
    q = data["questions"][0]
    attempt = client.post(f"/api/questions/{q['id']}/attempts").json()["attempt_id"]
    return data, q, attempt


def test_upload_first_chapter_suggests_current_level(setup):
    _, course, upload, _ = setup
    assert upload["document"]["title"] == "Κεφάλαιο 3: Διάστημα εμπιστοσύνης"
    assert upload["suggestion"]["level"] == 1 == upload["current_level"]


def test_study_shows_easy_read_and_original(setup):
    client, _, _, sections = setup
    study = client.get(f"/api/sections/{sections['3.4']}/study").json()
    assert study["easy"]["source"] == "fixture"
    assert any(b["type"] == "example" and "100" in b["text"] for b in study["easy"]["blocks"])
    assert study["original"][0].startswith("Από τον τύπο προκύπτει")
    assert study["position"] == 5 and study["total"] == 5 and study["next_id"] is None


def test_level_1_has_two_choices_and_never_sends_the_answer(setup):
    client, _, _, sections = setup
    data, q, _ = first_question(client, sections["3.4"])
    assert data["level"] == 1 and q["mode"] == "choice"
    assert len(q["options"]) == 2
    raw = json.dumps(data, ensure_ascii=False)
    for secret in ("key_point", "accept", "hints", "Όταν ρωτάμε περισσότερους"):
        assert secret not in raw


def test_level_2_has_three_choices(setup):
    client, course, _, sections = setup
    set_level(client, course["id"], 2)
    _, q, _ = first_question(client, sections["3.4"])
    assert len(q["options"]) == 3


def test_maria_climbs_two_hint_steps_and_answers(setup):
    client, course, _, sections = setup
    set_level(client, course["id"], 2)
    _, q, attempt = first_question(client, sections["3.4"])

    h1 = client.post(f"/api/attempts/{attempt}/hint").json()
    assert h1["step"] == 1 and h1["action"] == "replay_example" and "καφέ" in h1["example"]["text"]
    h2 = client.post(f"/api/attempts/{attempt}/hint").json()
    assert h2["step"] == 2 and "100 φίλους" in h2["text"]

    right = next(o for o in q["options"] if o["text"] == "Το διάστημα μικραίνει")
    result = client.post(f"/api/attempts/{attempt}/answer", json={"option_id": right["id"]}).json()
    assert result == {
        "outcome": "correct", "message": "Σωστά. Το βρήκες.", "done": True, "proposal": None,
        "key_point": "Όταν ρωτάμε περισσότερους, το διάστημα μικραίνει. Η εκτίμηση γίνεται πιο ακριβής.",
    }


def test_wrong_answer_is_neutral_and_explanation_only_after_trying(setup):
    client, _, _, sections = setup
    _, q, attempt = first_question(client, sections["3.4"])
    assert client.post(f"/api/attempts/{attempt}/explain").status_code == 409  # not before trying

    wrong = next(o for o in q["options"] if o["id"] != 0)
    result = client.post(f"/api/attempts/{attempt}/answer", json={"option_id": wrong["id"]}).json()
    assert result["outcome"] == "try_again" and result["key_point"] is None
    assert "Λάθος" not in result["message"] and result["message"].startswith("Ας το δούμε μαζί")

    explained = client.post(f"/api/attempts/{attempt}/explain").json()
    assert explained["outcome"] == "explained" and explained["key_point"]


def test_hint_ladder_has_four_steps_and_step_three_gives_two_choices(setup):
    client, course, _, sections = setup
    set_level(client, course["id"], 3)
    data, q, attempt = first_question(client, sections["3.4"])
    assert q["mode"] == "open" and q["options"] == []
    steps = [client.post(f"/api/attempts/{attempt}/hint").json() for _ in range(4)]
    assert [s["step"] for s in steps] == [1, 2, 3, 4]
    assert len(steps[2]["choices"]) == 2
    assert "Το διάστημα μικραίνει" not in steps[3]["text"]
    assert client.post(f"/api/attempts/{attempt}/hint").status_code == 409


def test_open_answer_and_self_check(setup):
    client, course, _, sections = setup
    set_level(client, course["id"], 3)
    _, _, attempt = first_question(client, sections["3.4"])
    assert client.post(f"/api/attempts/{attempt}/answer", json={"text": "γίνεται πιο στενό"}).json()["outcome"] == "correct"

    data = client.get(f"/api/sections/{sections['3.4']}/questions").json()
    second = client.post(f"/api/questions/{data['questions'][1]['id']}/attempts").json()["attempt_id"]
    r = client.post(f"/api/attempts/{second}/answer", json={"text": "δεν είμαι σίγουρη, κάτι αλλάζει"}).json()
    assert r["outcome"] == "self_check" and r["key_point"]
    done = client.post(f"/api/attempts/{second}/self-check", json={"close": True}).json()
    assert done["outcome"] == "correct" and done["done"]


def answer_right(client, section_id, index, hints=0):
    data = client.get(f"/api/sections/{section_id}/questions").json()
    q = data["questions"][index]
    attempt = client.post(f"/api/questions/{q['id']}/attempts").json()["attempt_id"]
    for _ in range(hints):
        client.post(f"/api/attempts/{attempt}/hint")
    return client.post(f"/api/attempts/{attempt}/answer", json={"option_id": 0}).json()


def test_three_easy_successes_bring_a_proposal_that_the_student_decides(setup):
    client, course, _, sections = setup
    answer_right(client, sections["3.1"], 0)
    answer_right(client, sections["3.1"], 1, hints=1)
    result = answer_right(client, sections["3.2"], 0)
    assert result["proposal"]["direction"] == "up" and result["proposal"]["to_level"] == 2
    assert "χωρίς βοήθεια" in result["proposal"]["message"]

    # Nothing changes until the student says yes.
    assert client.get(f"/api/courses/{course['id']}").json()["level"] == 1
    after = client.post(f"/api/courses/{course['id']}/level", json={"level": 2, "reason": "proposal"}).json()
    assert after["level"] == 2 and after["proposal"] is None


def test_declining_a_proposal_starts_counting_again(setup):
    client, course, _, sections = setup
    for section, i in (("3.1", 0), ("3.1", 1), ("3.2", 0)):
        answer_right(client, sections[section], i)
    declined = client.post(f"/api/courses/{course['id']}/proposal/decline").json()
    assert declined["level"] == 1 and declined["proposal"] is None
    assert answer_right(client, sections["3.2"], 1)["proposal"] is None


def test_second_chapter_gets_a_prediction(setup):
    client, course, _, sections = setup
    for section, i in (("3.1", 0), ("3.1", 1), ("3.2", 0), ("3.2", 1)):
        answer_right(client, sections[section], i)
    client.post(f"/api/courses/{course['id']}/level", json={"level": 2, "reason": "proposal"})
    other = build_pdf([("h1", "4 Έλεγχος υποθέσεων"), ("p", "Η υπόθεση ελέγχεται με δεδομένα από ένα δείγμα.")])
    upload = client.post(
        f"/api/courses/{course['id']}/documents", files={"file": ("kef4.pdf", other, "application/pdf")}
    ).json()
    assert upload["suggestion"]["level"] == 3  # 0 hints so far, capped at current level + 1
    chosen = client.post(f"/api/documents/{upload['document']['id']}/start-level", json={"level": 2}).json()
    assert chosen["level"] == 2  # the student keeps their own choice


def test_progress_and_supporter(setup):
    client, course, _, sections = setup
    answer_right(client, sections["3.1"], 0, hints=2)
    progress = client.get("/api/progress").json()
    assert progress["simulated"] is False
    stats = progress["courses"][0]
    assert stats["weeks"][1]["questions"] == 1 and stats["weeks"][1]["hints_per_question"] == 2
    assert stats["level_name"] == "Πλήρης βοήθεια"

    supporter = client.post("/api/supporters", json={"name": "Ελένη"}).json()
    shared = client.get(f"/api/shared/{supporter['token']}").json()
    assert shared["courses"][0]["level"] == 1
    assert "χρειάστηκες" not in json.dumps(shared, ensure_ascii=False)

    assert client.delete(f"/api/supporters/{supporter['id']}").status_code == 204
    assert client.get(f"/api/shared/{supporter['token']}").status_code == 404


def test_settings_roundtrip(client):
    assert client.get("/api/settings").json()["readAloud"] is True  # sound on by default
    saved = client.put("/api/settings", json={"fontScale": 1.5, "readAloud": False, "onboarded": True}).json()
    assert saved["fontScale"] == 1.5 and client.get("/api/settings").json()["readAloud"] is False


def test_strategy_question_at_level_3(setup):
    client, course, _, sections = setup
    set_level(client, course["id"], 3)
    assert client.get(f"/api/sections/{sections['3.4']}/questions").json()["ask_strategy"] is True
    client.post(f"/api/courses/{course['id']}/strategy", json={"choice": "example"})
    last = client.get(f"/api/sections/{sections['3.4']}/questions").json()["last_strategy"]
    assert last == {"choice": "example", "label": "Το παράδειγμα"}
