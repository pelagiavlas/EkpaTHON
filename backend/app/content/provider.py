"""The ContentProvider interface: the only way the app gets "smart" content.

Today only MockProvider is used (fixtures + simple rules, no network).
LLMProvider has the same methods and will be filled in later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.content.schema import EasyRead, GlossaryEntry, Hint, QuestionContent


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

    @abstractmethod
    def explain_word(self, word: str, section: SectionInput | None = None) -> GlossaryEntry | None:
        """A simple explanation of a word the student does not know, or None if there is none yet.
        Never make one up: None is a fine answer (the word then goes to the reviewer)."""

    # Pictures: a provider (also a future LLM) may only PROPOSE a picture that already exists in the
    # checked library (frontend/public/pictos/library.json). It never creates one. A proposed picture
    # is shown only after a reviewer approves it (see app/content/images.py).
