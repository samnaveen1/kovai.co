"""
Doc Migration Tool — Main Entry Point
Processes .docx and .pdf files for migration readiness analysis.
"""

import argparse
import sys
import json
from pathlib import Path

from config.settings import (
    MONGODB_URI,
    MONGODB_DB_NAME,
    MONGODB_COLLECTION,
    HUGGING_FACE_API_KEY,
    HUGGING_FACE_MODEL,
    OUTPUT_DIR,
)
from src.parsers.docx_parser import DocxParser
from src.parsers.pdf_parser import PdfParser
from src.metrics.extractor import MetricsExtractor
from src.ai.analyzer import ContentAnalyzer
from src.output.json_reporter import JsonReporter
from src.output.summary_reporter import SummaryReporter
from src.storage.local_db import LocalAnalysisStore


def get_parser(file_path: Path):
    """Return the appropriate parser based on file extension."""
    ext = file_path.suffix.lower()
    if ext == ".docx":
        return DocxParser(file_path)
    elif ext == ".pdf":
        return PdfParser(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Only .docx and .pdf are supported.")


def process_document(
    file_path: str,
    output_format: str,
    hf_model: str,
    output_dir: str,
    hf_api_key: str = HUGGING_FACE_API_KEY,
    mongodb_uri: str = MONGODB_URI,
    mongodb_db: str = MONGODB_DB_NAME,
    mongodb_collection: str = MONGODB_COLLECTION,
):
    """Full pipeline: parse → metrics → AI analysis → report."""
    path = Path(file_path)
    if not path.exists():
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Processing: {path.name}")
    print(f"{'='*60}")

    # 1. Parse document
    print("\n[1/4] Parsing document...")
    parser = get_parser(path)
    document = parser.parse()
    print(f"      ✓ Extracted {len(document.paragraphs)} paragraphs, "
          f"{len(document.headings)} headings")

    # 2. Extract metrics
    print("\n[2/4] Extracting metrics...")
    extractor = MetricsExtractor(document)
    metrics = extractor.extract()
    print(f"      ✓ Words: {metrics['word_count']}, "
          f"Paragraphs: {metrics['paragraph_count']}, "
          f"Sections: {metrics['heading_count']}")

    # 3. AI analysis
    from config import settings as cfg

    backend = cfg.LLM_BACKEND
    print(f"\n[3/4] Running AI analysis via {backend.title()}...")

    if backend == "ollama":
        from src.ai.ollama_client import OllamaClient
        client = OllamaClient(model=cfg.OLLAMA_MODEL, base_url=cfg.OLLAMA_BASE_URL, timeout=cfg.OLLAMA_TIMEOUT)
        used_model = cfg.OLLAMA_MODEL
    else:
        from src.ai.huggingface_client import HuggingFaceClient
        client = HuggingFaceClient(model=hf_model, api_key=hf_api_key)
        used_model = hf_model

    analyzer = ContentAnalyzer(client)
    analysis = analyzer.analyze(document, metrics)
    print(f"      ✓ Readability: {analysis.get('readability_level', 'N/A')}")
    print(f"      ✓ Migration readiness: {analysis.get('migration_readiness', 'N/A')}")

    # 4. Output report
    print("\n[4/4] Generating report...")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    result = {
        "file": str(path),
        "file_name": path.name,
        "file_type": path.suffix.lstrip(".").upper(),
        "metrics": metrics,
        "ai_analysis": analysis,
    }

    if output_format in ("json", "both"):
        json_path = out_dir / f"{stem}_report.json"
        JsonReporter(result).save(json_path)
        print(f"      ✓ JSON report → {json_path}")

    if output_format in ("summary", "both"):
        summary_path = out_dir / f"{stem}_summary.md"
        SummaryReporter(result).save(summary_path)
        print(f"      ✓ Summary report → {summary_path}")

    # 5. Save to local database
    try:
        store = LocalAnalysisStore(
            mongodb_uri,
            db_name=mongodb_db,
            collection_name=mongodb_collection,
        )
        row_id = store.save_result(result, source_path=str(path), ai_model=used_model)
        print(
            f"      ✓ Saved to MongoDB → {mongodb_uri} "
            f"({mongodb_db}.{mongodb_collection}, row {row_id})"
        )
    except Exception as e:
        print(f"      ⚠  Local DB save skipped: {e}")

    print(f"\n{'='*60}")
    print("  DONE")
    print(f"{'='*60}\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Document Migration Readiness Tool — Powered by Hugging Face AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py document.docx
  python main.py report.pdf --model meta-llama/Meta-Llama-3.1-8B-Instruct --format both
  python main.py docs/*.docx --output-dir ./reports --format json
        """
    )
    parser.add_argument("files", nargs="+", help="Path(s) to .docx or .pdf file(s)")
    parser.add_argument(
        "--model", default=HUGGING_FACE_MODEL,
        help="Hugging Face model to use (default: meta-llama/Meta-Llama-3.1-8B-Instruct)"
    )
    parser.add_argument(
        "--format", choices=["json", "summary", "both"], default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR,
        help="Directory for output reports (default: configured output dir)"
    )
    parser.add_argument(
        "--mongodb-uri", default=MONGODB_URI,
        help="MongoDB connection string (default: mongodb://localhost:27017)"
    )
    parser.add_argument(
        "--mongodb-db", default=MONGODB_DB_NAME,
        help="MongoDB database name (default: doc_migration_tool)"
    )
    parser.add_argument(
        "--mongodb-collection", default=MONGODB_COLLECTION,
        help="MongoDB collection name (default: analyses)"
    )
    parser.add_argument(
        "--print-json", action="store_true",
        help="Print JSON result to stdout after processing"
    )

    args = parser.parse_args()

    all_results = []
    for file_path in args.files:
        try:
            result = process_document(
                file_path,
                output_format=args.format,
                hf_model=args.model,
                output_dir=args.output_dir,
                hf_api_key=HUGGING_FACE_API_KEY,
                mongodb_uri=args.mongodb_uri,
                mongodb_db=args.mongodb_db,
                mongodb_collection=args.mongodb_collection,
            )
            all_results.append(result)
        except Exception as e:
            print(f"[ERROR] Failed to process {file_path}: {e}")

    if args.print_json:
        print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
