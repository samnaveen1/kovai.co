"""
PDF Parser — extracts structure and content from .pdf files.
Primary library: PyMuPDF (fitz). Falls back to pdfminer.six if not available.
"""

from pathlib import Path
from typing import List

from .document_model import DocumentModel, Heading, Paragraph as ParaModel


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 1: PyMuPDF (pip install pymupdf)
# ──────────────────────────────────────────────────────────────────────────────
def _parse_with_pymupdf(file_path: Path, model: DocumentModel) -> DocumentModel:
    import fitz  # PyMuPDF

    pdf = fitz.open(str(file_path))
    model.page_count = len(pdf)

    raw_parts: List[str] = []

    for page_num, page in enumerate(pdf, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                line_text = " ".join(
                    span["text"] for span in line.get("spans", [])
                ).strip()
                if not line_text:
                    continue

                # Heuristic: large / bold font → heading
                spans = line.get("spans", [])
                avg_size = (
                    sum(s["size"] for s in spans) / len(spans) if spans else 12
                )
                is_bold = any(s.get("flags", 0) & 2**4 for s in spans)  # bold flag

                if avg_size >= 16 or (avg_size >= 13 and is_bold):
                    level = 1 if avg_size >= 18 else 2
                    model.headings.append(
                        Heading(level=level, text=line_text, page=page_num)
                    )
                    model.paragraphs.append(
                        ParaModel(text=line_text, style=f"Heading{level}", page=page_num)
                    )
                else:
                    model.paragraphs.append(
                        ParaModel(text=line_text, style="Normal", page=page_num)
                    )

                raw_parts.append(line_text)

    model.raw_text = "\n".join(raw_parts)
    model.title = model.headings[0].text if model.headings else None
    pdf.close()
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 2: pdfminer.six (pip install pdfminer.six)  – plain text fallback
# ──────────────────────────────────────────────────────────────────────────────
def _parse_with_pdfminer(file_path: Path, model: DocumentModel) -> DocumentModel:
    from pdfminer.high_level import extract_text, extract_pages
    from pdfminer.layout import LTPage

    text = extract_text(str(file_path))
    pages = list(extract_pages(str(file_path)))
    model.page_count = len(pages)
    model.raw_text = text

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Very basic heuristic: short ALL-CAPS lines → heading
        if stripped.isupper() and len(stripped.split()) <= 10:
            model.headings.append(Heading(level=1, text=stripped))
        model.paragraphs.append(ParaModel(text=stripped, style="Normal"))

    model.title = model.headings[0].text if model.headings else None
    return model


class PdfParser:
    """
    Parses a PDF file into a DocumentModel.
    Tries PyMuPDF first (richer structure), falls back to pdfminer.six.

    Usage:
        parser = PdfParser(Path("doc.pdf"))
        doc = parser.parse()
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    def parse(self) -> DocumentModel:
        model = DocumentModel(
            source_path=str(self.file_path),
            file_type="pdf",
        )

        try:
            return _parse_with_pymupdf(self.file_path, model)
        except ImportError:
            pass

        try:
            return _parse_with_pdfminer(self.file_path, model)
        except ImportError:
            raise ImportError(
                "No PDF library found. Install one of:\n"
                "  pip install pymupdf          # recommended\n"
                "  pip install pdfminer.six     # fallback"
            )
