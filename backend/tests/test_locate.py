"""Finding the target sentence in the ORIGINAL text of the PDF (no LLM)."""

import pytest

from app.content.mock import load_fixtures
from app.content.schema import Option, QuestionContent
from app.learning.locate import locate, stems
from app.pdf import pdf_to_sections
from scripts.make_demo_pdf import CHAPTER
from scripts.pdfgen import build_pdf


@pytest.fixture(scope="module")
def demo():
    sections = {s.number: s for s in pdf_to_sections(build_pdf(CHAPTER))}
    questions = {q.key: (fs.number, q) for fs in load_fixtures()[0].sections for q in fs.questions}
    return sections, questions


def question(key_point: str, accept=None, source=None) -> QuestionContent:
    return QuestionContent(key="t", prompt="?", options=[Option(text="a"), Option(text="b")],
                           key_point=key_point, accept=accept or [], source_sentence=source)


def test_stems_ignore_accents_case_and_common_words():
    assert stems("Το ΔΕΊΓΜΑ και τα δείγματα") == {"δειγμ"}


def test_finds_the_n_sentence_in_the_demo_pdf(demo):
    sections, questions = demo
    number, q7 = questions["q7"]
    loc = locate(sections[number].paragraphs, q7.model_copy(update={"source_sentence": None}))  # automatic
    assert loc.paragraph == 0
    assert loc.sentences[loc.sentence].startswith("Επομένως, όσο αυξάνεται το n")


def test_automatic_matches_the_hand_picked_sentence_for_most_demo_questions(demo):
    sections, questions = demo
    same = 0
    for number, q in questions.values():
        manual = locate(sections[number].paragraphs, q)
        auto = locate(sections[number].paragraphs, q.model_copy(update={"source_sentence": None}))
        same += (manual.paragraph, manual.sentence) == (auto.paragraph, auto.sentence)
    assert same >= 7  # 7 of 8; source_sentence is there for the rest


def test_source_sentence_wins(demo):
    sections, questions = demo
    number, q8 = questions["q8"]
    loc = locate(sections[number].paragraphs, q8)
    assert loc.sentences[loc.sentence].startswith("Αντίθετα, η αύξηση του επιπέδου εμπιστοσύνης")


def test_formulas_are_never_the_target(demo):
    sections, _ = demo
    paragraphs = sections["3.3"].paragraphs
    loc = locate(paragraphs, question("x̄ ± z · σ / √n"))
    assert loc is None or "±" not in paragraphs[loc.paragraph][:20]


def test_pdf_without_fixture():
    pdf = build_pdf([
        ("h1", "2.1 Μέτρα διασποράς"),
        ("p", "Η διασπορά μετρά πόσο απλώνονται οι τιμές. Τη συμβολίζουμε με s²."),
        ("p", "Η τυπική απόκλιση είναι η τετραγωνική ρίζα της διασποράς. Έχει τις ίδιες μονάδες με τα δεδομένα."),
    ])
    section = pdf_to_sections(pdf)[0]
    loc = locate(section.paragraphs, question("Η τυπική απόκλιση είναι η ρίζα της διασποράς.", [["ριζα"]]))
    assert (loc.paragraph, loc.sentence) == (1, 0)


def test_nothing_in_common_gives_no_target():
    assert locate(["Ο καιρός σήμερα είναι καλός."], question("μέση τιμή δείγματος")) is None
