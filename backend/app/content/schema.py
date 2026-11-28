"""Shape of all "smart" content: Easy-to-Read text, questions and hints.

Fixtures, the rule-based fallback and (later) the LLM must all produce these
models, so every source is validated the same way.

In text, a glossary term is written as [[term]] or [[shown form|term]],
e.g. "Ρωτάμε λίγους. Αυτοί είναι το [[δείγμα]]." or "[[δείγματος|δείγμα]]".
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Symbol(BaseModel):
    symbol: str
    meaning: str


class Block(BaseModel):
    type: Literal["text", "example", "image", "formula", "key"]
    text: str = ""
    title: str | None = None
    image: str | None = None  # pictogram name (frontend/public/pictos/<name>.svg)
    alt: str | None = None
    formula: str | None = None  # kept exactly as in the original
    symbols: list[Symbol] = []
    essential: bool = True  # picture for a hard idea: level 1 shows every picture, level 2 only these

    @model_validator(mode="after")
    def check(self):
        if self.type == "formula" and not self.formula:
            raise ValueError("formula block needs `formula`")
        if self.type == "image" and not (self.image and self.alt):
            raise ValueError("image block needs `image` and `alt`")
        if self.type in ("text", "example", "key") and not self.text:
            raise ValueError(f"{self.type} block needs `text`")
        return self


class GlossaryEntry(BaseModel):
    term: str
    gloss: str


class EasyRead(BaseModel):
    blocks: list[Block]
    glossary: list[GlossaryEntry] = []
    source: Literal["fixture", "rules", "llm"]


class Option(BaseModel):
    text: str
    image: str | None = None


class Hint(BaseModel):
    step: int = Field(ge=1, le=4)
    text: str
    action: Literal["open_section", "replay_example"] | None = None


class QuestionContent(BaseModel):
    key: str  # stable id inside the section
    concept: str | None = None  # the idea the question checks, e.g. "μέγεθος δείγματος" (knowledge tracing)
    section_number: str | None = None
    prompt: str
    image: str | None = None
    image_alt: str | None = None
    options: list[Option] = Field(min_length=2, max_length=3)  # options[0] is the right one
    accept: list[list[str]] = []  # open answers: any group whose stems all appear
    key_point: str  # shown only AFTER the student has tried
    hints: list[Hint] = []  # the 4 hints that explain (levels 1-2, and fallback at 3-4)
    levels: list[int] = [1, 2, 3, 4]
    # Levels 3-4 send the student into the original text. Optional, to set by hand:
    source_sentence: str | None = None  # the sentence of the original that answers the question
    source_hint: str | None = None  # "τι γίνεται όταν μεγαλώνει το n" in "Βρες την πρόταση που λέει ..."
    meta: dict = {}

    @field_validator("hints")
    @classmethod
    def four_steps(cls, hints: list[Hint]) -> list[Hint]:
        if hints and [h.step for h in hints] != [1, 2, 3, 4]:
            raise ValueError("hints must be the 4 steps in order")
        return hints


class FixtureSection(BaseModel):
    number: str | None = None
    title: str
    easy: list[Block]
    glossary: list[GlossaryEntry] = []
    questions: list[QuestionContent] = []


class Fixture(BaseModel):
    id: str
    title: str
    sections: list[FixtureSection]
