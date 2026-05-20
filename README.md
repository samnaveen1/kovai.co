# Doc Migration Tool 📄→🚀

A CLI automation tool that analyses `.docx` and `.pdf` documents,
extracts structural metrics, and uses a **Hugging Face hosted LLM** to
generate actionable migration readiness reports.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [Running the Project](#running-the-project)
5. [UI Dashboard](#ui-dashboard)
6. [Output Format](#output-format)
7. [Configuration](#configuration)
8. [Sample Input & Output](#sample-input--output)
9. [Implementation Plan](#implementation-plan)

---

## Tech Stack

| Layer           | Technology             | Purpose                                  |
|-----------------|------------------------|------------------------------------------|
| Language        | Python 3.10+           | Core runtime                             |
| DOCX parsing    | `python-docx`          | Extract text, headings, styles from .docx|
| PDF parsing     | `PyMuPDF` (fitz)       | Rich PDF layout + font-size heuristics   |
| PDF fallback    | `pdfminer.six`         | Plain-text PDF extraction fallback       |
| AI model        | **Hugging Face Inference API** | Content analysis, readability, migration |
| HTTP client     | `urllib` (stdlib)      | Zero-dependency Hugging Face API calls   |
| Database        | MongoDB (local)        | Save analysis history on localhost       |
| Output          | JSON + plain text      | Structured + human-readable reports      |
| Tests           | `pytest`               | Unit tests for parsers and metrics       |

> **Why Hugging Face?**  
> Hugging Face provides hosted inference for many strong instruction-tuned
> models. You supply an API token through an environment variable or the UI;
> the key is never stored in source code.

---

## Architecture

```
doc-migration-tool/
├── main.py                         ← Entry point / CLI
├── requirements.txt
├── README.md
│
├── config/
│   └── settings.py                 ← Centralised defaults (env-overridable)
│
├── src/
│   ├── parsers/
│   │   ├── document_model.py       ← Shared DocumentModel dataclass
│   │   ├── docx_parser.py          ← .docx → DocumentModel
│   │   └── pdf_parser.py           ← .pdf  → DocumentModel
│   │
│   ├── metrics/
│   │   └── extractor.py            ← Calculates all document metrics
│   │
│   ├── ai/
│   │   ├── huggingface_client.py    ← Hugging Face inference wrapper
│   │   ├── prompts.py               ← Prompt templates
│   │   └── analyzer.py              ← Orchestrates AI + fallback
│   │
│   └── output/
│       ├── json_reporter.py        ← Saves result as JSON
│       └── summary_reporter.py     ← Human-readable text report
│
├── tests/
│   ├── test_docx_parser.py
│   ├── test_pdf_parser.py
│   ├── test_metrics.py
│   └── test_analyzer.py
│
├── sample_input/                   ← Put your test documents here
└── sample_output/                  ← Reports are written here
```

---

## Setup Instructions

### 1. Prerequisites

- Python **3.10 or higher**
- A Hugging Face account and access token

### 2. Clone / Download

```bash
git clone https://github.com/your-org/doc-migration-tool.git
cd doc-migration-tool
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Hugging Face access

```bash
set HUGGING_FACE_API_KEY=your_token_here
set HUGGING_FACE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

The tool works without the API key — it falls back to rule-based analysis.
For AI-powered insights, set the token before you process documents.

### 5. Verify setup

```bash
# Check the Hugging Face token is available
python -c "import os; print(bool(os.getenv('HUGGING_FACE_API_KEY')))"

# Check Python dependencies
python -c "import docx; import fitz; print('All good!')"
```

---

## Running the Project

### Basic usage

```bash
# Analyse a single Word document
python main.py sample_input/my_doc.docx

# Analyse a PDF
python main.py sample_input/my_doc.pdf

# Multiple files at once
python main.py docs/guide1.docx docs/guide2.pdf

# Use a different Hugging Face model
python main.py my_doc.docx --model meta-llama/Meta-Llama-3.1-8B-Instruct

# Choose output format
python main.py my_doc.docx --format json       # JSON only
python main.py my_doc.docx --format summary    # text only
python main.py my_doc.docx --format both       # both (default)

# Custom output directory
python main.py my_doc.docx --output-dir ./reports

# Print JSON to stdout (for piping)
python main.py my_doc.docx --print-json
```

### Launch the UI dashboard

```bash
streamlit run streamlit_app.py
```

The UI lets you upload a `.docx` or `.pdf`, review metrics and AI analysis,
and download JSON or summary reports.

All runs are also saved to a local MongoDB instance at `mongodb://localhost:27017`
by default, in the `doc_migration_tool.analyses` collection. You can override that
with the `ANALYSIS_MONGODB_URI`, `ANALYSIS_MONGODB_DB`, and
`ANALYSIS_MONGODB_COLLECTION` environment variables, or the matching CLI options.

## UI Dashboard

The Streamlit interface provides:

- File upload for `.docx` and `.pdf`
- Sample document selection from `sample_input/`
- Metrics cards for quick scanning
- JSON views of extracted metrics and AI insights
- Download buttons for the generated reports

It reuses the same parsing, metrics, and analysis pipeline as the CLI.

### Environment variable overrides

```bash
export HUGGING_FACE_API_KEY=your_token_here
export HUGGING_FACE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
export OUTPUT_DIR=./reports

python main.py my_doc.docx
```

### Run tests

```bash
pytest tests/ -v
```

---

## Output Format

Two report formats are generated per document:

### 1. JSON (`<filename>_report.json`)

```json
{
  "generated_at": "2025-01-15T10:30:00",
  "tool": "doc-migration-tool",
  "version": "1.0.0",
  "file_name": "guide.docx",
  "file_type": "DOCX",
  "metrics": {
    "page_count": 3,
    "word_count": 1095,
    "paragraph_count": 86,
    "heading_count": 22,
    "avg_words_per_paragraph": 12.7,
    "link_count": 4,
    "code_block_count": 0,
    "duplicate_headings": 0,
    "lexical_density_pct": 34.2
  },
  "ai_analysis": {
    "readability_level": "Easy",
    "content_clarity": "High",
    "structural_quality": "Well-organized",
    "migration_readiness": "Ready",
    "readiness_score": 92,
    "strengths": ["..."],
    "issues": ["..."],
    "suggestions": ["..."],
    "estimated_migration_effort": "Low",
    "recommended_actions_before_migration": ["..."]
  }
}
```

### 2. Summary (`<filename>_summary.txt`)

Plain text report with emoji status indicators — suitable for sharing
with writers, editors, or project managers.

---

## Configuration

All defaults live in `config/settings.py` and can be overridden with
environment variables:

| Setting                  | Default                      | Env var              |
|--------------------------|------------------------------|----------------------|
| Hugging Face API key     | unset                        | `HUGGING_FACE_API_KEY` |
| Hugging Face model       | `meta-llama/Meta-Llama-3.1-8B-Instruct` | `HUGGING_FACE_MODEL` |
| Output directory         | `./sample_output`            | `OUTPUT_DIR`         |
| Default output format    | `both`                       | `OUTPUT_FORMAT`      |
| MongoDB URI              | `mongodb://localhost:27017`  | `ANALYSIS_MONGODB_URI` |
| MongoDB database         | `doc_migration_tool`         | `ANALYSIS_MONGODB_DB` |
| MongoDB collection       | `analyses`                   | `ANALYSIS_MONGODB_COLLECTION` |

---

## Sample Input & Output

| File                                              | Description             |
|---------------------------------------------------|-------------------------|
| `sample_input/Editor_choices_in_Document360.docx` | Provided sample document|
| `sample_output/..._report.json`                   | JSON analysis result    |
| `sample_output/..._summary.txt`                   | Human-readable report   |

---

## Implementation Plan

### Phase 1 — Parsing Layer
- [x] `DocumentModel` shared dataclass
- [x] `DocxParser` using `python-docx` (headings, paragraphs, metadata)
- [x] `PdfParser` using PyMuPDF with font-size heuristics (fallback: pdfminer)
- [x] Edge case handling (empty docs, no headings, very large files)

### Phase 2 — Metrics Extraction
- [x] Word, paragraph, heading, sentence counts
- [x] Avg words/paragraph and words/sentence
- [x] Link and code block detection
- [x] Lexical density (unique words ÷ total words)
- [x] Duplicate heading detection
- [x] Empty section detection

### Phase 3 — AI Analysis (Hugging Face)
- [x] `HuggingFaceClient` — zero-dependency urllib wrapper
- [x] Structured prompt template requesting JSON output
- [x] JSON response parsing with markdown fence stripping
- [x] Rule-based fallback when Hugging Face is unavailable
- [x] Covers: readability, clarity, structure, readiness, suggestions

### Phase 4 — Output
- [x] JSON reporter with timestamp and version
- [x] Human-readable summary with emoji status indicators
- [x] CLI with argparse (files, model, format, output-dir flags)

### Phase 5 — Tests
- [x] Unit tests for all major modules
- [x] Edge case coverage (empty doc, PDF-only fields)

---

## Extending the Tool

**Add a new output format** (e.g., HTML dashboard):
- Create `src/output/html_reporter.py` with a `save(path)` method
- Import and call it in `main.py`

**Support more file types** (e.g., `.txt`, `.md`):
- Add a new parser in `src/parsers/`
- Register the extension in `main.py`'s `get_parser()`

**Use a different AI backend** (e.g., OpenAI-compatible API):
- Implement the same `generate(prompt, system)` interface as `HuggingFaceClient`
- Pass your custom client to `ContentAnalyzer`

---

## Interview Talking Points

### Why this LLM / backend
- Capability: chosen for instruction-following and structured JSON output, making parsing reliable.
- Tradeoffs: balance quality vs latency/cost; prefer local Ollama for sensitive data and Hugging Face for high-quality hosted models.
- Robustness: pipeline supports swapping backends and falls back to deterministic heuristics when AI is unavailable.

### How to explain key metrics (short answers)
- `page_count`, `word_count`: scale and effort estimates.
- `heading_count`, `max_heading_depth`: document structure and navigability—useful for mapping to CMS sections.
- `avg_words_per_paragraph` (6.9): very short paragraphs → easier editorial migration, may indicate lists.
- `image_count` (209): primary engineering cost (asset extraction, alt text, hosting).
- `link_count`: requires validation; broken links are migration blockers.
- `duplicate_headings` / `empty_sections`: clean-up items that reduce automation confidence.

### How to explain the AI analysis output
- `readability_level` & `readability_reason`: derived from avg words per paragraph/sentence.
- `structural_quality` & `structure_notes`: based on heading-to-paragraph ratios and duplicate headings.
- `readiness_score` & `migration_readiness`: composite heuristic (transparent weights) combining headings, word count, duplicates, and empty sections.
- `strengths`, `issues`, `suggestions`: actionable checklist for editors and engineers.

### Handling apparent contradictions (example)
- If `readiness_score` is high but `image_count` is large: explain that textual readiness and asset migration effort are orthogonal; both are surfaced so teams can plan editorial vs engineering work separately.

### Two‑sentence interview script
"I chose an LLM based on quality, cost, and privacy tradeoffs and designed the pipeline so it can swap backends and fallback to deterministic heuristics. The metrics quantify textual readiness while the AI maps these signals into an actionable readiness score and prioritized remediation steps."

### Quick demo guide for interviews
- Show Streamlit: upload 2 files, open each tab, download JSON for one file.
- Show CLI: run `python main.py sample_input/example.pdf` and open the generated JSON in `sample_output/`.

