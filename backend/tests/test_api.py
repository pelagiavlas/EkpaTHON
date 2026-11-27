from datetime import date, timedelta

MONDAY = date(2026, 11, 30)


def setup_week(client):
    windows = [{"weekday": d, "start": "17:00", "end": "20:00"} for d in range(7)]
    assert client.put("/availability", json={"windows": windows}).status_code == 200
    course = client.post("/courses", json={"name": "Μαθηματικά"}).json()
    task = client.post(
        "/tasks",
        json={
            "course_id": course["id"],
            "title": "Κεφάλαιο 3",
            "kind": "study",
            "deadline": str(MONDAY + timedelta(days=7)),
            "pages": 20,
            "difficulty": 1,
        },
    ).json()
    return course, task


def test_profile_defaults_and_update(client):
    assert client.get("/profile").json()["chunk_minutes"] == 30
    r = client.put("/profile", json={"chunk_minutes": 20, "ui_prefs": {"dyslexia_font": True}})
    assert r.json()["chunk_minutes"] == 20
    assert r.json()["ui_prefs"] == {"dyslexia_font": True}


def test_profile_rejects_chunk_outside_limits(client):
    assert client.put("/profile", json={"chunk_minutes": 90}).status_code == 422


def test_availability_rejects_end_before_start(client):
    r = client.put("/availability", json={"windows": [{"weekday": 0, "start": "18:00", "end": "17:00"}]})
    assert r.status_code == 422


def test_task_estimate_from_pages(client):
    _, task = setup_week(client)
    assert task["base_minutes"] == 60  # 20 pages x 3 min x difficulty 1


def test_task_without_estimate_rejected(client):
    course = client.post("/courses", json={"name": "Φυσική"}).json()
    r = client.post(
        "/tasks",
        json={"course_id": course["id"], "title": "Άσκηση", "kind": "assignment", "deadline": "2026-12-10"},
    )
    assert r.status_code == 422


def test_generate_and_follow_a_chunk(client):
    _, task = setup_week(client)
    schedule = client.post("/schedule/generate", json={"start_date": str(MONDAY), "seed": 1}).json()
    study = [c for c in schedule["chunks"] if c["kind"] == "study"]
    assert len(study) == 2 and schedule["unscheduled"] == []
    assert [c["seq"] for c in study] == [1, 2]

    first = study[0]
    today = client.get("/schedule/today", params={"day": first["day"]}).json()
    assert first["id"] in [c["id"] for c in today]

    assert client.post(f"/chunks/{first['id']}/start").json()["status"] == "in_progress"
    assert client.post(f"/chunks/{first['id']}/help").json()["help_requests"] == 1
    done = client.post(f"/chunks/{first['id']}/finish", json={"actual_minutes": 40}).json()
    assert done["status"] == "done" and done["actual_minutes"] == 40


def test_regenerate_keeps_history_and_plans_only_the_rest(client):
    _, task = setup_week(client)
    first = client.post("/schedule/generate", json={"start_date": str(MONDAY), "seed": 1}).json()
    study = [c for c in first["chunks"] if c["kind"] == "study"]
    client.post(f"/chunks/{study[0]['id']}/finish")

    again = client.post("/schedule/generate", json={"start_date": str(MONDAY + timedelta(days=1)), "seed": 2}).json()
    new_study = [c for c in again["chunks"] if c["kind"] == "study"]
    assert len(new_study) == 1
    assert new_study[0]["seq"] == 2


def test_item_done_removes_it_from_planning(client):
    _, task = setup_week(client)
    chunks = client.post("/schedule/generate", json={"start_date": str(MONDAY), "seed": 1}).json()["chunks"]
    client.post(f"/chunks/{chunks[0]['id']}/finish", json={"item_done": True})
    again = client.post("/schedule/generate", json={"start_date": str(MONDAY), "seed": 1}).json()
    assert again["chunks"] == []


def test_delete_course_removes_its_tasks(client):
    course, _ = setup_week(client)
    client.post("/schedule/generate", json={"start_date": str(MONDAY), "seed": 1})
    assert client.delete(f"/courses/{course['id']}").status_code == 204
    assert client.get("/tasks").json() == []
