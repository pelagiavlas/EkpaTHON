"""MockEkpaProvider: simulated eClass data from a JSON fixture, PDFs from backend/demo/.

Dates are relative to "today" (the app clock, which can be the demo clock), so the
demo always shows the same situation: week 9 of the semester, new documents a few days old.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from app.ekpa.provider import EkpaCourse, EkpaDocument, EkpaProvider, EkpaSlot, EkpaUnit

DATA = Path(__file__).parent / "data" / "ekpa_mock.json"
DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "demo"


class MockEkpaProvider(EkpaProvider):
    def __init__(self, today: date, data_path: Path = DATA, pdf_dir: Path = DEMO_DIR):
        self.today = today
        self.data = json.loads(data_path.read_text(encoding="utf-8"))
        self.pdf_dir = pdf_dir

    def courses(self) -> list[EkpaCourse]:
        return [EkpaCourse(c["id"], c["name"], c.get("icon", "book")) for c in self.data["courses"]]

    def timetable(self) -> list[EkpaSlot]:
        return [EkpaSlot(s["course"], s["weekday"], s["start"], s["end"], s["room"]) for s in self.data["timetable"]]

    def documents(self, course_id: str) -> list[EkpaDocument]:
        docs = []
        for d in self.data["documents"]:
            path = self.pdf_dir / d["file"]
            if d["course"] != course_id or not path.exists():
                continue
            docs.append(EkpaDocument(
                id=d["id"], course_id=course_id, title=d["title"], filename=d["file"],
                added_on=self.today - timedelta(days=d["added_days_ago"]), content=path.read_bytes(),
            ))
        return docs

    def syllabus(self, course_id: str) -> list[EkpaUnit]:
        return [EkpaUnit(u["number"], u["title"], u["week"]) for u in self.data["syllabus"].get(course_id, [])]

    def semester_start(self) -> date:
        monday = self.today - timedelta(days=self.today.weekday())
        return monday - timedelta(weeks=self.data["current_week"] - 1)
