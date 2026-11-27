"""Database tables. Single local student: the app runs on their own device,
so there is no login and nothing personal leaves it."""

from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    display_name: str = "Φοιτητής"
    chunk_minutes: int = 30
    short_break: int = 5
    long_break: int = 15
    max_chunks_per_day: int = 6
    minutes_per_page: float = 3.0
    ui_prefs: str = "{}"  # JSON: font size, dyslexia font, line spacing, reduced motion


class AvailabilityWindow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    weekday: int  # 0 = Monday
    start: str  # "HH:MM"
    end: str


class BlockedDate(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    day: date = Field(unique=True)


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class WorkItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id")
    title: str
    kind: str  # "study" | "assignment"
    base_minutes: float  # estimate before the personal multiplier
    deadline: date
    pages: int | None = None
    difficulty: int = 2
    steps: str = "[]"  # JSON list of approved steps
    done: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class KindStat(SQLModel, table=True):
    """Per task kind: prediction multiplier and fading-support state."""

    kind: str = Field(primary_key=True)
    multiplier: float = 1.0
    samples: int = 0
    support_level: int = 3
    success_streak: int = 0


class Chunk(SQLModel, table=True):
    """A planned study block. Started/finished times are the data for the
    prediction model (StudyBuddy's ScheduledTask kept only LocalTime)."""

    id: int | None = Field(default=None, primary_key=True)
    work_item_id: int = Field(foreign_key="workitem.id", index=True)
    kind: str  # "study" | "revision" | "assignment"
    day: date = Field(index=True)
    start_min: int
    minutes: int  # planned length
    seq: int = 1  # order within its work item
    status: str = "upcoming"  # upcoming | in_progress | done | missed
    started_at: datetime | None = None
    finished_at: datetime | None = None
    actual_minutes: float | None = None
    help_requests: int = 0
