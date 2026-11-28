"""Rule-based Easy-to-Read for PDFs without a fixture.

What the rules do:
  - every sentence becomes its own paragraph (one idea per paragraph);
  - a sentence longer than MAX_WORDS is split at its commas;
  - glossary terms are marked so the app shows a simple gloss next to them;
  - formulas and table rows are kept exactly as they are.
What they never do: remove words, change terms or rewrite definitions.
"""

import json
import random
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.content.provider import SectionInput
from app.content.schema import Block, EasyRead, GlossaryEntry, Hint, Option, QuestionContent
from app.pdf.sections import is_verbatim

MAX_WORDS = 12
MIN_CLAUSE_WORDS = 3
MAX_RULE_QUESTIONS = 3
GLOSSARY_PATH = Path(__file__).parent / "data" / "glossary.json"
SENTENCE_END = re.compile(r"(?<=[.!;·])\s+(?=[«(\"A-ZΑ-ΩΆ-Ώ0-9])")


@lru_cache
def load_glossary() -> list[dict]:
    entries = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    # Longer forms first, so "σημειακή εκτίμηση" wins over "εκτίμηση".
    return sorted(entries, key=lambda e: -max(len(f) for f in e["forms"]))


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def words(text: str) -> int:
    return len(text.split())


def split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(paragraph) if s.strip()]


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def shorten(sentence: str) -> str:
    """Split a long sentence at its commas into shorter sentences. No word is removed."""
    if words(sentence) <= MAX_WORDS or "," not in sentence:
        return sentence
    end = sentence[-1] if sentence[-1] in ".!;" else "."
    body = sentence.rstrip(".!; ")
    clauses: list[str] = []
    for part in (p.strip() for p in body.split(",")):
        if clauses and (words(part) < MIN_CLAUSE_WORDS or words(clauses[-1]) < MIN_CLAUSE_WORDS):
            clauses[-1] = f"{clauses[-1]}, {part}"
        else:
            clauses.append(part)
    return " ".join(f"{_capitalize(c)}." for c in clauses[:-1]) + f" {_capitalize(clauses[-1])}{end}"


def term_pattern(form: str) -> re.Pattern:
    return re.compile(rf"(?<![\w\[|]){re.escape(form)}(?![\w\]|])", re.IGNORECASE)


def mark_terms(text: str, seen: set[str]) -> str:
    """Mark the first appearance of each glossary term in the section."""
    for entry in load_glossary():
        if entry["term"] in seen:
            continue
        for form in entry["forms"]:
            match = term_pattern(form).search(text)
            if match:
                shown = match.group(0)
                marker = f"[[{shown}]]" if shown == entry["term"] else f"[[{shown}|{entry['term']}]]"
                text = text[: match.start()] + marker + text[match.end():]
                seen.add(entry["term"])
                break
    return text


def simplify(section: SectionInput) -> EasyRead:
    blocks: list[Block] = []
    seen: set[str] = set()
    for paragraph in section.paragraphs:
        if is_verbatim(paragraph):
            blocks.append(Block(type="formula", formula=paragraph))
            continue
        for sentence in split_sentences(paragraph):
            blocks.append(Block(type="text", text=mark_terms(shorten(sentence), seen)))
    glossary_by_term = {e["term"]: e["gloss"] for e in load_glossary()}
    glossary = [GlossaryEntry(term=t, gloss=glossary_by_term[t]) for t in sorted(seen)]
    return EasyRead(blocks=blocks, glossary=glossary, source="rules")


def _find_term_sentence(section: SectionInput, entry: dict) -> tuple[str, str] | None:
    for paragraph in section.paragraphs:
        if is_verbatim(paragraph):
            continue
        for sentence in split_sentences(paragraph):
            for form in entry["forms"]:
                match = term_pattern(form).search(sentence)
                if match and words(sentence) <= 30:
                    blanked = sentence[: match.start()] + "___" + sentence[match.end():]
                    return blanked, match.group(0)
    return None


def make_questions(section: SectionInput, level: int) -> list[QuestionContent]:
    """Fill-the-gap questions from glossary terms found in the section."""
    glossary = load_glossary()
    questions = []
    for entry in glossary:
        found = _find_term_sentence(section, entry)
        if not found:
            continue
        blanked, shown = found
        others = [e["term"] for e in glossary if e["term"] != entry["term"] and e["term"] not in shown]
        rng = random.Random(f"{section.title}|{entry['term']}")
        distractors = rng.sample(others, 2)
        questions.append(QuestionContent(
            key=f"rule-{len(questions) + 1}",
            concept=entry["term"],
            section_number=section.number,
            prompt=f"Ποια λέξη λείπει από την πρόταση; «{blanked}»",
            options=[Option(text=shown), Option(text=distractors[0]), Option(text=distractors[1])],
            accept=[[strip_accents(shown)[:-2] or strip_accents(shown)]],
            key_point=f"Η λέξη που λείπει είναι «{shown}». Σημαίνει: {entry['gloss']}.",
            meta={"term": entry["term"], "gloss": entry["gloss"]},
        ))
        if len(questions) == MAX_RULE_QUESTIONS:
            break
    return questions


def normalize_word(word: str) -> str:
    return re.sub(r"[^\w ]+", "", strip_accents(word)).strip()


def explain_word(word: str) -> GlossaryEntry | None:
    """Look the word up in the general glossary, in any of its forms."""
    wanted = normalize_word(word)
    if not wanted:
        return None
    for entry in load_glossary():
        if any(normalize_word(f) == wanted for f in entry["forms"]) or normalize_word(entry["term"]) == wanted:
            return GlossaryEntry(term=entry["term"], gloss=entry["gloss"])
    return None


def make_hints(question: QuestionContent) -> list[Hint]:
    where = f"στην ενότητα {question.section_number}" if question.section_number else "σε αυτή την ενότητα"
    gloss = question.meta.get("gloss")
    step4 = (
        f"Η λέξη που ψάχνεις σημαίνει: {gloss}. Ποια λέξη έχει αυτό το νόημα;"
        if gloss
        else "Διάβασε ξανά το «Σημαντικό» της ενότητας."
    )
    return [
        Hint(step=1, text=f"Η απάντηση είναι {where}. Θες να την ανοίξεις;", action="open_section"),
        Hint(step=2, text="Διάβασε ξανά την πρόταση. Για ποιο πράγμα μιλάει;"),
        Hint(step=3, text="Διάλεξε ανάμεσα σε δύο."),
        Hint(step=4, text=step4),
    ]
