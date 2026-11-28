"""Find where in the ORIGINAL text of a section a question is answered.

Used by the level 3-4 hints ("it is in the 2nd paragraph", "find the sentence").
No LLM: every sentence gets a score from the words it shares with the question's
key point and `accept` stems (accents and capitals ignored, words compared by their
first letters so "δείγμα" and "δείγματος" match, very common words ignored).
A fixture can set `source_sentence` to choose the sentence by hand.
"""

import re
from dataclasses import dataclass

from app.content.rules import split_sentences, strip_accents
from app.content.schema import QuestionContent
from app.pdf.sections import is_verbatim

STEM = 5
STOP_WORDS = {
    strip_accents(w) for w in (
        "ο η το οι τα του της των τον την τους τις στο στη στην στον στα στις στους "
        "και ή να θα δεν μη μην με σε για από ως που πως πώς ότι αν όταν είναι ήταν "
        "ένα ένας μια μία ενός μιας αυτό αυτή αυτός αυτά αυτές αυτοί πιο πολύ όπως "
        "δηλαδή τότε τόσο όσο κάθε έχει έχουν γίνεται"
    ).split()
}


@dataclass
class Location:
    paragraph: int  # index in the section's original paragraphs
    sentence: int  # index in that paragraph's sentences
    sentences: list[str]  # all sentences of the paragraph, in order


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", strip_accents(text)) if w not in STOP_WORDS]


def stems(text: str) -> set[str]:
    return {w[:STEM] for w in words(text)}


def target_stems(question: QuestionContent) -> set[str]:
    found = stems(question.key_point)
    for group in question.accept:
        for stem in group:
            found |= {w[:STEM] for w in re.findall(r"\w+", strip_accents(stem)) if w not in STOP_WORDS}
    return found


def _matches(sentence_stems: set[str], wanted: set[str]) -> int:
    """Shared stems; a short accept stem ("μικρ") matches any word starting with it."""
    score = 0
    for w in wanted:
        if any(s.startswith(w) or w.startswith(s) for s in sentence_stems if len(min(s, w, key=len)) >= 3):
            score += 1
    return score


def _normal(text: str) -> str:
    return " ".join(re.findall(r"\w+", strip_accents(text)))


def locate(paragraphs: list[str], question: QuestionContent) -> Location | None:
    candidates = [
        (p, s, sentences)
        for p, paragraph in enumerate(paragraphs)
        if not is_verbatim(paragraph)
        for sentences in [split_sentences(paragraph)]
        for s in range(len(sentences))
    ]
    if question.source_sentence:
        wanted = _normal(question.source_sentence)
        for p, s, sentences in candidates:
            if wanted and (wanted in _normal(sentences[s]) or _normal(sentences[s]) in wanted):
                return Location(p, s, sentences)

    wanted = target_stems(question)
    best, best_score = None, 0
    for p, s, sentences in candidates:
        score = _matches(stems(sentences[s]), wanted)
        if score > best_score:
            best, best_score = Location(p, s, sentences), score
    return best
