"""
Metrics Extractor — calculates structural and content-level metrics
from a DocumentModel. All values are pure Python; no AI needed here.
"""

import re
from collections import Counter
from typing import Dict, Any

from src.parsers.document_model import DocumentModel


class MetricsExtractor:
    """
    Derives quantitative metrics from a parsed DocumentModel.

    Usage:
        extractor = MetricsExtractor(document)
        metrics = extractor.extract()   # returns dict
    """

    def __init__(self, document: DocumentModel):
        self.doc = document

    # ------------------------------------------------------------------ public
    def extract(self) -> Dict[str, Any]:
        raw = self.doc.raw_text
        paragraphs = [p for p in self.doc.paragraphs if p.text.strip()]
        headings = self.doc.headings

        word_count       = self._word_count(raw)
        sentence_count   = self._sentence_count(raw)
        char_count       = len(raw.replace("\n", " "))
        avg_words_para   = round(word_count / max(len(paragraphs), 1), 1)
        avg_words_sent   = round(word_count / max(sentence_count, 1), 1)
        heading_depth    = max((h.level for h in headings), default=0)
        heading_dist     = self._heading_distribution(headings)
        link_count       = self._count_links(raw)
        code_block_count = self._count_code_blocks(raw)
        list_item_count  = self._count_list_items(paragraphs)
        unique_words     = len(set(re.findall(r'\b\w+\b', raw.lower())))
        lexical_density  = round(unique_words / max(word_count, 1) * 100, 1)
        empty_sections   = self._empty_section_count(headings, paragraphs)
        duplicate_heads  = self._duplicate_headings(headings)
        image_count       = getattr(self.doc, "images_count", 0)

        return {
            # basic counts
            "page_count":            self.doc.page_count,
            "word_count":            word_count,
            "character_count":       char_count,
            "sentence_count":        sentence_count,
            "paragraph_count":       len(paragraphs),
            "heading_count":         len(headings),

            # averages
            "avg_words_per_paragraph":  avg_words_para,
            "avg_words_per_sentence":   avg_words_sent,

            # structure
            "max_heading_depth":     heading_depth,
            "heading_distribution":  heading_dist,
            "list_item_count":       list_item_count,
            "link_count":            link_count,
            "code_block_count":      code_block_count,
            "image_count":           image_count,

            # quality signals
            "unique_word_count":     unique_words,
            "lexical_density_pct":   lexical_density,
            "empty_sections":        empty_sections,
            "duplicate_headings":    duplicate_heads,

            # derived flags (used by AI analyzer for context)
            "has_table_of_contents": self._has_toc(headings),
            "is_empty":              word_count == 0,
        }

    # ----------------------------------------------------------------- private
    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r'\b\w+\b', text))

    @staticmethod
    def _sentence_count(text: str) -> int:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return max(len([s for s in sentences if s.strip()]), 1)

    @staticmethod
    def _heading_distribution(headings) -> Dict[str, int]:
        dist: Counter = Counter(f"H{h.level}" for h in headings)
        return dict(sorted(dist.items()))

    @staticmethod
    def _count_links(text: str) -> int:
        url_pattern = re.compile(
            r'https?://\S+|www\.\S+|\[.+?\]\(.+?\)', re.IGNORECASE
        )
        return len(url_pattern.findall(text))

    @staticmethod
    def _count_code_blocks(text: str) -> int:
        # Markdown fenced code blocks or inline backticks
        fenced = len(re.findall(r'```[\s\S]*?```', text))
        inline = len(re.findall(r'`[^`]+`', text))
        return fenced + inline

    @staticmethod
    def _count_list_items(paragraphs) -> int:
        list_styles = {"ListBullet", "ListNumber", "List Bullet", "List Number",
                       "ListParagraph"}
        count = 0
        for p in paragraphs:
            if (p.style and p.style in list_styles) or \
               p.text.strip().startswith(("- ", "* ", "• ", "· ")):
                count += 1
        return count

    @staticmethod
    def _empty_section_count(headings, paragraphs) -> int:
        """Count headings that have no following paragraph content."""
        if not headings:
            return 0
        heading_texts = {h.text for h in headings}
        para_texts    = {p.text for p in paragraphs if p.style not in
                         {"Heading1","Heading2","Heading3","Heading 1","Heading 2","Heading 3"}}
        # Simple heuristic: last heading has content if paragraphs > headings
        empty = max(0, len(headings) - len([p for p in paragraphs
                                            if p.text not in heading_texts]))
        return empty

    @staticmethod
    def _duplicate_headings(headings) -> int:
        texts = [h.text.lower().strip() for h in headings]
        return len(texts) - len(set(texts))

    @staticmethod
    def _has_toc(headings) -> bool:
        toc_keywords = {"table of contents", "contents", "toc"}
        return any(h.text.lower().strip() in toc_keywords for h in headings)
