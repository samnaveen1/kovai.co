"""
tests/test_analyzer.py
Tests for ContentAnalyzer, focusing on the fallback path
(no Ollama required for CI).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

from src.parsers.document_model import DocumentModel, Heading, Paragraph
from src.ai.ollama_client import OllamaClient
from src.ai.analyzer import ContentAnalyzer


def _make_doc_and_metrics(avg_words=15, heading_count=5, word_count=500, dupes=0):
    doc = DocumentModel(source_path="x.docx", file_type="docx")
    doc.title = "Test Doc"
    doc.raw_text = "word " * word_count
    metrics = {
        "word_count": word_count,
        "paragraph_count": 20,
        "heading_count": heading_count,
        "avg_words_per_paragraph": avg_words,
        "link_count": 2,
        "duplicate_headings": dupes,
        "empty_sections": 0,
    }
    return doc, metrics


class TestAnalyzerFallback:
    """Tests that use the heuristic fallback (no Ollama needed)."""

    def _analyzer_no_ollama(self):
        client = OllamaClient()
        with patch.object(client, "is_available", return_value=False):
            return ContentAnalyzer(client), client

    def test_returns_dict(self):
        doc, metrics = _make_doc_and_metrics()
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        required = [
            "readability_level", "content_clarity", "structural_quality",
            "migration_readiness", "readiness_score", "suggestions", "issues"
        ]
        doc, metrics = _make_doc_and_metrics()
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_easy_readability_short_paragraphs(self):
        doc, metrics = _make_doc_and_metrics(avg_words=10)
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        assert result["readability_level"] == "Easy"

    def test_complex_readability_long_paragraphs(self):
        doc, metrics = _make_doc_and_metrics(avg_words=80)
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        assert result["readability_level"] == "Complex"

    def test_score_is_integer_in_range(self):
        doc, metrics = _make_doc_and_metrics()
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        assert isinstance(result["readiness_score"], int)
        assert 0 <= result["readiness_score"] <= 100

    def test_duplicate_headings_flagged(self):
        doc, metrics = _make_doc_and_metrics(dupes=3)
        analyzer, client = self._analyzer_no_ollama()
        with patch.object(client, "is_available", return_value=False):
            result = analyzer.analyze(doc, metrics)
        issues = " ".join(result.get("issues", []))
        assert "duplicate" in issues.lower()


class TestAnalyzerJsonParsing:

    def test_strips_markdown_fences(self):
        raw = '```json\n{"readability_level": "Easy"}\n```'
        result = ContentAnalyzer._parse_json_response(raw)
        assert result["readability_level"] == "Easy"

    def test_plain_json(self):
        raw = '{"readability_level": "Medium", "readiness_score": 75}'
        result = ContentAnalyzer._parse_json_response(raw)
        assert result["readiness_score"] == 75

    def test_raises_on_no_json(self):
        with pytest.raises((ValueError, Exception)):
            ContentAnalyzer._parse_json_response("no json here at all")
