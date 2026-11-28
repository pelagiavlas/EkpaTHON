"""eClass (mock), timetable, "Σήμερα", syllabus prediction, confirmations and corrections."""

import json
from datetime import date, datetime, time, timedelta

import pytest

from app.ekpa.clock import current_time
from app.ekpa.eclass import EclassProvider
from app.ekpa.schedule import Slot, Unit, ended_classes, next_class, predict_unit, teaching_position

TUE, THU = 1, 3
SLOTS = [Slot(1, TUE, time(11), time(13), "Α2"), Slot(1, THU, time(11), time(13), "Α2")]
A_TUESDAY = date(2026, 12, 1)
SEMESTER = A_TUESDAY - timedelta(days=1) - timedelta(weeks=8)  # Monday of week 1: A_TUESDAY is in week 9
UNITS = [Unit(i + 1, i, f"Ενότητα {i}", week) for i, week in enumerate([6, 7, 8, 9, 10])]


def at(day: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(day, time(hh, mm))


# --- timetable ------------------------------------------------------------------------

def test_next_class_before_during_and_after():
    c, phase = next_class(SLOTS, at(A_TUESDAY, 9, 30))
    assert (c.day, c.start, phase) == (A_TUESDAY, time(11), "before")
    assert next_class(SLOTS, at(A_TUESDAY, 12))[1] == "during"
    c, phase = next_class(SLOTS, at(A_TUESDAY, 13, 30))
    assert (c.day.weekday(), phase) == (THU, "later")


def test_next_class_over_the_weekend():
    friday = A_TUESDAY + timedelta(days=3)
    c, phase = next_class(SLOTS, at(friday, 18))
    assert c.day == A_TUESDAY + timedelta(days=7) and phase == "later"


def test_no_timetable_no_next_class():
    assert next_class([], at(A_TUESDAY, 9)) is None


def test_ended_classes_most_recent_first():
    ended = ended_classes(SLOTS, at(A_TUESDAY, 13, 30))
    assert ended[0].day == A_TUESDAY and ended[1].day == A_TUESDAY - timedelta(days=5)


# --- syllabus prediction ------------------------------------------------------------------

def test_prediction_follows_the_plan_without_confirmations():
    assert predict_unit(UNITS, [], A_TUESDAY, SEMESTER).title == "Ενότητα 3"  # week 9


def test_prediction_follows_what_really_happened():
    # Teaching is behind: the student confirmed unit 1 last time -> today unit 2, not the planned 3.
    assert predict_unit(UNITS, [0, 1], A_TUESDAY, SEMESTER).title == "Ενότητα 2"


def test_prediction_after_the_last_unit():
    assert predict_unit(UNITS, [4], A_TUESDAY, SEMESTER) is None


def test_teaching_position_prefers_confirmations():
    assert teaching_position(UNITS, [], A_TUESDAY, SEMESTER).title == "Ενότητα 3"
    assert teaching_position(UNITS, [1], A_TUESDAY, SEMESTER).title == "Ενότητα 1"


# --- demo clock -------------------------------------------------------------------------------

def test_demo_clock_always_has_a_class_at_11(monkeypatch):
    monkeypatch.delenv("DEMO_DATE", raising=False)
    monkeypatch.delenv("DEMO_TIME", raising=False)
    for real in range(7):
        now = current_time(True, SLOTS, real_now=at(A_TUESDAY + timedelta(days=real), 20))
        assert now.weekday() in (TUE, THU) and now.time() == time(9, 30)
        assert next_class(SLOTS, now)[0].start == time(11)
    assert current_time(True, SLOTS, "after", at(A_TUESDAY, 8)).time() == time(13)


def test_demo_date_can_be_set(monkeypatch):
    monkeypatch.setenv("DEMO_DATE", "2026-12-03")
    assert current_time(True, SLOTS, real_now=at(A_TUESDAY, 8)).date() == date(2026, 12, 3)


def test_without_demo_the_real_clock():
    real = at(A_TUESDAY, 17, 45)
    assert current_time(False, SLOTS, "after", real) == real


# --- through the API (mock eClass) -------------------------------------------------------------

@pytest.fixture
def demo(client, monkeypatch):
    monkeypatch.delenv("DEMO_DATE", raising=False)
    monkeypatch.delenv("EKPA_PROVIDER", raising=False)
    return client


def today(client, moment="before"):
    return client.get("/api/today", params={"demo": True, "moment": moment}).json()


def test_sync_imports_courses_timetable_syllabus_and_parses_documents(demo):
    first = demo.post("/api/ekpa/sync", params={"demo": True}).json()
    again = demo.post("/api/ekpa/sync", params={"demo": True}).json()
    assert first["new_documents"] == 2 and again["new_documents"] == 0
    courses = {c["name"]: c for c in demo.get("/api/courses").json()}
    assert set(courses) == {"Στατιστική", "Κοινωνική Ψυχολογία"} and courses["Στατιστική"]["from_eclass"]
    docs = demo.get(f"/api/courses/{courses['Στατιστική']['id']}/documents").json()
    assert [s["number"] for s in docs[0]["sections"]] == [None, "3.1", "3.2", "3.3", "3.4"]


def test_today_before_class(demo):
    view = today(demo)
    assert view["demo"] and view["simulated_eclass"]
    nc = view["next_class"]
    assert (nc["course_name"], nc["start"], nc["room"], nc["phase"], nc["is_today"]) == \
        ("Στατιστική", "11:00", "Αμφιθέατρο Α2", "before", True)
    before = view["before"]
    assert before["unit_title"] == "3.4 Η επίδραση του μεγέθους του δείγματος"  # planned for week 9
    assert before["section_id"] and before["minutes"] >= 1
    assert {m["title"] for m in view["new_material"]} == {"Κεφάλαιο 3: Διάστημα εμπιστοσύνης", "Κεφάλαιο 2: Κοινωνική επιρροή"}


def test_after_class_confirm_then_two_questions(demo):
    view = today(demo, "after")
    after = view["after"]
    assert after["when"] == "Σήμερα" and after["course_name"] == "Στατιστική"
    assert after["predicted"]["title"].startswith("3.4")
    r = demo.post("/api/classes/confirm", params={"demo": True, "moment": "after"}, json={
        "course_id": after["course_id"], "class_date": after["class_date"], "unit_id": after["predicted"]["unit_id"]}).json()
    assert r["status"] == "done" and r["section_id"] and r["has_questions"]
    nxt = today(demo, "after")["after"]
    assert nxt is None or nxt["class_date"] != after["class_date"]  # today's class is not asked again
    plan = demo.get(f"/api/courses/{after['course_id']}/plan", params={"demo": True}).json()
    assert plan["teaching"]["title"].startswith("3.4") and plan["teaching_from"] == "confirmed"


def test_we_did_another_unit_moves_the_plan(demo):
    after = today(demo, "after")["after"]
    other = next(u for u in after["units"] if u["title"].startswith("3.2"))
    demo.post("/api/classes/confirm", params={"demo": True, "moment": "after"}, json={
        "course_id": after["course_id"], "class_date": after["class_date"], "unit_id": other["unit_id"]})
    plan = demo.get(f"/api/courses/{after['course_id']}/plan", params={"demo": True}).json()
    assert plan["teaching"]["title"].startswith("3.2")
    course = next(c for c in demo.get("/api/courses", params={"demo": True}).json() if c["id"] == after["course_id"])
    assert course["teaching"].startswith("3.2")


def test_dont_know_is_asked_again_another_day_not_today(demo, monkeypatch):
    after = today(demo, "after")["after"]
    demo.post("/api/classes/confirm", params={"demo": True, "moment": "after"}, json={
        "course_id": after["course_id"], "class_date": after["class_date"], "status": "unknown"})
    same_day = today(demo, "after")["after"]
    assert same_day is None or same_day["class_date"] != after["class_date"]
    next_day = date.fromisoformat(after["class_date"]) + timedelta(days=1)
    monkeypatch.setenv("DEMO_DATE", next_day.isoformat())
    again = today(demo, "after")["after"]
    assert again["class_date"] == after["class_date"] and again["when"] != "Σήμερα"  # calmly, "Την Τρίτη..."


def test_student_can_correct_where_teaching_is(demo):
    after = today(demo, "after")["after"]
    demo.post("/api/classes/confirm", params={"demo": True, "moment": "after"}, json={
        "course_id": after["course_id"], "class_date": after["class_date"], "unit_id": after["predicted"]["unit_id"]})
    unit = next(u for u in after["units"] if u["title"].startswith("3.3"))
    plan = demo.post(f"/api/courses/{after['course_id']}/teaching", params={"demo": True}, json={"unit_id": unit["unit_id"]}).json()
    assert plan["teaching"]["title"].startswith("3.3")


def test_new_material_disappears_once_opened(demo):
    view = today(demo)
    doc = view["new_material"][0]
    demo.post(f"/api/documents/{doc['document_id']}/seen")
    assert doc["document_id"] not in [m["document_id"] for m in today(demo)["new_material"]]


def test_offers_never_orders(demo):
    text = json.dumps(today(demo, "after"), ensure_ascii=False)
    assert "Πρέπει" not in text and "πρέπει" not in text


def test_no_password_anywhere_and_eclass_is_a_placeholder(demo, monkeypatch):
    from app import schemas

    assert not any("password" in name.lower() or "κωδικ" in name.lower() for name in dir(schemas))
    with pytest.raises(NotImplementedError):
        EclassProvider().courses()
    today(demo)  # store some data first
    monkeypatch.setenv("EKPA_PROVIDER", "eclass")
    assert demo.post("/api/ekpa/sync").status_code == 503
    view = demo.get("/api/today", params={"demo": True}).json()  # works with what is stored
    assert view["simulated_eclass"] is False and view["next_class"]["course_name"] == "Στατιστική"
