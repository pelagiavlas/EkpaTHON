"""Demo mode: two weeks of SIMULATED use, clearly marked as such in the app.

Story: in Statistics, hints per question fall from ~2.8 to ~0.3 and the support
level goes 1 -> 2 -> 3 (each change accepted by the student). Chapters 1 and 2
are simulated history; chapter 3 (the demo PDF) is left for the live upload.
A second course stays at level 1, to show that the level is per course.

Run from backend/:
    .venv\\Scripts\\python -m scripts.seed_demo            (empty database only)
    .venv\\Scripts\\python -m scripts.seed_demo --reset    (deletes ALL current data first)
"""

import argparse
import sys
from datetime import datetime, time, timedelta

from sqlmodel import Session, SQLModel, select

from app.db import engine, init_db
from app.models import Attempt, Course, Document, LevelChange, Profile, StrategyNote
from app.schemas import Settings
from scripts.make_demo_pdf import main as make_demo_pdf

QUESTIONS_PER_DAY = 6

# (days ago, chapter, support level that day, mean hints per question, wrong answers that day)
STATISTICS_DAYS = [
    (13, 1, 1, 2.8, 2), (12, 1, 1, 2.5, 2), (10, 1, 1, 2.2, 1),
    (9, 1, 2, 1.8, 1), (8, 1, 2, 1.5, 0),
    (6, 2, 2, 0.9, 1), (5, 2, 2, 0.7, 1),
    (4, 2, 3, 0.5, 0), (3, 2, 3, 0.4, 0), (1, 2, 3, 0.3, 0),
]
# (days ago, from, to): accepted proposals, in the evening of that day
STATISTICS_LEVELS = [(10, 1, 2), (5, 2, 3)]
PSYCHOLOGY_DAYS = [(3, 1, 1, 2.6, 2), (1, 1, 1, 2.3, 1)]


def at(days_ago: int, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(datetime.now().date() - timedelta(days=days_ago), time(hour, minute))


def spread(total: int, n: int) -> list[int]:
    """`total` hints over `n` questions, as evenly as possible, max 4 each."""
    base, extra = divmod(total, n)
    return [min(4, base + (1 if i < extra else 0)) for i in range(n)]


def add_days(session: Session, course: Course, chapters: dict[int, Document], days: list) -> None:
    for days_ago, chapter, level, mean_hints, wrong in days:
        hints = spread(round(mean_hints * QUESTIONS_PER_DAY), QUESTIONS_PER_DAY)
        for i, h in enumerate(hints):
            start = at(days_ago, 17, i * 6)
            is_wrong = i >= QUESTIONS_PER_DAY - wrong
            session.add(Attempt(
                course_id=course.id, document_id=chapters[chapter].id, level=level,
                hints_used=h, wrong_tries=1 if is_wrong else 0, correct=not is_wrong,
                started_at=start, finished_at=start + timedelta(minutes=4), simulated=True,
            ))


def seed(session: Session) -> None:
    profile = session.get(Profile, 1) or Profile(id=1)
    profile.settings_json = Settings(onboarded=True).model_dump_json()
    session.add(profile)

    stats = Course(name="Στατιστική", icon="chart", level=3, created_at=at(14, 10), window_start=at(5, 21))
    psych = Course(name="Κοινωνική Ψυχολογία", icon="brain", level=1, created_at=at(4, 10), window_start=at(4, 10))
    session.add_all([stats, psych])
    session.flush()

    stats_chapters = {
        1: Document(course_id=stats.id, filename="", title="Κεφάλαιο 1: Περιγραφική στατιστική",
                    start_level=1, simulated=True, uploaded_at=at(14, 10)),
        2: Document(course_id=stats.id, filename="", title="Κεφάλαιο 2: Πιθανότητες και δειγματοληψία",
                    start_level=2, simulated=True, uploaded_at=at(7, 10)),
    }
    psych_chapters = {
        1: Document(course_id=psych.id, filename="", title="Κεφάλαιο 1: Εισαγωγή",
                    start_level=1, simulated=True, uploaded_at=at(4, 10)),
    }
    session.add_all([*stats_chapters.values(), *psych_chapters.values()])
    session.flush()

    add_days(session, stats, stats_chapters, STATISTICS_DAYS)
    add_days(session, psych, psych_chapters, PSYCHOLOGY_DAYS)
    for days_ago, from_level, to_level in STATISTICS_LEVELS:
        session.add(LevelChange(course_id=stats.id, from_level=from_level, to_level=to_level,
                                reason="proposal", created_at=at(days_ago, 21), simulated=True))
    session.add(StrategyNote(course_id=stats.id, choice="example", created_at=at(3, 18)))
    session.add(StrategyNote(course_id=stats.id, choice="example", created_at=at(1, 18)))
    session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="σβήνει ΟΛΑ τα δεδομένα πριν το demo")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.reset:
        SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as session:
        if session.exec(select(Course)).first() is not None:
            print("Η βάση έχει ήδη δεδομένα. Τρέξε ξανά με --reset για να τα σβήσεις και να φτιάξεις το demo.")
            return 1
        seed(session)
    pdf = make_demo_pdf()
    print("Έτοιμο το demo (ΠΡΟΣΟΜΟΙΩΜΕΝΑ δεδομένα 2 εβδομάδων).")
    print(f"PDF για το ζωντανό ανέβασμα: {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
