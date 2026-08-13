import os

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from . import ENV_PATH

GATEWAY_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{model}"

load_dotenv(ENV_PATH)
load_dotenv()  # fallback: .env found from cwd, for non-editable installs


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout | requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        if exc.response is None:
            return False
        if exc.response.status_code == 429 or exc.response.status_code >= 500:
            return True
        # Error 5024 "JSON Model couldn't be met": constrained generation
        # failed for this sample; surfaced as a 403 but retryable.
        return exc.response.status_code == 403 and '"code":5024' in exc.response.text
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
def run(model: str, payload: dict) -> dict:
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
        timeout=180,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(f"Workers AI error for {model}: {body.get('errors')}")
    return body["result"]
