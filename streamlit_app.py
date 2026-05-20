"""Streamlit UI for the document migration readiness tool."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import altair as alt
import streamlit as st

from config.settings import (
    MONGODB_URI,
    MONGODB_DB_NAME,
    MONGODB_COLLECTION,
    HUGGING_FACE_MODEL,
    HUGGING_FACE_API_KEY as DEFAULT_HF_API_KEY,
    LLM_BACKEND,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)
from main import process_document
from src.ai.prompts import CHAT_SYSTEM_PROMPT, build_chat_prompt
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


def _clean_number(value):
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _bar_chart(title: str, pairs, color: str):
    data = alt.Data(values=[{"label": str(label), "value": _clean_number(value)} for label, value in pairs])
    return (
        alt.Chart(data)
        .mark_bar(color=color)
        .encode(
            x=alt.X("label:N", sort=None, title=None),
            y=alt.Y("value:Q", title=None),
            tooltip=[alt.Tooltip("label:N", title="Metric"), alt.Tooltip("value:Q", title="Value")],
        )
        .properties(height=250, title=title)
    )


def _render_overview(results):
    if not results:
        return

    st.subheader("Batch Overview")
    left, right = st.columns(2)

    readiness_data = [
        (result.get("file_name", f"File {index + 1}"), result.get("ai_analysis", {}).get("readiness_score", 0))
        for index, result in enumerate(results)
    ]
    image_data = [
        (result.get("file_name", f"File {index + 1}"), result.get("metrics", {}).get("image_count", 0))
        for index, result in enumerate(results)
    ]

    with left:
        st.altair_chart(_bar_chart("Readiness score by file", readiness_data, "#7aa2f7"), use_container_width=True)
    with right:
        st.altair_chart(_bar_chart("Image count by file", image_data, "#f7b267"), use_container_width=True)


def _render_quality_charts(metrics, ai):
    left, right = st.columns(2)

    with left:
        scale_pairs = [
            ("Pages", metrics.get("page_count", 0)),
            ("Words", metrics.get("word_count", 0)),
            ("Paragraphs", metrics.get("paragraph_count", 0)),
            ("Headings", metrics.get("heading_count", 0)),
            ("Images", metrics.get("image_count", 0)),
        ]
        st.altair_chart(_bar_chart("Document scale", scale_pairs, "#6ee7b7"), use_container_width=True)

    with right:
        quality_pairs = [
            ("Readiness score", ai.get("readiness_score", 0)),
            ("Links", metrics.get("link_count", 0)),
            ("Duplicate headings", metrics.get("duplicate_headings", 0)),
            ("Empty sections", metrics.get("empty_sections", 0)),
            ("Lexical density", metrics.get("lexical_density_pct", 0)),
        ]
        st.altair_chart(_bar_chart("Migration factors", quality_pairs, "#f9a8d4"), use_container_width=True)


def _build_chat_client(sidebar_model: str, sidebar_api_key: str):
    backend = LLM_BACKEND.lower()

    if backend == "ollama":
        try:
            from src.ai.ollama_client import OllamaClient

            return OllamaClient(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)
        except Exception:
            return None

    api_key = (sidebar_api_key or DEFAULT_HF_API_KEY).strip()
    if backend == "huggingface" and api_key:
        try:
            from src.ai.huggingface_client import HuggingFaceClient

            return HuggingFaceClient(model=sidebar_model, api_key=api_key)
        except Exception:
            return None

    return None


def _local_chat_answer(question: str, metrics: dict, ai: dict) -> str:
    q = question.lower()
    title = ai.get("title") or metrics.get("title") or "this document"
    readiness = ai.get("migration_readiness", "N/A")
    score = ai.get("readiness_score", "N/A")

    if any(term in q for term in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
        return (
            "Hi. I can explain this document in simple terms, or answer questions about readiness, readability, structure, "
            "images, links, issues, and suggestions. Try asking: 'explain the document' or 'what are the main issues?'."
        )

    if any(term in q for term in ["explain the document", "explain this document", "explain document", "summary", "summarize", "what is this document", "tell me about the document"]):
        page_count = metrics.get("page_count", 0)
        word_count = metrics.get("word_count", 0)
        heading_count = metrics.get("heading_count", 0)
        image_count = metrics.get("image_count", 0)
        link_count = metrics.get("link_count", 0)

        return (
            f"{title} looks like a structured document with {page_count} pages, {word_count} words, {heading_count} headings, "
            f"{image_count} images, and {link_count} links. The report says it is '{readiness}' with a score of {score}. "
            f"Readability is '{ai.get('readability_level', 'N/A')}' because {ai.get('readability_reason', '')}. "
            f"Structural quality is '{ai.get('structural_quality', 'N/A')}' because {ai.get('structure_notes', '')}. "
            f"Main issues are: {'; '.join(ai.get('issues', [])[:3]) if ai.get('issues') else 'none detected'}. "
            f"Suggested next steps: {'; '.join(ai.get('suggestions', [])[:3]) if ai.get('suggestions') else 'review formatting and links before migration.'}"
        )

    if any(term in q for term in ["image", "images", "picture", "photo"]):
        count = metrics.get("image_count", 0)
        return (
            f"This document has {count} images. A high image count usually increases migration effort "
            f"because assets need to be extracted, named, verified, and uploaded correctly."
        )

    if any(term in q for term in ["readiness", "ready", "score"]):
        return (
            f"The document is rated '{readiness}' with a readiness score of {score}. "
            f"That means the content is generally ready, but the report still highlights the items listed in issues and suggestions."
        )

    if any(term in q for term in ["issue", "problem", "risk"]):
        issues = ai.get("issues", [])
        if issues:
            return "Main issues found: " + "; ".join(issues[:3])
        return "No major issues were detected in the current analysis."

    if any(term in q for term in ["suggestion", "improve", "fix", "action"]):
        suggestions = ai.get("suggestions", [])
        if suggestions:
            return "Suggested actions: " + "; ".join(suggestions[:3])
        return "The report does not include specific suggestions beyond the general review steps."

    if any(term in q for term in ["heading", "structure", "section"]):
        return (
            f"The document has {metrics.get('heading_count', 0)} headings, a maximum heading depth of "
            f"{metrics.get('max_heading_depth', 0)}, and {metrics.get('duplicate_headings', 0)} duplicate headings. "
            f"That is why the structural quality was rated as '{ai.get('structural_quality', 'N/A')}'."
        )

    if any(term in q for term in ["readability", "easy", "complex", "clear"]):
        return (
            f"Readability was marked '{ai.get('readability_level', 'N/A')}' because {ai.get('readability_reason', '')}. "
            f"You can also look at the average words per paragraph ({metrics.get('avg_words_per_paragraph', 'N/A')}) as the main signal."
        )

    return (
        "I can explain the document, its readiness score, readability, structure, images, links, issues, and suggestions. "
        "Try asking: 'explain the document', 'what are the main issues?', or 'why is the score high?'."
    )


def _generate_chat_answer(question: str, result: dict, sidebar_model: str, sidebar_api_key: str) -> str:
    metrics = result.get("metrics", {})
    ai = result.get("ai_analysis", {})
    client = _build_chat_client(sidebar_model, sidebar_api_key)

    if client is not None:
        try:
            prompt = build_chat_prompt(
                title=result.get("file_name"),
                file_type=result.get("file_type", ""),
                metrics=metrics,
                ai_analysis=ai,
                question=question,
            )
            return client.generate(prompt=prompt, system=CHAT_SYSTEM_PROMPT).strip()
        except Exception:
            pass

    return _local_chat_answer(question, metrics, ai)


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

    if st.button("Clear dashboard", use_container_width=True):
        st.session_state.pop("analysis_results", None)
        for key in list(st.session_state.keys()):
            if key.startswith("chat_history_") or key.startswith("chat_input_"):
                st.session_state.pop(key, None)
        st.rerun()

    st.caption(
        "The UI uses the same pipeline as the CLI and can fall back to heuristic analysis if the LLM is unavailable."
    )


uploaded_files = st.file_uploader(
    "Upload .docx or .pdf files (multiple allowed)", type=["docx", "pdf"], accept_multiple_files=True
)

if not uploaded_files and not st.session_state.get("analysis_results"):
    st.info("Upload one or more documents to analyze.")

analyze_clicked = st.button("Analyze documents", type="primary", use_container_width=True)

if analyze_clicked:
    if not uploaded_files:
        st.error("Upload at least one document first.")
    else:
        temp_dir = tempfile.TemporaryDirectory()
        temp_paths = []
        for up in uploaded_files:
            p = Path(temp_dir.name) / up.name
            p.write_bytes(up.getbuffer())
            temp_paths.append(p)

        results = []
        with st.spinner("Processing documents..."):
            for src in temp_paths:
                try:
                    out_tmp = tempfile.TemporaryDirectory()
                    res = process_document(
                        str(src),
                        output_format=output_format,
                        hf_model=model,
                        output_dir=out_tmp.name,
                        hf_api_key=hf_api_key,
                        mongodb_uri=mongodb_uri,
                        mongodb_db=mongodb_db,
                        mongodb_collection=mongodb_collection,
                    )
                    res["__out_dir"] = out_tmp
                    res["__report_id"] = uuid.uuid4().hex
                    results.append(res)
                except Exception as e:
                    st.error(f"Failed to process {src.name}: {e}")

        if results:
            st.session_state["analysis_results"] = results
            st.success(f"Processed {len(results)} document(s).")


results = st.session_state.get("analysis_results", [])

if results:
    _render_overview(results)

    tabs = st.tabs([Path(r["file_name"]).stem for r in results])
    for tab, res in zip(tabs, results):
        with tab:
            metrics = res.get("metrics", {})
            ai = res.get("ai_analysis", {})

            readiness = ai.get("migration_readiness", "N/A")
            score = ai.get("readiness_score", "N/A")
            readability = ai.get("readability_level", "N/A")

            st.success(f"Analysis complete. Readiness: {readiness}")

            col1, col2, col3, col4 = st.columns(4)
            cards = [
                ("Pages", metrics.get("page_count", 0)),
                ("Words", metrics.get("word_count", 0)),
                ("Headings", metrics.get("heading_count", 0)),
                ("Images", metrics.get("image_count", 0)),
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

            st.progress(min(int(_clean_number(score)) / 100, 1.0))

            st.subheader("Visual Summary")
            _render_quality_charts(metrics, ai)

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

            st.subheader("Chat with this report")
            chat_key = f"chat_history_{res['__report_id']}"
            reset_chat_clicked = st.button("Reset chat for this report", key=f"reset_chat_{res['__report_id']}")
            if reset_chat_clicked:
                st.session_state.pop(chat_key, None)
                st.rerun()

            if chat_key not in st.session_state:
                st.session_state[chat_key] = [
                    {
                        "role": "assistant",
                        "content": (
                            "Ask me to explain the document, or ask about readiness, readability, structure, images, links, issues, or suggestions."
                        ),
                    }
                ]

            for message in st.session_state[chat_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            user_question = st.chat_input("Ask a question about this document", key=f"chat_input_{res['__report_id']}")
            if user_question:
                st.session_state[chat_key].append({"role": "user", "content": user_question})
                answer = _generate_chat_answer(user_question, res, model, hf_api_key)
                st.session_state[chat_key].append({"role": "assistant", "content": answer})
                st.rerun()

            out_tmp = res.get("__out_dir")
            if out_tmp:
                summary_path = Path(out_tmp.name) / f"{Path(res.get('file_name')).stem}_summary.md"
                json_path = Path(out_tmp.name) / f"{Path(res.get('file_name')).stem}_report.json"
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
                            "Download summary report (MD)",
                            data=summary_text,
                            file_name=summary_path.name,
                            mime="text/markdown",
                            use_container_width=True,
                        )

                if summary_text:
                    with st.expander("Preview summary report", expanded=False):
                        st.markdown(summary_text)

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
