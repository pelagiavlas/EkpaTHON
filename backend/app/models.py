"""Database tables. Everything stays on the student's device and belongs to them.

No diagnosis or label about the person is stored anywhere: only the settings
they chose and a support level per SECTION that moves both ways, always with
the student's approval. Rows marked `simulated` come from the demo script.
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    settings_json: str = "{}"  # accessibility settings: never changed by a support level
    # First use: «Θέλεις κάποιος να σε βοηθήσει να ξεκινήσεις;» ("with_help" | "alone"; None = not answered)
    start_choice: str | None = None
    start_step: int = 1  # the step of the start guide to continue from (1-4)
    start_done: bool = False


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    icon: str = "book"
    ekpa_id: str | None = Field(default=None, index=True)  # the university's id, when it comes from eClass
    created_at: datetime = Field(default_factory=datetime.now)


class Document(SQLModel, table=True):
    """One uploaded PDF = one chapter."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    filename: str
    title: str = ""
    sha256: str = Field(default="", index=True)
    path: str = ""  # local file under storage/ ("" for simulated chapters)
    simulated: bool = False
    source: str = "upload"  # "upload" (by the student) or "eclass" (posted by the teacher)
    ekpa_id: str | None = Field(default=None, index=True)
    seen_at: datetime | None = None  # first time the student opened it (for "Νέο υλικό")
    uploaded_at: datetime = Field(default_factory=datetime.now)


class Section(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    position: int
    number: str | None = None  # "3.2" when the heading is numbered
    title: str
    paragraphs_json: str  # original text, one entry per paragraph
    concepts_json: str = "[]"  # concepts its questions check (for "Ξέρεις ήδη 3 από τις 5 έννοιες")


class SectionSupport(SQLModel, table=True):
    """Support level of one section. Every section starts at level 1."""

    section_id: int = Field(foreign_key="section.id", primary_key=True)
    level: int = 1
    proposal_to: int | None = None  # a level waiting for the student's yes/no
    proposal_reason: str | None = None  # fading_up | fading_down | easy_use | same_topic
    # Only answers and visits after the last decision count for new proposals.
    window_start: datetime = Field(default_factory=datetime.now)


class ContentCache(SQLModel, table=True):
    """Easy-to-Read version of a section, so a provider is asked only once."""

    section_id: int = Field(foreign_key="section.id", primary_key=True)
    easy_json: str
    # Human review of what a provider (rules, fixtures written with AI, later an LLM) produced.
    review_status: str = "ai_draft"  # "ai_draft" | "reviewed"
    reviewed_by: str | None = None  # free text, e.g. "Μονάδα Προσβασιμότητας"
    reviewed_at: datetime | None = None


class Question(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    level: int
    position: int
    content_json: str  # QuestionContent incl. answer and hints: never sent as a whole


class Attempt(SQLModel, table=True):
    """One student working on one question (or on the key points, at level 4)."""

    id: int | None = Field(default=None, primary_key=True)
    question_id: int | None = Field(default=None, foreign_key="question.id")
    section_id: int | None = Field(default=None, foreign_key="section.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    document_id: int | None = Field(default=None, foreign_key="document.id")
    level: int
    mode: str = "question"  # question | keypoints | exam (exam never changes the level)
    concept: str | None = None  # the concept the question checks (for knowledge tracing)
    shown_options: int = 0  # 2 or 3 choices, 0 = open question (sets the BKT guess chance)
    hints_used: int = 0  # hints that explain (0-4)
    search_steps: int = 0  # levels 3-4: hints that point into the original (0-3)
    wrong_picks: int = 0
    found_sentence: bool = False
    fell_back: bool = False  # levels 3-4: went back to the hints that explain
    wrong_tries: int = 0
    correct: bool | None = None  # None while still open
    self_checked: bool = False
    awaiting_self_check: bool = False
    opened_section: bool = False
    listened: bool = False
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    simulated: bool = False


class ConceptMastery(SQLModel, table=True):
    """Bayesian Knowledge Tracing: estimated probability that a concept is known, per course.
    Internal only: the student sees words ("Το μαθαίνεις", ...), never this number."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    concept: str = Field(index=True)
    p_known: float
    observations: int = 0
    updated_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class Visit(SQLModel, table=True):
    """One time the student opened a section to read it."""

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    level: int
    used_easy: bool = False  # opened the Easy-to-Read text during this visit
    created_at: datetime = Field(default_factory=datetime.now)


class LevelChange(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    from_level: int
    to_level: int
    reason: str  # fading_up | fading_down | easy_use | same_topic | manual
    accepted: bool = True  # False = the student said "not now"
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class StrategyNote(SQLModel, table=True):
    """Answer to "Τι σε βοήθησε;" (level 3)."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    choice: str  # "listen" | "image" | "example"
    created_at: datetime = Field(default_factory=datetime.now)


class SectionNote(SQLModel, table=True):
    """Level 4: key points the student wrote, or a question of their own."""

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    kind: str  # "keypoints" | "question"
    text: str
    created_at: datetime = Field(default_factory=datetime.now)


class Milestone(SQLModel, table=True):
    """A calm "first time" message, shown once."""

    key: str = Field(primary_key=True)
    section_id: int | None = None
    seen: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class SupporterAccess(SQLModel, table=True):
    """Read-only access to progress per course, given and revoked by the student."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    token: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    revoked_at: datetime | None = None
    scope: str = "course"  # course: only the picture per course | section: also each section's way of studying
    ask_less_at: datetime | None = None  # when to ask «...να βλέπει λιγότερα;» again (None = 4 weeks after created_at)


class TimetableSlot(SQLModel, table=True):
    """Weekly timetable from eClass."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    weekday: int  # 0 = Monday
    start: str  # "HH:MM"
    end: str
    room: str = ""


class SyllabusUnit(SQLModel, table=True):
    """The teaching plan: units in order, each with its planned week."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    position: int
    number: str | None = None
    title: str
    week: int


class ClassConfirmation(SQLModel, table=True):
    """What the student says was taught in a class. Can be corrected any time."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    class_date: date = Field(index=True)
    unit_id: int | None = Field(default=None, foreign_key="syllabusunit.id")
    status: str = "done"  # "done" | "unknown" ("Δεν ξέρω": asked again calmly another day)
    asked_on: date | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class ContentReport(SQLModel, table=True):
    """«Κάτι δεν μου φαίνεται σωστό» / «Δεν ξέρω αυτή τη λέξη». Anonymous: no student is named anywhere."""

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    block_index: int | None = None  # paragraph of the Easy-to-Read text, None = the whole part
    kind: str  # "unclear" | "wrong" | "missing" | "word"
    word: str | None = None
    comment: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class WordLookup(SQLModel, table=True):
    """«Δεν ξέρω αυτή τη λέξη»: the student's own vocabulary list («Οι λέξεις μου»)."""

    id: int | None = Field(default=None, primary_key=True)
    word: str
    term: str | None = None  # the glossary term it matched
    gloss: str | None = None
    section_id: int | None = Field(default=None, foreign_key="section.id")
    found: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False
