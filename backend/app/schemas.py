"""Request and response bodies."""

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from app.scheduler import parse_hhmm


class ProfileOut(BaseModel):
    display_name: str
    chunk_minutes: int
    short_break: int
    long_break: int
    max_chunks_per_day: int
    minutes_per_page: float
    ui_prefs: dict


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=60)
    chunk_minutes: int | None = Field(None, ge=15, le=45)
    short_break: int | None = Field(None, ge=0, le=30)
    long_break: int | None = Field(None, ge=5, le=60)
    max_chunks_per_day: int | None = Field(None, ge=1, le=16)
    minutes_per_page: float | None = Field(None, gt=0, le=30)
    ui_prefs: dict | None = None


class WindowIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def valid_time(cls, v: str) -> str:
        parse_hhmm(v)
        return v

    @model_validator(mode="after")
    def end_after_start(self):
        if parse_hhmm(self.end) <= parse_hhmm(self.start):
            raise ValueError("Η ώρα λήξης πρέπει να είναι μετά την ώρα έναρξης")
        return self


class AvailabilityIn(BaseModel):
    windows: list[WindowIn]
    blocked_dates: list[date] = []


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CourseOut(BaseModel):
    id: int
    name: str


class TaskIn(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern="^(study|assignment)$")
    deadline: date
    pages: int | None = Field(None, gt=0, le=5000)
    difficulty: int = Field(2, ge=1, le=3)
    estimated_minutes: float | None = Field(None, gt=0, le=6000)
    steps: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    deadline: date | None = None
    estimated_minutes: float | None = Field(None, gt=0, le=6000)
    steps: list[str] | None = None
    done: bool | None = None


class TaskOut(BaseModel):
    id: int
    course_id: int
    course: str
    title: str
    kind: str
    base_minutes: float
    deadline: date
    steps: list[str]
    done: bool


class GenerateIn(BaseModel):
    start_date: date | None = None
    seed: int | None = None


class ChunkOut(BaseModel):
    id: int
    work_item_id: int
    title: str
    course: str
    kind: str
    day: date
    start: str
    end: str
    minutes: int
    seq: int
    status: str
    help_requests: int
    actual_minutes: float | None


class UnscheduledOut(BaseModel):
    work_item_id: int
    title: str
    minutes: int


class ScheduleOut(BaseModel):
    score: float
    chunks: list[ChunkOut]
    unscheduled: list[UnscheduledOut]


class FinishIn(BaseModel):
    item_done: bool = False  # "the whole task is finished"
    actual_minutes: float | None = Field(None, gt=0, le=600)  # if they forgot to press start
