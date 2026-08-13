import json
import os

import requests
from crewai.llms.base_llm import BaseLLM
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

GATEWAY_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{model}"


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout | requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        return exc.response is not None and (exc.response.status_code == 429 or exc.response.status_code >= 500)
    return False


class WorkersAILLM(BaseLLM):
    """Cloudflare Workers AI backend for CrewAI agents, routed through AI Gateway.

    Workers AI's OpenAI-compatible endpoint (/ai/v1/chat/completions) only
    accepts a scoped API Token as a Bearer header; this account only has a
    Global API Key (X-Auth-Email + X-Auth-Key), which the OpenAI-compatible
    endpoint rejects. Both the native /ai/run/{model} endpoint and the AI
    Gateway proxy (gateway.ai.cloudflare.com/v1/{account}/{gateway}/
    workers-ai/{model}) accept the Global API Key, so this bypasses litellm
    entirely and calls the gateway URL directly per crewai.llms.base_llm.
    BaseLLM's documented extension point. Routing through the gateway (vs.
    the native endpoint) adds request logging/caching/analytics - see
    https://dash.cloudflare.com -> AI Gateway -> structured-extraction for
    per-request cost and token usage.
    """

    def __init__(self, model: str, **kwargs):
        super().__init__(model=model, provider="cloudflare-workers-ai", **kwargs)
        self._account_id = os.environ["CF_ACCOUNT_ID"]
        self._gateway_id = os.environ.get("CF_GATEWAY_ID", "structured-extraction")
        self._email = os.environ["CF_API_EMAIL"]
        self._key = os.environ["CF_API_KEY"]

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
              from_task=None, from_agent=None, response_model=None):
        formatted = self._format_messages(messages)
        body = self._request(formatted)
        text = body["result"]["response"]
        if isinstance(text, dict):
            text = json.dumps(text)
        text = self._apply_stop_words(text)
        return self._validate_structured_output(text, response_model) if response_model else text

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _request(self, formatted_messages):
        url = GATEWAY_URL.format(
            account_id=self._account_id, gateway_id=self._gateway_id, model=self.model
        )
        resp = requests.post(
            url,
            headers={
                "X-Auth-Email": self._email,
                "X-Auth-Key": self._key,
                "Content-Type": "application/json",
            },
            json={
                "messages": formatted_messages,
                "temperature": self.temperature if self.temperature is not None else 0.2,
                "max_tokens": self.max_tokens or 1024,
            },
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(f"Workers AI error for {self.model}: {body.get('errors')}")
        return body
