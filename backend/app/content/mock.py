"""MockProvider: ready-made content from JSON fixtures, rules for everything else.

A fixture section is used when its title (and number, if both have one) matches
the section found in the PDF, so a regenerated PDF still finds its content.
No network calls, no API key.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.content import rules
from app.content.provider import ContentProvider, SectionInput
from app.content.schema import EasyRead, Fixture, FixtureSection, Hint, QuestionContent

FIXTURES_DIR = Path(__file__).parent / "data" / "fixtures"


def normalize_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", rules.strip_accents(title)).strip()


@lru_cache
def load_fixtures(directory: Path = FIXTURES_DIR) -> list[Fixture]:
    return [
        Fixture.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    ]


class MockProvider(ContentProvider):
    def __init__(self, fixtures: list[Fixture] | None = None):
        self.fixtures = fixtures if fixtures is not None else load_fixtures()

    def find(self, section: SectionInput) -> FixtureSection | None:
        title = normalize_title(section.title)
        for fixture in self.fixtures:
            for fs in fixture.sections:
                if normalize_title(fs.title) != title:
                    continue
                if fs.number and section.number and fs.number != section.number:
                    continue
                return fs
        return None

    def simplify(self, section: SectionInput) -> EasyRead:
        fs = self.find(section)
        if fs is None:
            return rules.simplify(section)
        return EasyRead(blocks=fs.easy, glossary=fs.glossary, source="fixture")

    def make_questions(self, section: SectionInput, level: int) -> list[QuestionContent]:
        fs = self.find(section)
        if fs is None:
            return rules.make_questions(section, level)
        return [
            q.model_copy(update={"section_number": q.section_number or fs.number})
            for q in fs.questions
            if level in q.levels
        ]

    def make_hints(self, question: QuestionContent) -> list[Hint]:
        return question.hints or rules.make_hints(question)


def as_section_input(number: str | None, title: str, paragraphs_json: str) -> SectionInput:
    return SectionInput(number=number, title=title, paragraphs=json.loads(paragraphs_json))
