"""Tests for the local MongoDB analysis store."""

from unittest.mock import MagicMock, patch

from src.storage.local_db import LocalAnalysisStore


def test_save_and_list_recent():
    fake_client = MagicMock()
    fake_db = MagicMock()
    fake_collection = MagicMock()
    fake_admin = MagicMock()
    fake_client.admin = fake_admin
    fake_client.__getitem__.side_effect = lambda name: fake_db if name == "doc_migration_tool" else fake_collection
    fake_db.__getitem__.return_value = fake_collection
    fake_collection.insert_one.return_value.inserted_id = "123"
    fake_collection.find.return_value.sort.return_value.limit.return_value = [
        {
            "created_at": "2026-05-20T10:00:00",
            "file_name": "sample.docx",
            "file_type": "DOCX",
            "source_path": "C:/docs/sample.docx",
                "ai_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "page_count": 2,
            "word_count": 120,
            "paragraph_count": 10,
            "heading_count": 3,
            "readability_level": "Easy",
            "migration_readiness": "Ready",
            "readiness_score": 90,
        }
    ]

    with patch("src.storage.local_db.MongoClient", return_value=fake_client):
        store = LocalAnalysisStore(
            "mongodb://localhost:27017",
            db_name="doc_migration_tool",
            collection_name="analyses",
        )

        result = {
            "file": "sample.docx",
            "file_name": "sample.docx",
            "file_type": "DOCX",
            "metrics": {
                "page_count": 2,
                "word_count": 120,
                "paragraph_count": 10,
                "heading_count": 3,
            },
            "ai_analysis": {
                "readability_level": "Easy",
                "migration_readiness": "Ready",
                "readiness_score": 90,
            },
        }

        row_id = store.save_result(result, source_path="C:/docs/sample.docx", ai_model="meta-llama/Meta-Llama-3.1-8B-Instruct")
        assert row_id == "123"

        recent = store.list_recent(limit=5)
        assert len(recent) == 1
        assert recent[0]["file_name"] == "sample.docx"
        assert recent[0]["readiness_score"] == 90
