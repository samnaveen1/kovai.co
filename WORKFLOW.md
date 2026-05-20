# Doc Migration Tool — Workflow and Runbook

This document describes the full workflow, architecture, configuration, run commands, testing, and extension points for the `doc-migration-tool` project.

**Purpose**
- Extract structured content from DOCX/PDF files, compute quality and migration-readiness metrics, optionally enrich with LLM analysis, store results, and emit machine- and human-readable reports.

**High-level architecture**
- Input: .docx / .pdf files (uploaded or CLI-specified)
- Parsers: `src/parsers/*` produce a canonical `DocumentModel` (`src/parsers/document_model.py`).
- Metrics: `src/metrics/extractor.py` computes counts, averages and structural signals.
- AI Analysis: `src/ai/*` (HuggingFaceClient, OllamaClient, analyzer) optionally enriches metrics with semantic analysis.
- Storage: `src/storage/local_db.py` stores analysis results (MongoDB or local storage).
- Output: `src/output/*` creates JSON and summary reports; Streamlit UI and CLI wire everything together.

Dataflow (per file)
1. Ingest file (CLI: `main.py`; UI: `streamlit_app.py`).
2. `get_parser()` selects `DocxParser` or `PdfParser` → returns `DocumentModel`.
3. `MetricsExtractor(document).extract()` derives metrics → returns a metrics dict.
4. Instantiate chosen LLM client (Hugging Face or Ollama) per `LLM_BACKEND` configuration.
5. `ContentAnalyzer(client).analyze(document, metrics)` → returns AI analysis or heuristic fallback.
6. Combine metrics + ai_analysis → full `result` dict.
7. Save JSON + summary via `JsonReporter` and `SummaryReporter` and optionally persist via `LocalAnalysisStore`.

Configuration and environment
- `.env` (project root) — placeholders provided. Key variables:
  - `LLM_BACKEND` — `huggingface` or `ollama`.
  - `HUGGING_FACE_API_KEY` — required for Hugging Face.
  - `HUGGING_FACE_MODEL` — default model used when using Hugging Face.
  - `OLLAMA_BASE_URL` / `OLLAMA_MODEL` — for Ollama local server.
  - `ANALYSIS_MONGODB_URI`, `ANALYSIS_MONGODB_DB`, `ANALYSIS_MONGODB_COLLECTION` — DB settings.
  - `OUTPUT_DIR` — default reports location.

Run commands
- Install deps:
```bash
pip install -r requirements.txt
```
- CLI (single or multiple files supported):
```bash
python main.py path/to/file.pdf
python main.py docs/*.docx --model "meta-llama/Meta-Llama-3.1-8B-Instruct" --format both
```
- Streamlit UI:
```bash
streamlit run streamlit_app.py
# then upload one or multiple files and click Analyze
```

Selecting LLM backend
- Set `LLM_BACKEND` in `.env` or environment. The app will construct either `HuggingFaceClient` (requires API key) or `OllamaClient` (local Ollama server). The chosen model name is recorded in results.

Extending the project
- Add a new parser: implement a parser that returns `DocumentModel` and register it in `get_parser()` in `main.py` (or add dynamic factory).
- Add metrics: implement additional metrics in `src/metrics/extractor.py` and include them in reporters.
- Add reporter: create a new class under `src/output/` and call it from `main.py` or Streamlit UI.
- Add AI provider: implement a client with `is_available()` and `generate(prompt, system=None)` and use it in `main.py`.

Testing
- Unit tests live in `tests/`. Run:
```bash
pytest -q
```
- Add tests for new parsers/metrics/clients.

CI (GitHub Actions) — example job
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest -q
```

Troubleshooting
- "No PDF library found": ensure `pymupdf` or `pdfminer.six` is installed.
- Hugging Face errors: check `HUGGING_FACE_API_KEY` and network access.
- Ollama errors: run `ollama serve` and verify `OLLAMA_BASE_URL`.
- Large documents: increase timeouts or use local model backends.

Performance notes
- PyMuPDF (`pymupdf`) provides richer structure and image detection; prefer it when available.
- LLM calls are the slowest step — use smaller models or throttle concurrency for bulk runs.

Security and secrets
- Never commit secrets into git. Put API keys in `.env` or CI secrets.

Next recommended tasks
- Add `--backend` CLI flag to override `LLM_BACKEND` per-run.
- Add per-page image metadata to `DocumentModel` (if image previews are needed).
- Add end-to-end integration test that runs the full pipeline on a sample file.

Contact
- For further changes or to add a deployment pipeline (Docker / Heroku / Azure Web App), ask and I will scaffold it.
