"""Demo mode: two weeks of SIMULATED use, clearly marked as such in the app.

Story (support level per SECTION):
- Statistics, chapters 1-2 (simulated): help per question falls from ~2.8 to ~0.4 and
  sections climb 1 -> 2 -> 3, every change accepted by the student.
- Chapter 2 already covered two topics that come back in the demo PDF (chapter 3):
  "Σημειακή εκτίμηση και δειγματοληπτικό σφάλμα" and "Η έννοια του διαστήματος εμπιστοσύνης".
  Knowledge tracing (BKT) knows those concepts, so after the live upload 3.1 and 3.2 get a
  PROPOSAL ("you already know these concepts"), 3.3 and 3.4 start at level 1.
  So the presentation can show both kinds of help.
- A second course stays at level 1.

Run from backend/:
    .venv\\Scripts\\python -m scripts.seed_demo            (empty database only)
    .venv\\Scripts\\python -m scripts.seed_demo --reset    (deletes ALL current data first)
"""

import argparse
import json
import sys
from datetime import datetime, time, timedelta

from sqlmodel import Session, SQLModel, select

from app.db import engine, init_db
from app.ekpa import service as ekpa
from app.ekpa.clock import demo_day
from app.ekpa.mock import MockEkpaProvider
from app.ekpa.schedule import Slot, parse_time
from app.learning import service
from app.models import (
    Attempt, ClassConfirmation, ConceptMastery, Course, SyllabusUnit, Document, LevelChange, Milestone, Profile, Section, SectionSupport, StrategyNote,
)
from app.schemas import Settings
from scripts.make_demo_pdf import main as make_demo_pdf

QUESTIONS_PER_DAY = 6

# (number, title, concepts its questions check)
STATISTICS = {
    "Κεφάλαιο 1: Περιγραφική στατιστική": [
        ("1.1", "Μέση τιμή και διάμεσος", ["μέση τιμή", "διάμεσος"]),
        ("1.2", "Διασπορά και τυπική απόκλιση", ["διασπορά", "τυπική απόκλιση"]),
    ],
    "Κεφάλαιο 2: Δειγματοληψία": [
        ("2.1", "Σημειακή εκτίμηση και δειγματοληπτικό σφάλμα", ["δείγμα", "δειγματοληπτικό σφάλμα"]),
        ("2.2", "Η έννοια του διαστήματος εμπιστοσύνης", ["διάστημα εμπιστοσύνης", "επίπεδο εμπιστοσύνης"]),
    ],
}
# (days ago, section, level that day, mean help per question, wrong answers that day)
STATISTICS_DAYS = [
    (13, "1.1", 1, 2.8, 2), (12, "1.2", 1, 2.6, 2), (10, "1.1", 1, 2.0, 1),
    (9, "1.2", 1, 1.8, 1), (8, "1.1", 2, 1.4, 1),
    (6, "2.1", 1, 1.2, 1), (5, "2.2", 1, 1.0, 0), (4, "2.1", 2, 0.6, 0),
    (3, "2.2", 2, 0.5, 0), (2, "2.2", 3, 0.3, 0), (1, "2.1", 3, 0.4, 0),
]
# (section, days ago, from, to): proposals the student accepted, in the evening of that day
STATISTICS_LEVELS = [
    ("1.1", 10, 1, 2), ("1.2", 9, 1, 2), ("2.1", 6, 1, 2), ("2.2", 5, 1, 2), ("2.1", 4, 2, 3), ("2.2", 3, 2, 3),
]
PSYCHOLOGY = {"Κεφάλαιο 1: Εισαγωγή": [
    ("1.1", "Τι είναι η κοινωνική ψυχολογία", ["κοινωνική επιρροή", "ομάδα"]),
    ("1.2", "Στάσεις και συμπεριφορά", ["στάση", "συμπεριφορά"]),
]}
OPTIONS_AT_LEVEL = {1: 2, 2: 3, 3: 0, 4: 0}  # level 1: two choices, 2: three, 3-4: open questions
PSYCHOLOGY_DAYS = [(3, "1.1", 1, 2.6, 2), (1, "1.2", 1, 2.3, 1)]


def at(days_ago: int, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(datetime.now().date() - timedelta(days=days_ago), time(hour, minute))


def spread(total: int, n: int) -> list[int]:
    """`total` hints over `n` questions, as evenly as possible, max 3 each."""
    base, extra = divmod(total, n)
    return [min(3, base + (1 if i < extra else 0)) for i in range(n)]


def add_chapters(session: Session, course: Course, chapters: dict, uploaded_days_ago: list[int]) -> dict[str, Section]:
    sections = {}
    for (title, parts), days_ago in zip(chapters.items(), uploaded_days_ago):
        doc = Document(course_id=course.id, filename="", title=title, simulated=True, uploaded_at=at(days_ago, 10))
        session.add(doc)
        session.flush()
        for position, (number, name, concepts) in enumerate(parts):
            section = Section(document_id=doc.id, position=position, number=number, title=name, paragraphs_json="[]",
                              concepts_json=json.dumps(concepts, ensure_ascii=False))
            session.add(section)
            session.flush()
            session.add(SectionSupport(section_id=section.id, window_start=at(days_ago, 10)))
            sections[number] = section
    return sections


def add_days(session: Session, course: Course, sections: dict[str, Section], days: list) -> None:
    for days_ago, number, level, mean_help, wrong in days:
        section = sections[number]
        concepts = json.loads(section.concepts_json)
        for i, help_count in enumerate(spread(round(mean_help * QUESTIONS_PER_DAY), QUESTIONS_PER_DAY)):
            start = at(days_ago, 17, i * 6)
            is_wrong = i >= QUESTIONS_PER_DAY - wrong
            search = level >= 3  # at level 3 the help is "look in the original", not explanations
            session.add(Attempt(
                section_id=section.id, course_id=course.id, document_id=section.document_id, level=level,
                hints_used=0 if search else help_count, search_steps=help_count if search else 0,
                found_sentence=search and help_count >= 3, wrong_tries=1 if is_wrong else 0, correct=not is_wrong,
                started_at=start, finished_at=start + timedelta(minutes=4), simulated=True,
                concept=concepts[i % len(concepts)], shown_options=OPTIONS_AT_LEVEL[level],
            ))


def trace_knowledge(session: Session) -> None:
    """Run the real BKT over the simulated answers, oldest first, so the demo's
    'Το ξέρεις' labels come from the same model the app uses."""
    session.flush()
    for attempt in session.exec(select(Attempt).order_by(Attempt.finished_at)):
        service.record_evidence(session, attempt)
    for row in session.exec(select(ConceptMastery)):
        row.simulated = True
        session.add(row)


def demo_provider() -> MockEkpaProvider:
    """The mock eClass, dated on the demo "today" (the nearest day with a class at 11:00)."""
    mock = MockEkpaProvider(datetime.now().date())
    slots = [Slot(0, s.weekday, parse_time(s.start), parse_time(s.end), s.room) for s in mock.timetable()]
    return MockEkpaProvider(demo_day(slots, datetime.now().date()))


def confirm_past_classes(session: Session, provider: MockEkpaProvider, taught_until: dict[int, str]) -> None:
    """Past classes already answered: teaching reached `taught_until` (so today's class is about the next unit)."""
    today = provider.today
    slots = ekpa.load_slots(session)
    for course_id, last_number in taught_until.items():
        units = session.exec(select(SyllabusUnit).where(SyllabusUnit.course_id == course_id).order_by(SyllabusUnit.position)).all()
        last = next(u.position for u in units if u.number == last_number)
        days = [today - timedelta(days=n) for n in range(1, 15)]
        class_days = [d for d in days if any(s.course_id == course_id and s.weekday == d.weekday() for s in slots)]
        for i, day in enumerate(class_days):  # most recent class -> last taught unit, going back
            position = max(0, last - i)
            unit = next(u for u in units if u.position == position)
            session.add(ClassConfirmation(course_id=course_id, class_date=day, unit_id=unit.id, status="done",
                                          asked_on=day, simulated=True))
    session.flush()


def seed(session: Session) -> None:
    profile = session.get(Profile, 1) or Profile(id=1)
    profile.settings_json = Settings(onboarded=True).model_dump_json()
    session.add(profile)

    # Courses, timetable and syllabus come from (simulated) eClass.
    provider = demo_provider()
    courses = ekpa.sync_structure(session, provider)
    stats, psych = courses["stat101"], courses["psy210"]
    stats.created_at, psych.created_at = at(14, 10), at(4, 10)

    stats_sections = add_chapters(session, stats, STATISTICS, [14, 7])
    psych_sections = add_chapters(session, psych, PSYCHOLOGY, [4])
    add_days(session, stats, stats_sections, STATISTICS_DAYS)
    add_days(session, psych, psych_sections, PSYCHOLOGY_DAYS)

    for number, days_ago, from_level, to_level in STATISTICS_LEVELS:
        section = stats_sections[number]
        session.add(LevelChange(section_id=section.id, from_level=from_level, to_level=to_level,
                                reason="fading_up", created_at=at(days_ago, 21), simulated=True))
        support = session.get(SectionSupport, section.id)
        support.level = to_level
        support.window_start = at(days_ago, 21)
        session.add(support)
    session.add(Milestone(key="first_level3", section_id=stats_sections["2.1"].id, seen=True,
                          created_at=at(4, 21), simulated=True))
    session.add(StrategyNote(course_id=stats.id, choice="example", created_at=at(1, 18)))
    trace_knowledge(session)
    confirm_past_classes(session, provider, {stats.id: "3.3", psych.id: "2.1"})
    # Last: the teacher's new PDFs, analysed like uploads (BKT already knows the earlier concepts).
    ekpa.sync_documents(session, provider)
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
        pdf = make_demo_pdf()  # the PDFs the simulated eClass points to
        seed(session)
    print("Έτοιμο το demo (ΠΡΟΣΟΜΟΙΩΜΕΝΑ δεδομένα 2 εβδομάδων).")
    print(f"Το Κεφάλαιο 3 έρχεται ως «Νέο υλικό» από το (προσομοιωμένο) eClass. Για χειροκίνητο ανέβασμα: {pdf}")
    print("Για την προεπισκόπηση στην παρουσίαση: DEMO_MODE=true στο backend/.env ή ?demo=1 στο URL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
