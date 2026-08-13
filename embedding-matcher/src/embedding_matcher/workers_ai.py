import os
import re

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from . import EMBEDDING_MODEL, ENV_PATH, RERANKER_MODEL

GATEWAY_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{model}"

load_dotenv(ENV_PATH)
load_dotenv()  # fallback: .env found from cwd, for non-editable installs


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout | requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        return exc.response is not None and (exc.response.status_code == 429 or exc.response.status_code >= 500)
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
def _run(model: str, payload: dict) -> dict:
    url = GATEWAY_URL.format(
        account_id=os.environ["CF_ACCOUNT_ID"],
        gateway_id=os.environ.get("CF_GATEWAY_ID", "structured-extraction"),
        model=model,
    )
    resp = requests.post(
        url,
        headers={
            "X-Auth-Email": os.environ["CF_API_EMAIL"],
            "X-Auth-Key": os.environ["CF_API_KEY"],
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"Workers AI error for {model}: {body.get('errors')}")
    return body["result"]


def embed(texts: list[str]) -> list[list[float]]:
    result = _run(EMBEDDING_MODEL, {"text": texts})
    return result["data"]


RERANK_PROMPT = (
    "You are scoring how relevant an SFIA skill description is to a query.\n\n"
    "Query (a job/course/role description):\n{query}\n\n"
    "Candidate skill description:\n{candidate}\n\n"
    "How relevant is the candidate to the query? Reply with ONLY a number "
    "between 0 and 1 (e.g. 0.85), nothing else."
)

NUMBER_RE = re.compile(r"[01](?:\.\d+)?")


def rerank_score(query: str, candidate: str) -> float:
    result = _run(RERANKER_MODEL, {
        "messages": [{"role": "user", "content": RERANK_PROMPT.format(query=query, candidate=candidate)}],
        "temperature": 0.0,
        "max_tokens": 8,
    })
    match = NUMBER_RE.search(str(result["response"]))
    return float(match.group()) if match else 0.0
