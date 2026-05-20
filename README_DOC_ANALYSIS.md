Document Analysis Tool

This tool extracts text and metrics from PDF, DOCX, TXT, PPTX, and HTML files.

Setup

1. Create a Python 3.11+ virtual environment and activate it.

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Usage

- Single file:

```bash
python -m doc_analysis.cli path/to/file.pdf
```

- Batch folder:

```bash
python -m doc_analysis.cli --batch path/to/folder
```

- Enable OCR fallback for scanned PDFs:

```bash
python -m doc_analysis.cli --ocr path/to/scanned.pdf
```

Streamlit UI

```bash
streamlit run -m doc_analysis.streamlit_app
```

Outputs

- JSON report(s) saved under `output/` as `<filename>_report.json`.
- Combined batch `output/reports.json` when processing a folder.
- CSV export via `doc_analysis.utils.export_csv(results)`

Notes

- OCR requires `tesseract` installed on your system and `pytesseract` Python package.
- The tool uses heuristic heading detection for plain text and PDFs.
