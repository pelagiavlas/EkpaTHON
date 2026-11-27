"""Text extraction from a PDF with pdfplumber.

We keep font size and boldness per line, so headings can be found later.
No OCR: a PDF without a text layer (a scan) is reported with a friendly message.
"""

import io
from collections import Counter
from dataclasses import dataclass

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

MIN_CHARS_PER_PAGE = 20  # less than this on average means the PDF is a picture


class PdfError(Exception):
    """Error with a message that can be shown to the student as is."""


class ScannedPdfError(PdfError):
    def __init__(self):
        super().__init__("Αυτό το PDF είναι φωτογραφία, δοκίμασε άλλο.")


class InvalidPdfError(PdfError):
    def __init__(self):
        super().__init__("Δεν μπορώ να ανοίξω αυτό το αρχείο. Είναι σίγουρα PDF;")


@dataclass
class Line:
    text: str
    size: float  # font size in points
    bold: bool
    page: int  # starts at 1
    top: float  # distance from the top of the page
    bottom: float


def _line_from_chars(text: str, chars: list[dict], page: int, top: float, bottom: float) -> Line:
    sizes = Counter(round(c["size"], 1) for c in chars if c["text"].strip())
    size = sizes.most_common(1)[0][0] if sizes else 0.0
    letters = [c for c in chars if c["text"].strip()]
    bold = bool(letters) and sum("bold" in c["fontname"].lower() for c in letters) > len(letters) / 2
    return Line(text=text.strip(), size=size, bold=bold, page=page, top=top, bottom=bottom)


def extract_lines(data: bytes) -> list[Line]:
    if not data.startswith(b"%PDF"):
        raise InvalidPdfError()
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            lines = []
            for page_no, page in enumerate(pdf.pages, start=1):
                for raw in page.extract_text_lines(return_chars=True):
                    if raw["text"].strip():
                        lines.append(_line_from_chars(raw["text"], raw["chars"], page_no, raw["top"], raw["bottom"]))
            pages = len(pdf.pages)
    except (PDFSyntaxError, ValueError, KeyError, TypeError):
        raise InvalidPdfError()
    if pages == 0:
        raise InvalidPdfError()
    if sum(len(l.text) for l in lines) < MIN_CHARS_PER_PAGE * pages:
        raise ScannedPdfError()
    return lines
