"""The demo data tells the story we promise in the presentation."""

from datetime import date

from sqlmodel import Session

from app.learning import service
from app.models import Course
from app.routers.progress import build_progress
from scripts.seed_demo import seed


def test_demo_story(engine):
    with Session(engine) as session:
        seed(session)
        progress = build_progress(session, date.today())
        stats = next(c for c in progress.courses if c.name == "Στατιστική")
        psych = next(c for c in progress.courses if c.name == "Κοινωνική Ψυχολογία")

        assert progress.simulated is True
        assert stats.level == 3 and psych.level == 1
        assert [(s.from_level, s.to_level) for s in stats.level_history] == [(1, 2), (2, 3)]
        before, now = stats.weeks
        assert now.hints_per_question < before.hints_per_question
        assert "λιγότερη βοήθεια" in stats.message

        # Uploading chapter 3 live: the model suggests starting from level 3.
        course = session.get(Course, stats.id)
        assert service.suggestion_for(session, course, document_id=-1).level == 3
