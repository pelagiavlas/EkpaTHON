"""Database tables. Everything stays on the student's device and belongs to them.

No diagnosis or label about the person is stored anywhere: only the settings
they chose and a support level per course that moves both ways.
Rows marked `simulated` come from the demo script and are shown as such.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    settings_json: str = "{}"


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    icon: str = "book"
    level: int = 1  # support level 1 (full help) ... 4 (autonomy)
    proposal: str | None = None  # "up" | "down" while waiting for the student's answer
    # Only answers after the last level decision count for new proposals.
    window_start: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)


class Document(SQLModel, table=True):
    """One uploaded PDF = one chapter."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    filename: str
    title: str = ""
    sha256: str = Field(default="", index=True)
    path: str = ""  # local file under storage/ ("" for simulated chapters)
    suggested_level: int | None = None
    start_level: int | None = None
    simulated: bool = False
    uploaded_at: datetime = Field(default_factory=datetime.now)


class Section(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    position: int
    number: str | None = None  # "3.2" when the heading is numbered
    title: str
    paragraphs_json: str  # original text, one entry per paragraph


class ContentCache(SQLModel, table=True):
    """Easy-to-Read version of a section, so a provider is asked only once."""

    section_id: int = Field(foreign_key="section.id", primary_key=True)
    easy_json: str


class Question(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    level: int
    position: int
    content_json: str  # QuestionContent incl. answer and hints: never sent as a whole


class Attempt(SQLModel, table=True):
    """One student working on one question."""

    id: int | None = Field(default=None, primary_key=True)
    question_id: int | None = Field(default=None, foreign_key="question.id")
    course_id: int = Field(foreign_key="course.id", index=True)
    document_id: int | None = Field(default=None, foreign_key="document.id")
    level: int
    hints_used: int = 0  # 0-4
    wrong_tries: int = 0
    correct: bool | None = None  # None while still open
    self_checked: bool = False
    awaiting_self_check: bool = False  # open answer sent, student compares with the key point
    opened_section: bool = False
    listened: bool = False
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    simulated: bool = False


class StudyView(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id")
    mode: str  # "easy" | "original"
    created_at: datetime = Field(default_factory=datetime.now)


class LevelChange(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    from_level: int
    to_level: int
    reason: str  # "proposal" | "manual" | "new_chapter"
    accepted: bool = True  # False = the student said "not now" to a proposal
    created_at: datetime = Field(default_factory=datetime.now)
    simulated: bool = False


class StrategyNote(SQLModel, table=True):
    """Answer to "Τι σε βοήθησε;" (level 3)."""

    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    choice: str  # "listen" | "image" | "example"
    created_at: datetime = Field(default_factory=datetime.now)


class SupporterAccess(SQLModel, table=True):
    """Read-only access to progress per course, given and revoked by the student."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    token: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    revoked_at: datetime | None = None
