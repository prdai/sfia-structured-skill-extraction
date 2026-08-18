from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = REPO_ROOT / "data" / "sfia-dataset.json"
ENV_PATH = REPO_ROOT / "llm-matcher" / ".env"

MODEL = "@cf/google/gemma-4-26b-a4b-it"

SWEEP_MODELS = [
    "@cf/meta/llama-3.1-8b-instruct-fast",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/qwen/qwen3-30b-a3b-fp8",
    "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "@cf/google/gemma-4-26b-a4b-it",
    "@cf/moonshotai/kimi-k2.6",
    "@cf/moonshotai/kimi-k2.7-code",
    "@cf/nvidia/nemotron-3-120b-a12b",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/zai-org/glm-5.2",
]
