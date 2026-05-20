"""Streamlit UI for the document migration readiness tool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from config.settings import (
    MONGODB_URI,
    MONGODB_DB_NAME,
    MONGODB_COLLECTION,
    HUGGING_FACE_MODEL,
)
from main import process_document
from src.storage.local_db import LocalAnalysisStore


st.set_page_config(
    page_title="Doc Migration Tool",
    page_icon="📄",
    layout="wide",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _metric_value(value):
    if isinstance(value, float):
        return f"{value:.1f}"
    return value


st.markdown(
    """
    <style>
      .main {
        background: radial-gradient(circle at top, rgba(26, 33, 58, 0.92), rgba(8, 11, 20, 1));
      }
      .stApp {
        color: #e8eef9;
      }
      .hero {
        padding: 1.6rem 1.8rem;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(15, 20, 35, 0.9), rgba(28, 38, 66, 0.82));
        box-shadow: 0 20px 50px rgba(0,0,0,0.28);
      }
      .hero h1 {
        margin: 0;
        font-size: 2.3rem;
      }
      .hero p {
        margin: 0.35rem 0 0;
        color: rgba(232, 238, 249, 0.78);
      }
      .metric-card {
        padding: 1rem 1.1rem;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }
      .metric-label {
        color: rgba(232, 238, 249, 0.65);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 0.3rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="hero">
      <h1>Document Migration Readiness UI</h1>
      <p>Upload a Word or PDF document, review extracted metrics, and get a migration readiness assessment you can share.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.header("Analysis Settings")
    model = st.text_input("Hugging Face model", value=HUGGING_FACE_MODEL)
    hf_api_key = st.text_input("Hugging Face API key", value="", type="password")
    output_format = st.selectbox("Output format", ["json", "summary", "both"], index=2)
    mongodb_uri = st.text_input("MongoDB URI", value=MONGODB_URI)
    mongodb_db = st.text_input("MongoDB database", value=MONGODB_DB_NAME)
    mongodb_collection = st.text_input("MongoDB collection", value=MONGODB_COLLECTION)
    st.caption("The UI uses the same pipeline as the CLI and can fall back to heuristic analysis if Hugging Face is unavailable.")


uploaded = st.file_uploader("Upload a .docx or .pdf file", type=["docx", "pdf"])

source_path: Path | None = None
temp_dir = None

if uploaded is not None:
    temp_dir = tempfile.TemporaryDirectory()
    source_path = Path(temp_dir.name) / uploaded.name
    source_path.write_bytes(uploaded.getbuffer())


analyze_clicked = st.button("Analyze document", type="primary", use_container_width=True)

if analyze_clicked and source_path is None:
    st.error("Upload a document first.")

if analyze_clicked and source_path is not None:
    with tempfile.TemporaryDirectory() as out_dir:
        with st.spinner("Processing document..."):
            result = process_document(
                str(source_path),
                output_format=output_format,
                hf_model=model,
                output_dir=out_dir,
                hf_api_key=hf_api_key,
                mongodb_uri=mongodb_uri,
                mongodb_db=mongodb_db,
                mongodb_collection=mongodb_collection,
            )

        metrics = result.get("metrics", {})
        ai = result.get("ai_analysis", {})

        readiness = ai.get("migration_readiness", "N/A")
        score = ai.get("readiness_score", "N/A")
        readability = ai.get("readability_level", "N/A")

        st.success(f"Analysis complete. Readiness: {readiness}")

        col1, col2, col3, col4 = st.columns(4)
        cards = [
            ("Pages", metrics.get("page_count", 0)),
            ("Words", metrics.get("word_count", 0)),
            ("Headings", metrics.get("heading_count", 0)),
            ("Avg words / paragraph", _metric_value(metrics.get("avg_words_per_paragraph", 0))),
        ]
        for column, (label, value) in zip([col1, col2, col3, col4], cards):
            with column:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">{label}</div>'
                    f'<div class="metric-value">{value}</div></div>',
                    unsafe_allow_html=True,
                )

        st.subheader("Migration Signal")
        signal_col1, signal_col2, signal_col3 = st.columns(3)
        signal_col1.metric("Readability", readability)
        signal_col2.metric("Readiness", readiness)
        signal_col3.metric("Score", score)

        left, right = st.columns(2)
        with left:
            st.subheader("Metrics")
            st.json(metrics)
        with right:
            st.subheader("AI Analysis")
            st.json(ai)

        st.subheader("Recommendations")
        for item in ai.get("suggestions", []):
            st.write(f"- {item}")

        summary_path = Path(out_dir) / f"{source_path.stem}_summary.txt"
        json_path = Path(out_dir) / f"{source_path.stem}_report.json"
        summary_text = _read_text(summary_path)
        json_text = _read_text(json_path)

        download_col1, download_col2 = st.columns(2)
        with download_col1:
            if json_text:
                st.download_button(
                    "Download JSON report",
                    data=json_text,
                    file_name=json_path.name,
                    mime="application/json",
                    use_container_width=True,
                )
        with download_col2:
            if summary_text:
                st.download_button(
                    "Download summary report",
                    data=summary_text,
                    file_name=summary_path.name,
                    mime="text/plain",
                    use_container_width=True,
                )

        if summary_text:
            with st.expander("Preview summary report", expanded=False):
                st.text(summary_text)

        st.subheader("Recent Database Records")
        try:
            store = LocalAnalysisStore(mongodb_uri, db_name=mongodb_db, collection_name=mongodb_collection)
            recent = store.list_recent(limit=10)
            if recent:
                st.dataframe(recent, use_container_width=True, hide_index=True)
            else:
                st.info("No saved analyses yet.")
        except Exception as exc:
            st.warning(f"Could not load recent database records: {exc}")

        if temp_dir is not None:
            temp_dir.cleanup()
