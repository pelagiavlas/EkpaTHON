import pytest

from app.pdf import InvalidPdfError, ScannedPdfError, extract_lines, is_verbatim, pdf_to_sections
from scripts.pdfgen import build_image_only_pdf, build_pdf

LONG = (
    "Η στατιστική είναι η επιστήμη που συλλέγει, οργανώνει και ερμηνεύει δεδομένα. "
    "Τη χρησιμοποιούμε για να βγάζουμε συμπεράσματα από αριθμούς που μετράμε στον κόσμο γύρω μας."
)


def test_extracts_greek_text():
    lines = extract_lines(build_pdf([("p", "Η μέση τιμή είναι ένα μέτρο θέσης.")]))
    assert "Η μέση τιμή είναι ένα μέτρο θέσης." in [l.text for l in lines]


def test_splits_on_numbered_headings():
    pdf = build_pdf([
        ("h1", "1 Εισαγωγή στη Στατιστική"),
        ("p", LONG),
        ("h2", "1.1 Πληθυσμός και δείγμα"),
        ("p", "Πληθυσμός είναι όλα τα άτομα που μας ενδιαφέρουν."),
        ("h2", "1.2 Μέση τιμή"),
        ("p", "Η μέση τιμή είναι το άθροισμα των τιμών διά το πλήθος τους."),
    ])
    sections = pdf_to_sections(pdf)
    assert [(s.number, s.title) for s in sections] == [
        ("1", "Εισαγωγή στη Στατιστική"),
        ("1.1", "Πληθυσμός και δείγμα"),
        ("1.2", "Μέση τιμή"),
    ]
    assert sections[2].paragraphs == ["Η μέση τιμή είναι το άθροισμα των τιμών διά το πλήθος τους."]


def test_wrapped_lines_join_into_one_paragraph():
    sections = pdf_to_sections(build_pdf([("h1", "Κεφάλαιο"), ("p", LONG * 2)]))
    assert len(sections[0].paragraphs) == 1
    assert sections[0].paragraphs[0].startswith("Η στατιστική είναι")


def test_unnumbered_bold_heading():
    sections = pdf_to_sections(build_pdf([("h2", "Διασπορά"), ("p", LONG)]))
    assert sections[0].number is None and sections[0].title == "Διασπορά"


def test_text_before_first_heading_goes_to_intro():
    sections = pdf_to_sections(build_pdf([("p", LONG), ("h1", "2 Μέτρα θέσης"), ("p", LONG)]))
    assert sections[0].title == "Εισαγωγή"
    assert sections[1].number == "2"


def test_formula_kept_as_its_own_paragraph():
    pdf = build_pdf([
        ("h1", "Μέση τιμή"),
        ("p", "Τη βρίσκουμε με τον τύπο:"),
        ("formula", "x̄ = (x₁ + x₂ + … + xₙ) / n"),
        ("p", "όπου n είναι το πλήθος των τιμών."),
    ])
    paragraphs = pdf_to_sections(pdf)[0].paragraphs
    assert "x̄ = (x₁ + x₂ + … + xₙ) / n" in paragraphs


def test_sections_across_pages():
    pdf = build_pdf([("h1", "1 Πρώτο"), ("p", LONG), ("page", ""), ("h1", "2 Δεύτερο"), ("p", LONG)])
    assert [s.number for s in pdf_to_sections(pdf)] == ["1", "2"]


def test_scanned_pdf_gets_friendly_message():
    with pytest.raises(ScannedPdfError) as err:
        extract_lines(build_image_only_pdf())
    assert "φωτογραφία" in str(err.value)


@pytest.mark.parametrize("data", [b"hello", b"%PDF-1.4 broken"])
def test_not_a_pdf(data):
    with pytest.raises(InvalidPdfError):
        extract_lines(data)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("x̄ = (x₁ + x₂ + … + xₙ) / n", True),
        ("s² = Σ(xᵢ − x̄)² / (n − 1)", True),
        ("Βαθμός    Συχνότητα    Ποσοστό", True),
        ("Η μέση τιμή είναι ένα μέτρο θέσης.", False),
        ("Το 30% των φοιτητών απάντησε ναι.", False),
    ],
)
def test_is_verbatim(text, expected):
    assert is_verbatim(text) is expected
