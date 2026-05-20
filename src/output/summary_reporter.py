"""
Summary Reporter — generates a readable Markdown report
formatted for sharing with non-technical stakeholders.
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Dict


_TRAFFIC  = {
    "Ready":                      "✅ READY",
    "Needs Minor Fixes":          "⚠️  NEEDS MINOR FIXES",
    "Needs Major Restructuring":  "🚨 NEEDS MAJOR RESTRUCTURING",
}

_READ_ICON = {"Easy": "🟢", "Medium": "🟡", "Complex": "🔴"}
_STR_ICON  = {
    "Well-organized": "✅",
    "Fragmented":     "🚨",
    "Needs improvement": "⚠️",
}


def _bullet(items, indent=4) -> str:
    prefix = " " * indent + "- "
    return "\n".join(prefix + str(i) for i in items)


class SummaryReporter:
    """
    Renders a human-readable migration readiness report.

    Usage:
        reporter = SummaryReporter(result_dict)
        reporter.save(Path("output/summary.txt"))
        text = reporter.render()   # get as string
    """

    def __init__(self, result: Dict[str, Any]):
        self.result = result

    def render(self) -> str:
        r = self.result
        m = r.get("metrics", {})
        a = r.get("ai_analysis", {})

        lines = [
            "# Document Migration Readiness Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**File:** {r.get('file_name', 'Unknown')}",
            f"**Type:** {r.get('file_type', 'Unknown')}",
            "",
            "## Metrics Summary",
            f"- **Pages:** {m.get('page_count', 'N/A')}",
            f"- **Words:** {m.get('word_count', 'N/A'):,}" if isinstance(m.get('word_count'), int) else f"- **Words:** {m.get('word_count', 'N/A')}",
            f"- **Paragraphs:** {m.get('paragraph_count', 'N/A')}",
            f"- **Headings:** {m.get('heading_count', 'N/A')}",
            f"- **Avg Words/Para:** {m.get('avg_words_per_paragraph', 'N/A')}",
            f"- **Links:** {m.get('link_count', 'N/A')}",
            f"- **Code Blocks:** {m.get('code_block_count', 'N/A')}",
            f"- **List Items:** {m.get('list_item_count', 'N/A')}",
            f"- **Duplicate Heads:** {m.get('duplicate_headings', 0)}",
            f"- **Empty Sections:** {m.get('empty_sections', 0)}",
            f"- **Lexical Density:** {m.get('lexical_density_pct', 'N/A')}%",
            "",
            "## AI Analysis",
            f"- **Readability:** {_READ_ICON.get(a.get('readability_level',''), '•')} {a.get('readability_level', 'N/A')}",
            f"  - {a.get('readability_reason', '')}",
            f"- **Clarity:** {a.get('content_clarity', 'N/A')}",
            f"  - {a.get('clarity_notes', '')}",
            f"- **Structure:** {_STR_ICON.get(a.get('structural_quality',''), '•')} {a.get('structural_quality', 'N/A')}",
            f"  - {a.get('structure_notes', '')}",
            "",
            "## Migration Readiness",
            f"- **Status:** {_TRAFFIC.get(a.get('migration_readiness',''), a.get('migration_readiness','N/A'))}",
            f"- **Score:** {a.get('readiness_score', 'N/A')} / 100",
            f"- **Effort:** {a.get('estimated_migration_effort', 'N/A')}",
            f"- **Summary:** {a.get('readiness_reason', '')}",
            "",
        ]

        # Strengths
        strengths = a.get("strengths", [])
        if strengths:
            lines += ["## Strengths", _bullet(strengths), ""]

        # Issues
        issues = a.get("issues", [])
        if issues:
            lines += ["## Issues Found", _bullet(issues), ""]

        # Suggestions
        suggestions = a.get("suggestions", [])
        if suggestions:
            lines += ["## Recommendations", _bullet(suggestions), ""]

        # Actions before migration
        actions = a.get("recommended_actions_before_migration", [])
        if actions:
            lines += ["## Actions Before Migration", _bullet(actions), ""]

        lines += ["---", ""]
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")

    def print(self) -> None:
        print(self.render())
