"""The whole flow through the API, with support levels per section."""

import json

import pytest
from sqlmodel import Session, select

from app.models import ConceptMastery

from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf

PDF = build_pdf(CHAPTER)


@pytest.fixture
def setup(client):
    course = client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()
    doc = client.post(
        f"/api/courses/{course['id']}/documents", files={"file": ("kef3.pdf", PDF, "application/pdf")}
    ).json()
    sections = {s["number"]: s["id"] for s in doc["sections"]}
    return client, course, doc, sections


def set_level(client, section_id, level):
    return client.post(f"/api/sections/{section_id}/level", json={"level": level, "reason": "manual"}).json()


def start(client, section_id, index=0, exam=False):
    data = client.get(f"/api/sections/{section_id}/questions", params={"exam": exam}).json()
    q = data["questions"][index]
    attempt = client.post(f"/api/questions/{q['id']}/attempts", params={"exam": exam}).json()["attempt_id"]
    return data, q, attempt


def answer_right(client, section_id, index, hints=0):
    _, _, attempt = start(client, section_id, index)
    for _ in range(hints):
        client.post(f"/api/attempts/{attempt}/hint")
    return client.post(f"/api/attempts/{attempt}/answer", json={"option_id": 0}).json()


# --- 1. no placement before first use ----------------------------------------------

def test_upload_goes_straight_to_sections_all_at_level_1(setup):
    _, _, doc, _ = setup
    assert doc["title"] == "Κεφάλαιο 3: Διάστημα εμπιστοσύνης"
    assert {s["level"] for s in doc["sections"]} == {1}
    assert not any(s["has_proposal"] for s in doc["sections"])
    assert "suggestion" not in doc


def test_first_use_has_no_question_before_studying(client):
    settings = client.get("/api/settings").json()
    assert settings["onboarded"] is False and settings["readAloud"] is True  # defaults, nothing asked


def test_known_concepts_are_offered_never_applied(client, engine):
    """A new chapter whose concepts are already known: a proposal with an explanation, no change."""
    course = client.post("/api/courses", json={"name": "Στατιστική", "icon": "chart"}).json()
    with Session(engine) as s:
        for concept in ("διάστημα εμπιστοσύνης", "επίπεδο εμπιστοσύνης"):
            s.add(ConceptMastery(course_id=course["id"], concept=concept, p_known=0.97, observations=6))
        s.commit()
    doc = client.post(f"/api/courses/{course['id']}/documents", files={"file": ("k3.pdf", PDF, "application/pdf")}).json()
    sections = {s["number"]: s for s in doc["sections"]}
    assert {s["level"] for s in doc["sections"]} == {1}  # nothing applied silently
    support = client.get(f"/api/sections/{sections['3.2']['id']}/support").json()
    assert support["proposal"]["reason"] == "known_start" and support["proposal"]["to_level"] == 2
    assert "Ξέρεις ήδη" in support["proposal"]["message"]
    assert not sections["3.4"]["has_proposal"]  # 3.4 also needs "μέγεθος δείγματος", not known yet
    assert (doc["concepts_known"], doc["concepts_total"]) == (2, 6)


# --- study ---------------------------------------------------------------------------

def test_study_shows_easy_read_and_original(setup):
    client, _, _, sections = setup
    study = client.get(f"/api/sections/{sections['3.4']}/study").json()
    assert study["easy"]["source"] == "fixture" and study["support"]["level"] == 1
    assert any(b["type"] == "example" and "100" in b["text"] for b in study["easy"]["blocks"])
    assert study["original"][0].startswith("Από τον τύπο προκύπτει")
    assert study["demo"] is False


def test_level_preview_only_in_demo_mode(setup, monkeypatch):
    client, _, _, sections = setup
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert client.get(f"/api/sections/{sections['3.4']}/study").json()["demo"] is False
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get(f"/api/sections/{sections['3.4']}/study").json()["demo"] is True


def test_students_see_ways_of_studying_not_level_numbers(setup):
    client, _, doc, sections = setup
    names = {s["level_name"] for s in doc["sections"]}
    assert names == {"Με πολλή υποστήριξη"}
    for level, name in [(2, "Με λιγότερη υποστήριξη"), (3, "Από το πρωτότυπο"), (4, "Αυτόνομα")]:
        assert set_level(client, sections["3.4"], level)["level_name"] == name


# --- levels 1-2: hints that explain ----------------------------------------------------

def test_level_1_two_choices_and_the_answer_never_sent(setup):
    client, _, _, sections = setup
    data, q, _ = start(client, sections["3.4"])
    assert data["level"] == 1 and q["mode"] == "choice" and len(q["options"]) == 2
    raw = json.dumps(data, ensure_ascii=False)
    for secret in ("key_point", "accept", "hints", "source_sentence", "Όταν ρωτάς περισσότερους"):
        assert secret not in raw


def test_level_2_three_choices(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 2)
    _, q, _ = start(client, sections["3.4"])
    assert len(q["options"]) == 3


def test_maria_climbs_two_explaining_hints_and_answers(setup):
    client, _, _, sections = setup
    _, q, attempt = start(client, sections["3.4"])
    h1 = client.post(f"/api/attempts/{attempt}/hint").json()
    assert h1["kind"] == "explain" and h1["action"] == "replay_example" and "καφέ" in h1["example"]["text"]
    h2 = client.post(f"/api/attempts/{attempt}/hint").json()
    assert h2["step"] == 2 and "100 φίλους" in h2["text"]
    right = next(o for o in q["options"] if o["text"] == "Το διάστημα μικραίνει")
    result = client.post(f"/api/attempts/{attempt}/answer", json={"option_id": right["id"]}).json()
    assert result["outcome"] == "correct" and result["message"] == "Σωστά. Το βρήκες."


def test_wrong_answer_is_neutral_and_explanation_only_after_trying(setup):
    client, _, _, sections = setup
    _, q, attempt = start(client, sections["3.4"])
    assert client.post(f"/api/attempts/{attempt}/explain").status_code == 409
    wrong = next(o for o in q["options"] if o["id"] != 0)
    result = client.post(f"/api/attempts/{attempt}/answer", json={"option_id": wrong["id"]}).json()
    assert result["outcome"] == "try_again" and result["key_point"] is None
    assert "Λάθος" not in result["message"]
    assert result["message"] == "Όχι ακόμα. Ζήτησε υπόδειξη ή δοκίμασε ξανά."
    assert client.post(f"/api/attempts/{attempt}/explain").json()["key_point"]


# --- levels 3-4: hints that point into the ORIGINAL --------------------------------------

def test_level_3_hints_point_into_the_original_and_explain_nothing(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, q, attempt = start(client, sections["3.4"])
    assert q["mode"] == "open"
    a = client.post(f"/api/attempts/{attempt}/hint").json()
    b = client.post(f"/api/attempts/{attempt}/hint").json()
    c = client.post(f"/api/attempts/{attempt}/hint").json()
    assert [h["kind"] for h in (a, b, c)] == ["search"] * 3
    assert a["text"] == "Η απάντηση είναι στην ενότητα 3.4. Διάβασέ την ξανά." and a["action"] == "open_original"
    assert b["text"] == "Είναι στην 1η παράγραφο." and b["paragraph"] == 0
    assert c["text"] == "Βρες την πρόταση που λέει τι γίνεται όταν μεγαλώνει το n. Πάτησέ την."
    assert len(c["sentences"]) == 3
    for h in (a, b, c):  # no Easy-to-Read, no example, no choices
        assert h["example"] is None and h["choices"] == []


def test_picking_the_right_sentence_then_answering(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, _, attempt = start(client, sections["3.4"])
    for _ in range(3):
        hint = client.post(f"/api/attempts/{attempt}/hint").json()
    wrong = client.post(f"/api/attempts/{attempt}/pick", json={"sentence": 0}).json()
    assert wrong == {"correct": False, "message": "Δεν είναι αυτή. Ψάξε στην ίδια παράγραφο.",
                     "fallback_hint": None, "new_milestones": []}
    target = next(i for i, s in enumerate(hint["sentences"]) if s.startswith("Επομένως"))
    right = client.post(f"/api/attempts/{attempt}/pick", json={"sentence": target}).json()
    assert right["correct"] and right["new_milestones"][0]["key"] == "first_found_sentence"
    done = client.post(f"/api/attempts/{attempt}/answer", json={"text": "γίνεται πιο στενό"}).json()
    assert done["outcome"] == "correct"


def test_three_wrong_sentences_fall_back_to_level_2_hints_and_count_for_fading(setup, engine):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, _, attempt = start(client, sections["3.4"])
    for _ in range(3):
        client.post(f"/api/attempts/{attempt}/hint")
    client.post(f"/api/attempts/{attempt}/pick", json={"sentence": 0})
    second = client.post(f"/api/attempts/{attempt}/pick", json={"sentence": 2}).json()
    assert "Θες βοήθεια" in second["message"]
    third = client.post(f"/api/attempts/{attempt}/pick", json={"sentence": 0}).json()
    assert third["fallback_hint"]["kind"] == "explain" and third["fallback_hint"]["fell_back"]
    assert third["fallback_hint"]["step"] == 1
    nxt = client.post(f"/api/attempts/{attempt}/hint").json()
    assert nxt["kind"] == "explain" and nxt["step"] == 2

    from sqlmodel import Session
    from app.models import Attempt
    with Session(engine) as s:
        assert s.get(Attempt, attempt).fell_back is True


def test_help_after_the_search_steps_falls_back(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 4)
    _, _, attempt = start(client, sections["3.4"])
    kinds = [client.post(f"/api/attempts/{attempt}/hint").json()["kind"] for _ in range(4)]
    assert kinds == ["search", "search", "search", "explain"]


def test_pick_needs_step_3(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, _, attempt = start(client, sections["3.4"])
    assert client.post(f"/api/attempts/{attempt}/pick", json={"sentence": 0}).status_code == 409


# --- fading per section, always with a yes -----------------------------------------------

def test_fading_is_per_section(setup, rules_engine):
    client, _, _, sections = setup
    answer_right(client, sections["3.1"], 0)
    answer_right(client, sections["3.1"], 1)
    answer_right(client, sections["3.2"], 0)  # 3 successes, but in two sections
    assert client.get(f"/api/sections/{sections['3.1']}/support").json()["proposal"] is None
    result = answer_right(client, sections["3.1"], 0)
    assert result["proposal"]["reason"] == "fading_up" and result["proposal"]["to_level"] == 2
    assert client.get(f"/api/sections/{sections['3.2']}/support").json()["proposal"] is None


def test_no_level_change_without_a_yes(setup, rules_engine):
    client, _, _, sections = setup
    for i in (0, 1, 0):
        answer_right(client, sections["3.1"], i)
    assert client.get(f"/api/sections/{sections['3.1']}/support").json()["level"] == 1
    after = client.post(f"/api/sections/{sections['3.1']}/level", json={"level": 2, "reason": "proposal"}).json()
    assert after["level"] == 2 and after["proposal"] is None


def test_declining_starts_counting_again(setup, rules_engine):
    client, _, _, sections = setup
    for i in (0, 1, 0):
        answer_right(client, sections["3.1"], i)
    declined = client.post(f"/api/sections/{sections['3.1']}/proposal/decline").json()
    assert declined["level"] == 1 and declined["proposal"] is None
    assert answer_right(client, sections["3.1"], 1)["proposal"] is None


def test_easy_text_used_often_brings_a_proposal_not_a_change(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.3"], 3)
    support = None
    for used in (True, False, True):
        visit = client.post(f"/api/sections/{sections['3.3']}/visits").json()["visit_id"]
        if used:
            support = client.post(f"/api/visits/{visit}/easy").json()
    assert support["level"] == 3
    assert support["proposal"]["reason"] == "easy_use" and support["proposal"]["to_level"] == 2


def test_settings_never_change_with_the_level(setup):
    client, _, _, sections = setup
    chosen = {"fontScale": 1.5, "lineSpacing": 2.0, "highContrast": True, "reducedMotion": True,
              "readAloud": True, "autoRead": False, "voiceRate": 0.7, "onboarded": True}
    client.put("/api/settings", json=chosen)
    for level in (1, 2, 3, 4, 1):
        set_level(client, sections["3.4"], level)
        client.get(f"/api/sections/{sections['3.4']}/study")
        assert client.get("/api/settings").json() == chosen


# --- level 4 ---------------------------------------------------------------------------

def test_level_4_key_points_shown_only_after_writing(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 4)
    r = client.post(f"/api/sections/{sections['3.4']}/keypoints", json={"text": "Περισσότεροι άνθρωποι, πιο στενό."}).json()
    assert any("περισσότεροι άνθρωποι" in p.lower() for p in r["key_points"])
    done = client.post(f"/api/attempts/{r['attempt_id']}/self-check", json={"close": True}).json()
    assert done["message"] == "Ωραία. Τα βασικά σημεία τα είχες."


def test_own_questions_are_kept(setup):
    client, _, _, sections = setup
    client.post(f"/api/sections/{sections['3.4']}/my-questions", json={"text": "Γιατί √n και όχι n;"})
    assert [n["text"] for n in client.get(f"/api/sections/{sections['3.4']}/my-questions").json()] == ["Γιατί √n και όχι n;"]


def test_exam_practice_only_at_level_4_no_help_no_level_change(setup):
    client, _, _, sections = setup
    assert client.get(f"/api/sections/{sections['3.4']}/questions", params={"exam": True}).status_code == 409
    set_level(client, sections["3.4"], 4)
    data, q, attempt = start(client, sections["3.4"], exam=True)
    assert data["exam"] and q["mode"] == "open"
    assert client.post(f"/api/attempts/{attempt}/hint").status_code == 409
    r = client.post(f"/api/attempts/{attempt}/answer", json={"text": "μικραίνει"}).json()
    assert r["proposal"] is None and r["new_milestones"][0]["key"] == "first_exam"


# --- milestones, progress, supporter -----------------------------------------------------

def test_milestones_are_given_once(setup):
    client, _, _, sections = setup
    first = answer_right(client, sections["3.1"], 0)
    second = answer_right(client, sections["3.1"], 1)
    assert [m["key"] for m in first["new_milestones"]] == ["first_no_help"]
    assert second["new_milestones"] == []


def test_progress_shows_levels_per_section(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.2"], 3)
    answer_right(client, sections["3.1"], 0, hints=2)
    progress = client.get("/api/progress").json()
    stats = progress["courses"][0]
    levels = {s["label"]: s["level"] for s in stats["chapters"][0]["sections"]}
    assert levels["3.2 Η έννοια του διαστήματος εμπιστοσύνης"] == 3
    assert levels["3.1 Σημειακή εκτίμηση και δειγματοληπτικό σφάλμα"] == 1
    assert stats["weeks"][1]["hints_per_question"] == 2
    assert stats["level_history"][0]["section"].startswith("3.2")


def test_supporter_sees_levels_not_answers_and_can_be_revoked(setup):
    client, _, _, sections = setup
    answer_right(client, sections["3.1"], 0)
    supporter = client.post("/api/supporters", json={"name": "Ελένη", "scope": "section"}).json()
    shared = client.get(f"/api/shared/{supporter['token']}").json()
    assert shared["scope"] == "section" and shared["courses"][0]["chapters"][0]["sections"]
    assert shared["milestones"] == []
    assert "χρειάστηκες" not in json.dumps(shared, ensure_ascii=False)
    client.delete(f"/api/supporters/{supporter['id']}")
    assert client.get(f"/api/shared/{supporter['token']}").status_code == 404


def test_supporter_sees_only_courses_by_default_and_student_can_change_it(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.2"], 3)
    answer_right(client, sections["3.1"], 0, hints=1)
    supporter = client.post("/api/supporters", json={"name": "Ελένη"}).json()
    assert supporter["scope"] == "course"
    course = client.get(f"/api/shared/{supporter['token']}").json()["courses"][0]
    assert course["message"] and course["weeks"][1]["questions"] == 1
    assert course["chapters"] == course["days"] == course["level_history"] == course["concepts"] == []
    more = client.put(f"/api/supporters/{supporter['id']}/scope", json={"scope": "section"}).json()
    assert more["scope"] == "section"
    assert client.get(f"/api/shared/{supporter['token']}").json()["courses"][0]["chapters"]
    assert client.put(f"/api/supporters/{supporter['id']}/scope", json={"scope": "all"}).status_code == 422


def test_strategy_question_at_level_3(setup):
    client, course, _, sections = setup
    set_level(client, sections["3.4"], 3)
    assert client.get(f"/api/sections/{sections['3.4']}/questions").json()["ask_strategy"] is True
    client.post(f"/api/courses/{course['id']}/strategy", json={"choice": "example"})
    last = client.get(f"/api/sections/{sections['3.4']}/questions").json()["last_strategy"]
    assert last == {"choice": "example", "label": "Το παράδειγμα"}


# --- knowledge tracing (BKT) -----------------------------------------------------------

def known(engine, concept):
    with Session(engine) as s:
        return s.exec(select(ConceptMastery).where(ConceptMastery.concept == concept)).first()


def test_bkt_updates_after_each_answer(setup, engine):
    client, _, _, sections = setup
    answer_right(client, sections["3.4"], 0)  # q7, two choices, no help
    row = known(engine, "μέγεθος δείγματος")
    assert row.observations == 1 and round(row.p_known, 2) == 0.52


def test_self_checked_answers_do_not_update_bkt(setup, engine):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, _, attempt = start(client, sections["3.4"])
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν είμαι σίγουρος"})
    assert client.post(f"/api/attempts/{attempt}/answer", json={"text": "κάτι αλλάζει"}).json()["outcome"] == "self_check"
    assert client.post(f"/api/attempts/{attempt}/self-check", json={"close": True}).json()["done"]
    row = known(engine, "μέγεθος δείγματος")
    assert row is None or row.observations == 0


def test_bkt_proposes_less_support_when_every_concept_is_known(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    _, _, a = start(client, sections["3.4"], 0)
    first = client.post(f"/api/attempts/{a}/answer", json={"text": "μικραίνει"}).json()
    assert first["proposal"] is None  # one concept of two
    _, _, b = start(client, sections["3.4"], 1)
    second = client.post(f"/api/attempts/{b}/answer", json={"text": "μεγαλώνει"}).json()
    assert second["proposal"]["reason"] == "known_up" and second["proposal"]["to_level"] == 4
    assert client.get(f"/api/sections/{sections['3.4']}/support").json()["level"] == 3  # still a proposal


def test_bkt_proposes_more_support_only_after_enough_answers(setup):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 2)
    results = []
    for _ in range(2):
        _, q, attempt = start(client, sections["3.4"], 0)
        wrong = next(o for o in q["options"] if o["id"] != 0)
        client.post(f"/api/attempts/{attempt}/answer", json={"option_id": wrong["id"]})
        results.append(client.post(f"/api/attempts/{attempt}/explain").json())
    assert results[0]["proposal"] is None  # one answer is not enough
    assert results[1]["proposal"]["reason"] == "concept_down" and results[1]["proposal"]["to_level"] == 1


def test_students_never_get_probabilities(setup):
    client, _, _, sections = setup
    answer_right(client, sections["3.4"], 0)
    concepts = client.get(f"/api/sections/{sections['3.4']}/concepts").json()
    assert concepts == [{"concept": "μέγεθος δείγματος", "label_key": "learning", "label": "Το μαθαίνεις"}]
    progress = json.dumps(client.get("/api/progress").json())
    assert "p_known" not in progress and "0.52" not in progress


# --- open answers: try again first, self-check later (mentor feedback) ---------------------

def open_attempt(client, sections, level=3):
    set_level(client, sections["3.4"], level)
    return start(client, sections["3.4"])[2]


def test_first_unmatched_open_answer_is_try_again_without_the_key_point(setup):
    client, _, _, sections = setup
    attempt = open_attempt(client, sections)
    r = client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"}).json()
    assert r == {"outcome": "try_again", "message": "Όχι ακόμα. Ζήτησε υπόδειξη ή δοκίμασε ξανά.",
                 "key_point": None, "done": False, "proposal": None, "new_milestones": []}


def test_second_unmatched_open_answer_brings_self_check(setup):
    client, _, _, sections = setup
    attempt = open_attempt(client, sections)
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"})
    r = client.post(f"/api/attempts/{attempt}/answer", json={"text": "κάτι αλλάζει"}).json()
    assert r["outcome"] == "self_check" and r["key_point"].startswith("Όταν ρωτάς περισσότερους")


def test_self_check_right_away_after_all_hints(setup):
    client, _, _, sections = setup
    attempt = open_attempt(client, sections)
    for _ in range(7):  # 3 search steps + 4 explaining hints
        client.post(f"/api/attempts/{attempt}/hint")
    r = client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"}).json()
    assert r["outcome"] == "self_check" and r["key_point"]


def test_no_new_answer_while_waiting_for_self_check(setup):
    client, _, _, sections = setup
    attempt = open_attempt(client, sections)
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"})
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "κάτι αλλάζει"})
    r = client.post(f"/api/attempts/{attempt}/answer", json={"text": "μικραίνει"})
    assert r.status_code == 409 and r.json()["detail"] == "Πρώτα πες μας αν είναι κοντά σε αυτό που έγραψες."


def test_right_after_one_try_again_still_works(setup):
    client, _, _, sections = setup
    attempt = open_attempt(client, sections)
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"})
    assert client.post(f"/api/attempts/{attempt}/answer", json={"text": "μικραίνει"}).json()["outcome"] == "correct"


def self_checked_close(client, section_id, index):
    _, _, attempt = start(client, section_id, index)
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν ξέρω"})
    client.post(f"/api/attempts/{attempt}/answer", json={"text": "δεν είμαι σίγουρος"})
    return client.post(f"/api/attempts/{attempt}/self-check", json={"close": True}).json()


def test_self_checked_answers_never_count_as_success_for_a_proposal(setup, rules_engine):
    client, _, _, sections = setup
    set_level(client, sections["3.4"], 3)
    results = [self_checked_close(client, sections["3.4"], i % 2) for i in range(4)]
    assert all(r["proposal"] is None for r in results)
