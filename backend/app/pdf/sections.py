"""Split extracted lines into sections, using the headings.

A line is a heading when it is short and either noticeably larger than the
body text or bold. A leading number ("3.2 Μέση τιμή") becomes the section
number, so hints can say "the answer is in section 3.2".
Formula and table lines are kept as separate, untouched paragraphs.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from app.pdf.extract import Line

HEADING_SIZE_RATIO = 1.15
MAX_HEADING_CHARS = 100
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$")
MATH_CHARS = set("=+−×÷±∑Σ√∫≤≥≠≈^_∞μσ²³₁₂₃ₙ/")
TABLE_GAP = re.compile(r"\S\s{3,}\S|\t|\|")


@dataclass
class Section:
    number: str | None
    title: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs)


def is_verbatim(text: str) -> bool:
    """Formulas and table rows must never be rewritten or merged."""
    stripped = text.strip()
    if not stripped:
        return False
    if TABLE_GAP.search(stripped):
        return True
    # Greek letters used as symbols (μ, σ, Σ) count only when they stand alone ("σ / √n"),
    # never inside a word: "Συμμόρφωση" is a heading, not a formula.
    symbols = sum(ch in MATH_CHARS for ch in stripped if not ch.isalpha())
    letters_as_symbols = sum(1 for w in re.findall(r"\w+", stripped) if len(w) == 1 and w in MATH_CHARS)
    math = symbols + letters_as_symbols
    digits = sum(ch.isdigit() for ch in stripped)
    letters = sum(ch.isalpha() for ch in stripped)
    return "=" in stripped and (math + digits) >= letters / 2 or math >= 3 and letters < 15


def body_size(lines: list[Line]) -> float:
    weights = Counter()
    for line in lines:
        weights[line.size] += len(line.text)
    return weights.most_common(1)[0][0]


def is_heading(line: Line, body: float) -> bool:
    text = line.text
    if len(text) > MAX_HEADING_CHARS or text.endswith((".", ",", ";")) or is_verbatim(text):
        return False
    return line.size >= body * HEADING_SIZE_RATIO or (line.bold and line.size >= body * 0.95)


def _join(previous: str, line: str) -> str:
    if previous.endswith("-"):  # hyphenated word split over two lines
        return previous[:-1] + line
    return f"{previous} {line}"


def split_sections(lines: list[Line]) -> list[Section]:
    if not lines:
        return []
    body = body_size(lines)
    sections: list[Section] = []
    current: Section | None = None
    paragraph = ""
    prev: Line | None = None

    def flush():
        nonlocal paragraph
        if paragraph and current is not None:
            current.paragraphs.append(paragraph.strip())
        paragraph = ""

    for line in lines:
        if is_heading(line, body):
            # Headings broken over two lines (same style, right below) are one heading.
            if prev is not None and current is not None and not paragraph and not current.paragraphs \
                    and is_heading(prev, body) and prev.page == line.page and line.top - prev.bottom < line.size:
                current.title = f"{current.title} {line.text}"
            else:
                flush()
                match = NUMBERED.match(line.text)
                number, title = (match.group(1), match.group(2)) if match else (None, line.text)
                current = Section(number, title.strip())
                sections.append(current)
            prev = line
            continue

        if current is None:
            current = Section(None, "Εισαγωγή")
            sections.append(current)

        new_paragraph = (
            not paragraph
            or prev is None
            or prev.page != line.page
            or line.top - prev.bottom > line.size * 0.8  # visible gap between paragraphs
            or is_verbatim(line.text)
            or is_verbatim(paragraph.splitlines()[-1])
        )
        if new_paragraph:
            flush()
            paragraph = line.text
        else:
            paragraph = _join(paragraph, line.text)
        prev = line
    flush()
    return [s for s in sections if s.paragraphs or s.number]
