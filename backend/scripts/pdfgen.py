"""Small helper to build Greek PDFs (demo material and tests) with fpdf2."""

from pathlib import Path

from fpdf import FPDF

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def build_pdf(blocks: list[tuple[str, str]]) -> bytes:
    """blocks: ("h1" | "h2" | "p" | "formula" | "page", text)."""
    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    styles = {"h1": ("B", 16, 9), "h2": ("B", 13, 8), "p": ("", 11, 6), "formula": ("", 11, 7)}
    for kind, text in blocks:
        if kind == "page":
            pdf.add_page()
            continue
        style, size, height = styles[kind]
        pdf.set_font("DejaVu", style, size)
        align = "C" if kind == "formula" else "L"
        pdf.multi_cell(0, height, text, align=align, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    return bytes(pdf.output())


def build_image_only_pdf() -> bytes:
    """A page with only drawn shapes: behaves like a scanned PDF (no text layer)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(120, 120, 120)
    pdf.rect(20, 20, 170, 250, style="F")
    return bytes(pdf.output())
