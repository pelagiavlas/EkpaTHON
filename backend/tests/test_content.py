"""MockProvider, fixtures and rule-based Easy-to-Read."""

import re
from pathlib import Path

import pytest

from app.content import get_provider
from app.content.llm import LLMProvider
from app.content.mock import MockProvider, load_fixtures
from app.content.provider import SectionInput
from app.content.rules import shorten, simplify
from app.learning.answers import matches_open_answer
from app.pdf import pdf_to_sections
from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf

TERM = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


@pytest.fixture(scope="module")
def demo_sections():
    return [SectionInput(s.number, s.title, s.paragraphs) for s in pdf_to_sections(build_pdf(CHAPTER))]


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.delenv("CONTENT_PROVIDER", raising=False)
    assert isinstance(get_provider(), MockProvider)


def test_llm_provider_is_an_empty_placeholder(monkeypatch):
    monkeypatch.setenv("CONTENT_PROVIDER", "llm")
    provider = get_provider()
    assert isinstance(provider, LLMProvider)
    with pytest.raises(NotImplementedError):
        provider.simplify(SectionInput("1", "x", ["y"]))


def test_fixture_is_valid_and_complete():
    fixture = load_fixtures()[0]
    for section in fixture.sections:
        terms = {m.group(2) or m.group(1) for b in section.easy for m in TERM.finditer(b.text)}
        assert terms <= {g.term for g in section.glossary}, section.title  # every marked term has a gloss
        for q in section.questions:
            assert len(q.hints) == 4 and q.key_point
            assert q.options[0].text not in q.hints[3].text  # step 4 never gives the answer


def test_every_demo_section_matches_the_fixture(demo_sections):
    provider = MockProvider()
    assert all(provider.find(s) is not None for s in demo_sections)
    assert all(provider.simplify(s).source == "fixture" for s in demo_sections)


def test_fixture_keeps_the_formula_exactly(demo_sections):
    section = next(s for s in demo_sections if s.number == "3.3")
    formula = next(p for p in section.paragraphs if "√n" in p)
    easy = MockProvider().simplify(section)
    assert formula in [b.formula for b in easy.blocks if b.type == "formula"]


def test_fixture_easy_sentences_are_short():
    for section in load_fixtures()[0].sections:
        for block in section.easy:
            if block.type in ("text", "key"):
                for sentence in re.split(r"(?<=[.;:])\s+", TERM.sub(r"\1", block.text)):
                    assert len(sentence.split()) <= 14, sentence


def test_questions_from_fixture(demo_sections):
    section = next(s for s in demo_sections if s.number == "3.4")
    questions = MockProvider().make_questions(section, level=1)
    assert [q.key for q in questions] == ["q7", "q8"]
    assert questions[0].section_number == "3.4"


# --- rules for PDFs without a fixture ---------------------------------------

UNKNOWN = SectionInput("2.1", "Μέτρα διασποράς", [
    "Η διασπορά και η τυπική απόκλιση περιγράφουν πόσο απέχουν οι τιμές από τη μέση τιμή, "
    "ενώ το εύρος δείχνει τη διαφορά μεγίστου και ελαχίστου, και χρησιμοποιείται συχνά σε περιγραφικές αναλύσεις.",
    "s² = Σ(xᵢ − x̄)² / (n − 1)",
    "Ένα δείγμα με μικρή τυπική απόκλιση έχει τιμές κοντά στη μέση τιμή.",
])


def test_rules_keep_formula_and_mark_terms():
    easy = simplify(UNKNOWN)
    assert easy.source == "rules"
    assert "s² = Σ(xᵢ − x̄)² / (n − 1)" in [b.formula for b in easy.blocks]
    text = " ".join(b.text for b in easy.blocks)
    assert "[[διασπορά]]" in text and "[[τυπική απόκλιση]]" in text
    assert {"διασπορά", "τυπική απόκλιση", "μέση τιμή", "δείγμα"} <= {g.term for g in easy.glossary}


def test_rules_never_drop_words():
    easy = simplify(UNKNOWN)
    original = re.findall(r"\w+", UNKNOWN.paragraphs[0].lower())
    simplified = re.findall(r"\w+", TERM.sub(r"\1", " ".join(b.text for b in easy.blocks[:2])).lower())
    assert sorted(original) == sorted(simplified)


def test_long_sentence_is_split():
    long = "Η στατιστική μελετά δεδομένα, που συλλέγονται από έρευνες σε πολλούς ανθρώπους, και βοηθά να βγάλουμε συμπεράσματα."
    assert shorten(long).count(".") >= 2


def test_unknown_pdf_still_gets_questions_with_four_hints():
    provider = MockProvider()
    questions = provider.make_questions(UNKNOWN, level=2)
    assert questions
    for q in questions:
        hints = provider.make_hints(q)
        assert [h.step for h in hints] == [1, 2, 3, 4]
        assert "2.1" in hints[0].text
        assert "___" in q.prompt


# --- open answers -------------------------------------------------------------

@pytest.mark.parametrize("answer, ok", [
    ("μικραίνει", True),
    ("Γίνεται πιο ΣΤΕΝΟ", True),
    ("μεγαλώνει", False),
    ("είναι ίδιο", False),
])
def test_open_answer_check(answer, ok):
    q7 = next(q for s in load_fixtures()[0].sections for q in s.questions if q.key == "q7")
    assert matches_open_answer(q7, answer) is ok


def test_open_answer_matches_word_starts_only():
    q2 = next(q for s in load_fixtures()[0].sections for q in s.questions if q.key == "q2")
    assert not matches_open_answer(q2, "είναι λάθος")  # "ναι" inside "είναι" does not count
    assert matches_open_answer(q2, "ναι")


def test_demo_pdf_in_repo_matches_script():
    pdf = Path(__file__).resolve().parent.parent / "demo" / "kefalaio-3-diastima-empistosynis.pdf"
    titles = [s.title for s in pdf_to_sections(pdf.read_bytes())]
    assert titles == [s.title for s in pdf_to_sections(build_pdf(CHAPTER))]
