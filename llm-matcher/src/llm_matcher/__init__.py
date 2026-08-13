from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = REPO_ROOT / "data" / "sfia-dataset.json"
ENV_PATH = REPO_ROOT / "llm-matcher" / ".env"

MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"

SWEEP_MODELS = [
    "@cf/meta/llama-3.1-8b-instruct-fast",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/qwen/qwen3-30b-a3b-fp8",
]
