"""The ContentProvider interface: the only way the app gets "smart" content.

Today only MockProvider is used (fixtures + simple rules, no network).
LLMProvider has the same methods and will be filled in later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.content.schema import EasyRead, Hint, QuestionContent


@dataclass
class SectionInput:
    """Only the course text goes to a provider. Never anything about the student."""

    number: str | None
    title: str
    paragraphs: list[str]


class ContentProvider(ABC):
    @abstractmethod
    def simplify(self, section: SectionInput) -> EasyRead:
        """Easy-to-Read version. Never removes or changes concepts, definitions or formulas."""

    @abstractmethod
    def make_questions(self, section: SectionInput, level: int) -> list[QuestionContent]:
        """Comprehension questions for this section and support level."""

    @abstractmethod
    def make_hints(self, question: QuestionContent) -> list[Hint]:
        """The 4 hint steps. Step 4 explains the idea with ANOTHER example, never the answer."""
