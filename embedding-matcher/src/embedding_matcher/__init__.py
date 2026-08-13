from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATH = REPO_ROOT / "data" / "sfia-skill-level-records.json"
ENV_PATH = REPO_ROOT / "embedding-matcher" / ".env"

QDRANT_URL = "http://localhost:6333"
COLLECTION = "sfia-skill-level-records"

EMBEDDING_MODEL = "@cf/qwen/qwen3-embedding-0.6b"
RERANKER_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

RETRIEVAL_K = 20
RERANK_THRESHOLD = 0.6
