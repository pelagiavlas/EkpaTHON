"""Request and response bodies of the API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.content.schema import Block, GlossaryEntry

ICONS = ("chart", "book", "flask", "calculator", "brain", "globe", "scale", "code")


# --- settings -------------------------------------------------------------

class Settings(BaseModel):
    """Accessibility settings. Only what the student chose: no diagnosis.
    A support level NEVER changes these."""

    fontScale: float = Field(1.0, ge=1.0, le=2.0)
    lineSpacing: float = Field(1.6, ge=1.4, le=2.4)
    highContrast: bool = False
    reducedMotion: bool = False
    readAloud: bool = True
    autoRead: bool = True
    voiceRate: float = Field(0.9, ge=0.5, le=1.5)
    onboarded: bool = False  # the one-time "you can change this in Settings" tip was closed


# --- milestones and support levels ---------------------------------------

class MilestoneOut(BaseModel):
    key: str
    text: str
    created_at: datetime


class ProposalOut(BaseModel):
    reason: str
    from_level: int
    to_level: int
    message: str


class SupportOut(BaseModel):
    section_id: int
    level: int
    level_name: str
    proposal: ProposalOut | None
    new_milestones: list[MilestoneOut] = []


class LevelIn(BaseModel):
    level: int = Field(ge=1, le=4)
    reason: Literal["proposal", "manual"] = "manual"


# --- courses and chapters -------------------------------------------------

class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: Literal[ICONS] = "book"  # type: ignore[valid-type]


class CourseOut(BaseModel):
    id: int
    name: str
    icon: str
    chapters: int
    proposals: int  # sections with a proposal waiting for an answer
    from_eclass: bool = False
    teaching: str | None = None  # "Στο μάθημα: 3.4 ... (εβδομάδα 9)"
    studied: int = 0  # sections with material the student has opened or answered
    with_material: int = 0
    next_section_id: int | None = None
    next_text: str | None = None  # "Θες να δεις την ενότητα 3.3...;"


class SectionSummary(BaseModel):
    id: int
    number: str | None
    title: str
    level: int
    level_name: str
    has_proposal: bool


class DocumentOut(BaseModel):
    id: int
    course_id: int
    title: str
    filename: str
    uploaded_at: datetime
    sections: list[SectionSummary]
    concepts_known: int = 0  # "Ξέρεις ήδη 3 από τις 5 έννοιες αυτού του κεφαλαίου"
    concepts_total: int = 0


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
    support: SupportOut
    position: int  # 1-based
    total: int
    prev_id: int | None
    next_id: int | None
    original: list[str]
    easy: EasyOut
    demo: bool  # DEMO_MODE=true: the level preview for the presentation is offered


class VisitOut(BaseModel):
    visit_id: int


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
    exam: bool
    questions: list[QuestionOut]
    ask_strategy: bool  # level 3: ask "Τι σε βοήθησε;" at the end
    last_strategy: LastStrategy | None


class AttemptOut(BaseModel):
    attempt_id: int
    new_milestones: list[MilestoneOut] = []


class HintOut(BaseModel):
    kind: Literal["explain", "search"]
    step: int  # explain: 1-4, search: 1-3
    text: str
    action: Literal["open_section", "replay_example", "open_original", "highlight_paragraph", "pick_sentence"] | None
    section_id: int | None
    paragraph: int | None = None  # index in the original paragraphs (search steps 2-3)
    sentences: list[str] = []  # search step 3: the sentences of that paragraph, each one a button
    choices: list[OptionOut] = []  # explain step 3: two choices
    example: Block | None = None  # "replay_example": the everyday example to hear again
    fell_back: bool = False  # the first explaining hint after searching


class PickIn(BaseModel):
    sentence: int = Field(ge=0)


class PickOut(BaseModel):
    correct: bool
    message: str
    fallback_hint: HintOut | None = None
    new_milestones: list[MilestoneOut] = []


class AnswerIn(BaseModel):
    option_id: int | None = None
    text: str | None = Field(None, max_length=2000)


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
    new_milestones: list[MilestoneOut] = []


class StrategyIn(BaseModel):
    choice: Literal["listen", "image", "example"]


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class NoteOut(BaseModel):
    id: int
    kind: str
    text: str
    created_at: datetime


class KeyPointsOut(BaseModel):
    """Level 4: shown only after the student has written their own key points."""

    attempt_id: int
    key_points: list[str]


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


class ConceptOut(BaseModel):
    """How well a concept is known, in words only. The probability itself never leaves the server."""

    concept: str
    label_key: Literal["learning", "almost", "known"]
    label: str


class SectionLevel(BaseModel):
    id: int
    label: str
    level: int
    level_name: str


class ChapterLevels(BaseModel):
    title: str
    sections: list[SectionLevel]


class LevelStep(BaseModel):
    at: datetime
    section: str
    from_level: int
    to_level: int


class CourseProgress(BaseModel):
    id: int
    name: str
    icon: str
    chapters: list[ChapterLevels]
    days: list[DayPoint]
    weeks: list[WeekPoint]
    level_history: list[LevelStep]
    message: str
    concepts: list[ConceptOut] = []


class ProgressOut(BaseModel):
    simulated: bool
    message: str
    courses: list[CourseProgress]
    milestones: list[MilestoneOut]


# --- supporter ------------------------------------------------------------

class SupporterIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class SupporterOut(BaseModel):
    id: int
    name: str
    token: str
    created_at: datetime
    active: bool


# --- eClass and "Σήμερα" -------------------------------------------------------

class NextClassOut(BaseModel):
    course_id: int
    course_name: str
    day: date
    weekday: str
    is_today: bool
    start: str
    end: str
    room: str
    phase: Literal["before", "during", "later"]


class BeforeClassOut(BaseModel):
    course_id: int
    course_name: str
    unit_id: int
    unit_title: str
    section_id: int | None  # None: the material is not on eClass yet
    minutes: int | None


class UnitChoice(BaseModel):
    unit_id: int
    title: str


class AfterClassOut(BaseModel):
    course_id: int
    course_name: str
    class_date: date
    when: str  # "Σήμερα" or "Την Τρίτη"
    predicted: UnitChoice | None
    units: list[UnitChoice]


class NewMaterialOut(BaseModel):
    document_id: int
    course_name: str
    title: str
    added_on: date


class TodayOut(BaseModel):
    now: datetime
    demo: bool
    simulated_eclass: bool
    next_class: NextClassOut | None
    before: BeforeClassOut | None
    after: AfterClassOut | None
    new_material: list[NewMaterialOut]


class ConfirmIn(BaseModel):
    course_id: int
    class_date: date
    unit_id: int | None = None
    status: Literal["done", "unknown"] = "done"


class ConfirmOut(BaseModel):
    status: str
    unit_title: str | None
    section_id: int | None  # for "Θες 2 ερωτήσεις...;"
    has_questions: bool


class PlanUnitOut(BaseModel):
    unit_id: int
    title: str
    week: int
    taught: bool
    section_id: int | None
    studied: bool


class NextStepOut(BaseModel):
    section_id: int
    text: str


class PlanOut(BaseModel):
    teaching: dict | None
    teaching_from: Literal["confirmed", "plan"]
    week: int
    units: list[PlanUnitOut]
    studied: int
    with_material: int
    next: NextStepOut | None
    simulated_eclass: bool


class TeachingIn(BaseModel):
    unit_id: int
