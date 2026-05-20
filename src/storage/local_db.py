"""Local MongoDB storage for migration analysis results."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pymongo import MongoClient  # pyright: ignore[reportMissingImports]
except ImportError as exc:
    raise ImportError(
        "pymongo is required. Install with:  pip install pymongo"
    ) from exc


class LocalAnalysisStore:
    """Persist analysis results to a local MongoDB collection."""

    def __init__(self, mongodb_uri: str, db_name: str, collection_name: str):
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
        self.client.admin.command("ping")
        self.collection = self.client[self.db_name][self.collection_name]
        self._initialize()

    def _initialize(self) -> None:
        self.collection.create_index("created_at")
        self.collection.create_index("file_name")

    def save_result(
        self,
        result: Dict[str, Any],
        source_path: Optional[str] = None,
        ai_model: Optional[str] = None,
    ) -> int:
        metrics = result.get("metrics", {})
        ai = result.get("ai_analysis", {})
        created_at = datetime.now().isoformat(timespec="seconds")

        document = {
            "created_at": created_at,
            "source_path": source_path or result.get("file"),
            "file_name": result.get("file_name", "Unknown"),
            "file_type": result.get("file_type", "Unknown"),
            "ai_model": ai_model,
            "page_count": metrics.get("page_count"),
            "word_count": metrics.get("word_count"),
            "paragraph_count": metrics.get("paragraph_count"),
            "heading_count": metrics.get("heading_count"),
            "readability_level": ai.get("readability_level"),
            "migration_readiness": ai.get("migration_readiness"),
            "readiness_score": ai.get("readiness_score"),
            "metrics_json": json.dumps(metrics, ensure_ascii=False),
            "ai_json": json.dumps(ai, ensure_ascii=False),
            "result_json": json.dumps(result, ensure_ascii=False),
        }

        inserted = self.collection.insert_one(document)
        return str(inserted.inserted_id)

    def list_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = (
            self.collection.find(
                {},
                {
                    "_id": 0,
                    "created_at": 1,
                    "file_name": 1,
                    "file_type": 1,
                    "source_path": 1,
                    "ai_model": 1,
                    "page_count": 1,
                    "word_count": 1,
                    "paragraph_count": 1,
                    "heading_count": 1,
                    "readability_level": 1,
                    "migration_readiness": 1,
                    "readiness_score": 1,
                },
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        return list(cursor)
