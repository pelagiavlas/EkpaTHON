"""EkpaProvider: the only way the app gets a student's courses from the university.

Same pattern as ContentProvider: today only MockEkpaProvider is used (JSON fixtures, no network).
EclassProvider has the same methods and will be filled in later.
The app never asks for and never stores the student's university password.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class EkpaCourse:
    id: str  # the university's id for the course
    name: str
    icon: str = "book"


@dataclass
class EkpaSlot:
    course_id: str
    weekday: int  # 0 = Monday
    start: str  # "HH:MM"
    end: str
    room: str


@dataclass
class EkpaDocument:
    id: str
    course_id: str
    title: str
    filename: str
    added_on: date
    content: bytes  # the PDF itself


@dataclass
class EkpaUnit:
    """One unit of the syllabus, in teaching order, with the week it is planned for."""

    number: str | None
    title: str
    week: int


class EkpaProvider(ABC):
    @abstractmethod
    def courses(self) -> list[EkpaCourse]:
        """The courses the student is enrolled in."""

    @abstractmethod
    def timetable(self) -> list[EkpaSlot]:
        """Weekly timetable: day, time and room of every class."""

    @abstractmethod
    def documents(self, course_id: str) -> list[EkpaDocument]:
        """Documents the teacher has posted (only PDFs are imported)."""

    @abstractmethod
    def syllabus(self, course_id: str) -> list[EkpaUnit]:
        """Units in teaching order, each with its planned week."""

    @abstractmethod
    def semester_start(self) -> date:
        """Monday of week 1 of the semester."""
