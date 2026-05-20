# config/settings.py
# Central configuration for the doc-migration-tool.
# Override any value by setting the matching environment variable.

import os
from pathlib import Path

# Load environment variables from a local .env file when present
try:
	from dotenv import load_dotenv
	env_path = Path(__file__).resolve().parents[1] / '.env'
	if env_path.exists():
		load_dotenv(env_path)
except Exception:
	# If python-dotenv is not installed, silently continue using system env vars
	pass

# ── Ollama settings ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL",  "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL",     "llama3")
OLLAMA_TIMEOUT   = int(os.getenv("OLLAMA_TIMEOUT", "120"))   # seconds

# ── Output settings ───────────────────────────────────────────────────────────
OUTPUT_DIR       = os.getenv("OUTPUT_DIR",       "./sample_output")
DEFAULT_FORMAT   = os.getenv("OUTPUT_FORMAT",    "both")     # json | summary | both

# ── MongoDB settings ─────────────────────────────────────────────────────────
MONGODB_URI      = os.getenv("ANALYSIS_MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME  = os.getenv("ANALYSIS_MONGODB_DB", "doc_migration_tool")
MONGODB_COLLECTION = os.getenv("ANALYSIS_MONGODB_COLLECTION", "analyses")

# ── Hugging Face settings ────────────────────────────────────────────────────
HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY", "")
HUGGING_FACE_MODEL   = os.getenv(
	"HUGGING_FACE_MODEL",
	"meta-llama/Meta-Llama-3.1-8B-Instruct",
)

# ── Parser settings ───────────────────────────────────────────────────────────
MAX_EXCERPT_CHARS = int(os.getenv("MAX_EXCERPT_CHARS", "1500"))

# Which LLM backend to use: 'huggingface' or 'ollama'
LLM_BACKEND = os.getenv("LLM_BACKEND", "huggingface").lower()


# ── Metrics thresholds (used by fallback heuristics) ─────────────────────────
WORDS_PER_PAGE_ESTIMATE    = 350
EASY_READABILITY_MAX_WORDS = 25    # avg words/para
COMPLEX_READABILITY_MIN    = 60    # avg words/para
MIN_HEADING_RATIO          = 0.15  # headings / paragraphs for "well-organized"
