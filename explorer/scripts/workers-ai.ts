import { EMBEDDING_MODEL } from "../src/lib/retrieval-config";

// Same AI Gateway route and X-Auth credentials the Python matchers use, so the
// repo's existing CF_* env vars work unchanged; see
// embedding-matcher/src/embedding_matcher/workers_ai.py.
const GATEWAY_URL = "https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{model}";
const DEFAULT_GATEWAY = "structured-extraction";
const MAX_ATTEMPTS = 4;
const BACKOFF_MIN_MS = 1_000;
const BACKOFF_MAX_MS = 20_000;

function credentials() {
  const accountId = Bun.env.CF_ACCOUNT_ID;
  const email = Bun.env.CF_API_EMAIL;
  const key = Bun.env.CF_API_KEY;

  if (!accountId || !email || !key) {
    throw new Error(
      "Set CF_ACCOUNT_ID, CF_API_EMAIL and CF_API_KEY (optionally CF_GATEWAY_ID) before seeding. " +
        "The same values the Python matchers use in embedding-matcher/.env work here.",
    );
  }

  return { accountId, email, key, gateway: Bun.env.CF_GATEWAY_ID ?? DEFAULT_GATEWAY };
}

function retryable(status: number): boolean {
  return status === 429 || status >= 500;
}

async function run<T>(model: string, payload: unknown): Promise<T> {
  const { accountId, email, key, gateway } = credentials();
  const url = GATEWAY_URL.replace("{account_id}", accountId)
    .replace("{gateway_id}", gateway)
    .replace("{model}", model);

  for (let attempt = 1; ; attempt += 1) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-Auth-Email": email,
        "X-Auth-Key": key,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (retryable(response.status) && attempt < MAX_ATTEMPTS) {
        const delay = Math.min(BACKOFF_MIN_MS * 2 ** (attempt - 1), BACKOFF_MAX_MS);
        console.error(`${model}: HTTP ${response.status}, retrying in ${delay}ms`);
        await Bun.sleep(delay);
        continue;
      }
      throw new Error(`Workers AI ${model} failed: HTTP ${response.status} ${await response.text()}`);
    }

    const body = (await response.json()) as { success: boolean; errors?: unknown; result: T };
    if (!body.success) {
      throw new Error(`Workers AI ${model} error: ${JSON.stringify(body.errors)}`);
    }
    return body.result;
  }
}

export async function embed(texts: string[]): Promise<number[][]> {
  const result = await run<{ data: number[][] }>(EMBEDDING_MODEL, { text: texts });
  return result.data;
}
