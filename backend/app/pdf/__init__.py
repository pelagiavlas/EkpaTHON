from .extract import InvalidPdfError, Line, PdfError, ScannedPdfError, extract_lines
from .sections import Section, is_verbatim, split_sections


def pdf_to_sections(data: bytes) -> list[Section]:
    return split_sections(extract_lines(data))
