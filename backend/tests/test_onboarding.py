"""First use, the start guide with its practice question, and the supporter's view fading over time."""

from datetime import datetime, timedelta

from sqlmodel import Session, func, select

from app.learning import answers, practice
from app.models import Attempt, LevelChange, SupporterAccess


def test_first_use_question_until_answered(client):
    assert client.get("/api/today").json()["start"] == {"choice": None, "step": 1, "done": False}
    alone = client.post("/api/start", json={"choice": "alone"}).json()
    assert alone == {"choice": "alone", "step": 1, "done": True}
    helped = client.post("/api/start", json={"choice": "with_help"}).json()
    assert helped["choice"] == "with_help" and helped["done"] is False
    assert client.put("/api/start/step", json={"step": 3}).json()["step"] == 3
    assert client.put("/api/start/step", json={"step": 4, "done": True}).json()["done"] is True
    assert client.get("/api/today").json()["start"]["done"] is True
    assert client.post("/api/start", json={"choice": "maybe"}).status_code == 422
    assert client.put("/api/start/step", json={"step": 5}).status_code == 422


def test_demo_can_show_the_questions_again(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    client.post("/api/start", json={"choice": "alone"})
    assert client.delete("/api/start").status_code == 403
    assert client.delete("/api/start", params={"demo": True}).json()["choice"] is None
    s = client.post("/api/supporters", json={"name": "Ελένη"}).json()
    assert client.post(f"/api/supporters/{s['id']}/ask-now").status_code == 403
    client.post(f"/api/supporters/{s['id']}/ask-now", params={"demo": True})
    assert checks(client) == [s["id"]]


def test_practice_question_gives_hints_not_the_answer(client):
    data = client.get("/api/practice").json()
    assert data["blocks"] and data["glossary"]
    q = data["question"]
    assert len(q["hints"]) == 4 and practice.RIGHT in q["options"] and q["options"][0] != practice.RIGHT
    assert all(practice.RIGHT.lower() not in h.lower() for h in q["hints"])


def test_practice_answer_is_never_stored(client, engine):
    wrong = client.post("/api/practice/answer", json={"option": "Όλες τις λεπτομέρειες"}).json()
    assert wrong == {"correct": False, "message": answers.TRY_AGAIN}
    right = client.post("/api/practice/answer", json={"option": practice.RIGHT}).json()
    assert right == {"correct": True, "message": answers.CORRECT}
    with Session(engine) as session:
        assert session.exec(select(func.count()).select_from(Attempt)).one() == 0
        assert session.exec(select(func.count()).select_from(LevelChange)).one() == 0
    progress = client.get("/api/progress").json()
    assert progress["courses"] == [] and progress["milestones"] == []


def backdate(engine, supporter_id, **fields):
    with Session(engine) as session:
        row = session.get(SupporterAccess, supporter_id)
        for k, v in fields.items():
            setattr(row, k, v)
        session.add(row)
        session.commit()


def checks(client):
    return [c["id"] for c in client.get("/api/today").json()["supporter_checks"]]


def test_supporter_question_every_four_weeks(client, engine):
    s = client.post("/api/supporters", json={"name": "Ελένη", "scope": "section"}).json()
    assert checks(client) == []
    backdate(engine, s["id"], created_at=datetime.now() - timedelta(weeks=4, days=1))
    assert checks(client) == [s["id"]]
    client.post(f"/api/supporters/{s['id']}/keep")  # «Όχι, άφησέ το»
    assert checks(client) == []
    backdate(engine, s["id"], ask_less_at=datetime.now() - timedelta(minutes=1))
    assert checks(client) == [s["id"]]
    assert client.put(f"/api/supporters/{s['id']}/scope", json={"scope": "course"}).json()["scope"] == "course"
    assert checks(client) == []
    backdate(engine, s["id"], ask_less_at=datetime.now() - timedelta(minutes=1))
    client.delete(f"/api/supporters/{s['id']}")  # one tap
    assert checks(client) == []
    assert client.post(f"/api/supporters/{s['id']}/keep").status_code == 404
