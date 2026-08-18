from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATH = REPO_ROOT / "data" / "sfia-skill-level-records.json"
ENV_PATH = REPO_ROOT / "agentic-rag-matcher" / ".env"

MODEL = "@cf/zai-org/glm-4.7-flash"

SWEEP_MODELS = [
    "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
    "@cf/google/gemma-4-26b-a4b-it",
    "@cf/moonshotai/kimi-k2.6",
    "@cf/moonshotai/kimi-k2.7-code",
    "@cf/nvidia/nemotron-3-120b-a12b",
    "@cf/zai-org/glm-4.7-flash",
    "@cf/zai-org/glm-5.2",
]
COMPAT_BASE_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/compat"
