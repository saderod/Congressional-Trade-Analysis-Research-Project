"""Project-wide configuration constants and filesystem paths."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DUCKDB_PATH = PROCESSED_DIR / "db.duckdb"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FINBERT_MODEL = "ProsusAI/finbert"
OLLAMA_MODEL = "llama3.1:8b"
