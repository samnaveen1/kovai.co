"""
Shared data model that both DocxParser and PdfParser populate.
All downstream modules (metrics, AI, output) work with this model.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Heading:
    level: int          # 1 = H1, 2 = H2, etc.
    text: str
    page: Optional[int] = None


@dataclass
class Paragraph:
    text: str
    style: Optional[str] = None   # e.g. "Normal", "ListBullet"
    page: Optional[int] = None


@dataclass
class DocumentModel:
    """Normalised representation of a parsed document."""
    source_path: str
    file_type: str                          # "docx" or "pdf"
    title: Optional[str] = None
    headings: List[Heading] = field(default_factory=list)
    paragraphs: List[Paragraph] = field(default_factory=list)
    raw_text: str = ""
    page_count: int = 0
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ helpers
    @property
    def all_text_blocks(self) -> List[str]:
        """All non-empty text blocks (headings + paragraphs)."""
        blocks = [h.text for h in self.headings if h.text.strip()]
        blocks += [p.text for p in self.paragraphs if p.text.strip()]
        return blocks

    @property
    def body_text(self) -> str:
        """Full concatenated body text (paragraphs only)."""
        return "\n".join(p.text for p in self.paragraphs if p.text.strip())

    @property
    def word_count_from_raw(self) -> int:
        """Backward-compatible helper used by older tests and callers."""
        return len(self.raw_text.split()) if self.raw_text.strip() else 0
