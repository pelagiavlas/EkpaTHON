"""Request and response bodies of the API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.content.schema import Block, GlossaryEntry

ICONS = ("chart", "book", "flask", "calculator", "brain", "globe", "scale", "code")


# --- settings -------------------------------------------------------------

class Settings(BaseModel):
    """Display and sound settings. Only what the student chose: no diagnosis."""

    fontScale: float = Field(1.0, ge=1.0, le=2.0)
    lineSpacing: float = Field(1.6, ge=1.4, le=2.4)
    highContrast: bool = False
    reducedMotion: bool = False
    readAloud: bool = True
    autoRead: bool = True
    voiceRate: float = Field(0.9, ge=0.5, le=1.5)
    onboarded: bool = False


# --- courses and chapters -------------------------------------------------

class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: Literal[ICONS] = "book"  # type: ignore[valid-type]


class ProposalOut(BaseModel):
    direction: Literal["up", "down"]
    from_level: int
    to_level: int
    message: str


class CourseOut(BaseModel):
    id: int
    name: str
    icon: str
    level: int
    level_name: str
    chapters: int
    proposal: ProposalOut | None


class SectionSummary(BaseModel):
    id: int
    number: str | None
    title: str


class DocumentOut(BaseModel):
    id: int
    course_id: int
    title: str
    filename: str
    uploaded_at: datetime
    start_level: int | None
    suggested_level: int | None
    sections: list[SectionSummary]


class SuggestionOut(BaseModel):
    level: int
    level_name: str
    reason: str


class UploadOut(BaseModel):
    document: DocumentOut
    suggestion: SuggestionOut
    current_level: int


class LevelIn(BaseModel):
    level: int = Field(ge=1, le=4)
    reason: Literal["proposal", "manual", "new_chapter"] = "manual"


# --- study ----------------------------------------------------------------

class EasyOut(BaseModel):
    blocks: list[Block]
    glossary: list[GlossaryEntry]
    source: str


class StudyOut(BaseModel):
    id: int
    number: str | None
    title: str
    document_id: int
    document_title: str
    course_id: int
    course_name: str
    level: int
    position: int  # 1-based
    total: int
    prev_id: int | None
    next_id: int | None
    original: list[str]
    easy: EasyOut


class ViewIn(BaseModel):
    mode: Literal["easy", "original"]


# --- questions ------------------------------------------------------------

class OptionOut(BaseModel):
    id: int
    text: str
    image: str | None


class QuestionOut(BaseModel):
    id: int
    prompt: str
    image: str | None
    image_alt: str | None
    mode: Literal["choice", "open"]
    options: list[OptionOut]  # empty for open questions


class LastStrategy(BaseModel):
    choice: str
    label: str


class QuestionsOut(BaseModel):
    section_id: int
    course_id: int
    level: int
    questions: list[QuestionOut]
    ask_strategy: bool  # level 3: ask "Τι σε βοήθησε;" at the end
    last_strategy: LastStrategy | None


class AttemptOut(BaseModel):
    attempt_id: int
    hints_used: int


class HintOut(BaseModel):
    step: int
    text: str
    action: str | None
    section_id: int | None
    choices: list[OptionOut]  # only for step 3: two choices
    example: Block | None = None  # for "replay_example": the everyday example to hear again


class AnswerIn(BaseModel):
    option_id: int | None = None
    text: str | None = Field(None, max_length=1000)


class SelfCheckIn(BaseModel):
    close: bool


class FlagsIn(BaseModel):
    listened: bool | None = None
    opened_section: bool | None = None


class AnswerOut(BaseModel):
    outcome: Literal["correct", "try_again", "self_check", "explained", "not_yet"]
    message: str
    key_point: str | None  # only after the student has tried
    done: bool
    proposal: ProposalOut | None = None


class StrategyIn(BaseModel):
    choice: Literal["listen", "image", "example"]


# --- progress -------------------------------------------------------------

class DayPoint(BaseModel):
    day: date
    questions: int
    hints_per_question: float


class WeekPoint(BaseModel):
    label: str
    start: date
    end: date
    questions: int
    hints_per_question: float | None


class LevelStep(BaseModel):
    at: datetime
    from_level: int
    to_level: int


class CourseProgress(BaseModel):
    id: int
    name: str
    icon: str
    level: int
    level_name: str
    days: list[DayPoint]
    weeks: list[WeekPoint]
    level_history: list[LevelStep]
    message: str


class ProgressOut(BaseModel):
    simulated: bool
    message: str
    courses: list[CourseProgress]


# --- supporter ------------------------------------------------------------

class SupporterIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class SupporterOut(BaseModel):
    id: int
    name: str
    token: str
    created_at: datetime
    active: bool
