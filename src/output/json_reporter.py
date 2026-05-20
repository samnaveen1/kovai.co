"""
JSON Reporter — saves the full analysis result as a formatted JSON file.
"""

import json
from pathlib import Path
from datetime import datetime


class JsonReporter:
    """
    Writes the analysis result to a pretty-printed JSON file.

    Usage:
        reporter = JsonReporter(result_dict)
        reporter.save(Path("output/report.json"))
    """

    def __init__(self, result: dict):
        self.result = result

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        output = {
            "generated_at": datetime.now().isoformat(),
            "tool": "doc-migration-tool",
            "version": "1.0.0",
            **self.result,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
