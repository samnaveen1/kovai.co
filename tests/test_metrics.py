"""
tests/test_metrics.py
Unit tests for the MetricsExtractor.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.parsers.document_model import DocumentModel, Heading, Paragraph
from src.metrics.extractor import MetricsExtractor


def _doc(paragraphs=None, headings=None, raw_text=None, pages=1):
    doc = DocumentModel(source_path="test.docx", file_type="docx", page_count=pages)
    doc.paragraphs = paragraphs or []
    doc.headings   = headings   or []
    doc.raw_text   = raw_text   or " ".join(p.text for p in (paragraphs or []))
    return doc


class TestMetricsExtractor:

    def test_word_count(self):
        doc = _doc(paragraphs=[Paragraph("hello world foo bar")], raw_text="hello world foo bar")
        m = MetricsExtractor(doc).extract()
        assert m["word_count"] == 4

    def test_paragraph_count(self):
        paras = [Paragraph("a"), Paragraph("b"), Paragraph("c")]
        doc = _doc(paragraphs=paras)
        m = MetricsExtractor(doc).extract()
        assert m["paragraph_count"] == 3

    def test_heading_count(self):
        heads = [Heading(1, "H1"), Heading(2, "H2")]
        doc = _doc(headings=heads)
        m = MetricsExtractor(doc).extract()
        assert m["heading_count"] == 2

    def test_empty_document(self):
        doc = _doc(raw_text="")
        m = MetricsExtractor(doc).extract()
        assert m["word_count"] == 0
        assert m["is_empty"] is True

    def test_duplicate_headings(self):
        heads = [Heading(1, "Intro"), Heading(2, "Intro")]
        doc = _doc(headings=heads)
        m = MetricsExtractor(doc).extract()
        assert m["duplicate_headings"] == 1

    def test_link_count(self):
        doc = _doc(raw_text="See https://example.com and https://test.org for more.")
        m = MetricsExtractor(doc).extract()
        assert m["link_count"] == 2

    def test_lexical_density_range(self):
        doc = _doc(raw_text="the the the the cat cat sat sat")
        m = MetricsExtractor(doc).extract()
        assert 0 < m["lexical_density_pct"] <= 100

    def test_page_count_preserved(self):
        doc = _doc(pages=5)
        m = MetricsExtractor(doc).extract()
        assert m["page_count"] == 5

    def test_avg_words_per_paragraph(self):
        paras = [Paragraph("one two three"), Paragraph("four five six seven")]
        raw   = "one two three four five six seven"
        doc = _doc(paragraphs=paras, raw_text=raw)
        m = MetricsExtractor(doc).extract()
        # 7 words / 2 paragraphs = 3.5
        assert m["avg_words_per_paragraph"] == 3.5
