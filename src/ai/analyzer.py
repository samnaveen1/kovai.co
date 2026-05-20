"""
Content Analyzer — sends document data to an AI provider and parses the response.
Falls back to a rule-based analysis if the provider is unavailable.
"""

import json
import re
from typing import Dict, Any

from src.parsers.document_model import DocumentModel
from src.ai.huggingface_client import HuggingFaceClient, HuggingFaceError
from src.ai.prompts import SYSTEM_PROMPT, build_analysis_prompt


class ContentAnalyzer:
    """
    Uses an AI provider client to produce AI-driven migration analysis.

    Args:
        client: AI provider instance (already configured with model)

    Usage:
        analyzer = ContentAnalyzer(client)
        result   = analyzer.analyze(document, metrics)
    """

    def __init__(self, client: HuggingFaceClient):
        self.client = client

    # ------------------------------------------------------------------ public
    def analyze(self, document: DocumentModel, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Return the AI analysis dict. Falls back to heuristics on error."""
        prompt = build_analysis_prompt(
            title=document.title,
            file_type=document.file_type,
            metrics=metrics,
            excerpt=document.raw_text,
        )

        # --- check provider availability ----------------------------------
        if not self.client.is_available():
            print("      ⚠  Hugging Face not reachable — using rule-based fallback analysis")
            return self._fallback_analysis(document, metrics)

        # --- call provider ------------------------------------------------
        try:
            response = self.client.generate(prompt=prompt, system=SYSTEM_PROMPT)
            return self._parse_json_response(response)
        except HuggingFaceError as e:
            print(f"      ⚠  Hugging Face error: {e}\n         Using rule-based fallback.")
            return self._fallback_analysis(document, metrics)
        except Exception as e:
            print(f"      ⚠  Unexpected AI error: {e}\n         Using rule-based fallback.")
            return self._fallback_analysis(document, metrics)

    # ----------------------------------------------------------------- private
    @staticmethod
    def _parse_json_response(text: str) -> Dict[str, Any]:
        """
        Extract the JSON object from the provider response.
        Handles cases where the model wraps output in markdown fences.
        """
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()

        # Find first { ... } block
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("No JSON object found in AI response")

    @staticmethod
    def _fallback_analysis(
        document: DocumentModel, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pure heuristic analysis when the AI provider is unavailable.
        Deterministic, transparent rules — derived from the document metrics.
        """
        wc        = metrics.get("word_count", 0)
        hc        = metrics.get("heading_count", 0)
        pc        = metrics.get("paragraph_count", 1)
        avg_words = metrics.get("avg_words_per_paragraph", 0)
        dupes     = metrics.get("duplicate_headings", 0)
        empty_sec = metrics.get("empty_sections", 0)
        links     = metrics.get("link_count", 0)
        is_empty  = metrics.get("is_empty", wc == 0)

        # Readability
        if avg_words < 25:
            readability = "Easy"
            readability_reason = (
                f"Average {avg_words} words per paragraph suggests short, readable sections."
            )
        elif avg_words < 60:
            readability = "Medium"
            readability_reason = (
                f"Average {avg_words} words per paragraph suggests moderate sentence density."
            )
        else:
            readability = "Complex"
            readability_reason = (
                f"Average {avg_words} words per paragraph suggests dense, complex sections."
            )

        # Structure
        ratio = hc / max(pc, 1)
        if ratio > 0.15 and dupes == 0:
            structure = "Well-organized"
            structure_notes = (
                f"{hc} headings across {pc} paragraphs provide a strong structure."
            )
        elif dupes > 2 or empty_sec > 2:
            structure = "Fragmented"
            structure_notes = (
                f"{dupes} duplicate headings and {empty_sec} empty sections indicate fragmentation."
            )
        else:
            structure = "Needs improvement"
            structure_notes = (
                f"{hc} headings across {pc} paragraphs give moderate structure, but the hierarchy can be improved."
            )

        # Score (0-100)
        score = 60
        if hc > 3:          score += 10
        if wc > 200:        score += 10
        if dupes == 0:      score += 10
        if empty_sec == 0:  score += 10
        if links <= 5:      score += 5
        score = min(score, 100)

        if score >= 80:
            readiness = "Ready"
        elif score >= 55:
            readiness = "Needs Minor Fixes"
        else:
            readiness = "Needs Major Restructuring"

        content_clarity = (
            "Low" if is_empty or wc < 100
            else "High" if avg_words < 25 and dupes == 0
            else "Medium"
        )

        issues = []
        if dupes > 0:
            issues.append(f"{dupes} duplicate heading(s) found — rename for clarity.")
        if empty_sec > 0:
            issues.append(f"{empty_sec} section(s) appear to have no body content.")
        if links > 5:
            issues.append("High number of external links — verify all are valid before migration.")
        if wc < 100:
            issues.append("Very short document — may need more content.")
        if is_empty:
            issues.append("Document appears to be empty.")

        suggestions = []
        if hc == 0:
            suggestions.append("Add clear section headings so the content is easier to migrate.")
        if dupes > 0:
            suggestions.append("Rename duplicate headings to make the hierarchy unique.")
        if empty_sec > 0:
            suggestions.append("Add body content under empty sections or remove those headings.")
        if links > 0:
            suggestions.append("Verify all hyperlinks before migration.")
        if avg_words >= 60:
            suggestions.append("Split long paragraphs to reduce migration complexity.")
        if wc > 0 and wc < 100:
            suggestions.append("Expand short content with introductions or supporting details.")
        if not suggestions:
            suggestions.append("Document structure looks consistent; review formatting before migration.")

        if wc > 200:
            strength_text = f"Contains {wc} words of substantive content."
        elif wc > 0:
            strength_text = f"Contains {wc} words with a concise presentation."
        else:
            strength_text = "No body content was detected."

        return {
            "readability_level":   readability,
            "readability_reason":  readability_reason,
            "content_clarity":     content_clarity,
            "clarity_notes":       (
                "Empty or very short documents reduce clarity."
                if is_empty or wc < 100
                else "Clarity is supported by the observed paragraph length and heading structure."
            ),
            "structural_quality":  structure,
            "structure_notes":     structure_notes,
            "migration_readiness": readiness,
            "readiness_score":     score,
            "readiness_reason":    (
                f"Heuristic score derived from {hc} headings, {dupes} duplicate headings, "
                f"{empty_sec} empty sections, and {wc} words."
            ),
            "strengths":           [
                f"Contains {hc} section headings." if hc else strength_text,
                f"Word count of {wc} is {'adequate' if wc > 200 else 'low' if wc > 0 else 'missing'}.",
            ],
            "issues":              issues or ["No critical issues detected from the available metrics."],
            "suggestions":         suggestions,
            "estimated_migration_effort": (
                "Low" if readiness == "Ready"
                else "Medium" if readiness == "Needs Minor Fixes"
                else "High"
            ),
            "recommended_actions_before_migration": [
                "Review document structure and heading hierarchy.",
                "Fix any broken or outdated links.",
            ],
            "_analysis_method": "heuristic_fallback",
        }
