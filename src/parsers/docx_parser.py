"""
DOCX Parser — extracts structure and content from .docx files using python-docx.
Handles edge cases: empty paragraphs, missing headings, large documents.
"""

import subprocess
import sys
import zipfile
import re
from pathlib import Path
from typing import Optional

try:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Pt
except ImportError:
    raise ImportError(
        "python-docx is required. Install with:  pip install python-docx"
    )

from .document_model import DocumentModel, Heading, Paragraph as ParaModel


# Heading styles that python-docx maps to outline levels
_HEADING_STYLE_PATTERN = re.compile(r"^[Hh]eading\s*(\d)$")
_TITLE_STYLES = {"Title", "Subtitle"}


def _heading_level(style_name: str) -> Optional[int]:
    """Return heading level (1-6) or None if not a heading style."""
    m = _HEADING_STYLE_PATTERN.match(style_name)
    return int(m.group(1)) if m else None


class DocxParser:
    """
    Parses a .docx file into a DocumentModel.

    Usage:
        parser = DocxParser(Path("doc.docx"))
        doc = parser.parse()
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    def parse(self) -> DocumentModel:
        doc_obj = Document(str(self.file_path))

        model = DocumentModel(
            source_path=str(self.file_path),
            file_type="docx",
        )

        # --- core properties / metadata -----------------------------------
        core_props = doc_obj.core_properties
        model.metadata = {
            "author":   core_props.author or "",
            "created":  str(core_props.created) if core_props.created else "",
            "modified": str(core_props.modified) if core_props.modified else "",
            "subject":  core_props.subject or "",
            "keywords": core_props.keywords or "",
        }

        # --- walk paragraphs ----------------------------------------------
        raw_parts = []
        for para in doc_obj.paragraphs:
            text = para.text.strip()
            style_name = para.style.name if para.style else "Normal"

            # skip completely empty lines
            if not text:
                continue

            level = _heading_level(style_name)

            if style_name in _TITLE_STYLES and model.title is None:
                model.title = text

            if level is not None:
                model.headings.append(Heading(level=level, text=text))
                # Also store as paragraph for full-text purposes
                model.paragraphs.append(ParaModel(text=text, style=style_name))
            else:
                model.paragraphs.append(ParaModel(text=text, style=style_name))

            raw_parts.append(text)

        model.raw_text = "\n".join(raw_parts)

        # Use first H1 as title fallback
        if model.title is None and model.headings:
            model.title = next(
                (h.text for h in model.headings if h.level == 1), None
            )

        # --- page count ----------------------------------------------------
        # Prefer DOCX metadata written by Word (usually matches the true page count).
        model.page_count = self._page_count(doc_obj, model.raw_text)

        return model

    def _page_count(self, doc_obj, raw_text: str) -> int:
        """Return the page count from DOCX metadata, else estimate from text."""
        pages = self._pages_from_word_subprocess()
        if pages > 0:
            return pages

        pages = self._pages_from_app_properties()
        if pages > 0:
            return pages

        # Fallback heuristic for environments without Word.
        word_count = len(raw_text.split())
        estimated_pages = round(word_count / 350)
        return max(1, estimated_pages)

    def _pages_from_app_properties(self) -> int:
        """Read the page count from docProps/app.xml when it exists."""
        try:
            with zipfile.ZipFile(self.file_path) as archive:
                if "docProps/app.xml" not in archive.namelist():
                    return 0

                from xml.etree import ElementTree as ET

                root = ET.fromstring(archive.read("docProps/app.xml"))
                for element in root.iter():
                    if element.tag.endswith("Pages") and element.text:
                        try:
                            return int(element.text.strip())
                        except ValueError:
                            return 0
        except Exception:
            return 0

        return 0

    def _pages_from_word_subprocess(self) -> int:
        """Ask Microsoft Word for the rendered page count in a separate process."""
        if sys.platform != "win32":
            return 0

        script = r'''
import sys

try:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    document = word.Documents.Open(sys.argv[1], ReadOnly=True)
    try:
        document.Repaginate()
        print(int(document.ComputeStatistics(2)))
    finally:
        document.Close(False)
        word.Quit()
        pythoncom.CoUninitialize()
except Exception:
    raise
'''

        try:
            completed = subprocess.run(
                [sys.executable, "-c", script, str(self.file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception:
            return 0

        if completed.returncode != 0:
            return 0

        try:
            return max(0, int(completed.stdout.strip()))
        except ValueError:
            return 0
