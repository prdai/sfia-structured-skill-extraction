# SFIA Explorer

Public web demo for the single-agent SFIA matcher. Paste a role description,
get SFIA 9 skills and responsibility levels with short evidence excerpts.

This is a port of the research implementation, not the Python/CrewAI artifact.
It keeps the prompt, the two retrieval tools, and the structured output, and
runs on Cloudflare Workers with Vectorize and Workers AI. The Python matchers,
corpus pipeline, and evaluation harness live in the repository root.

## Stack

- Astro static pages + one React island (`@ai-sdk/react`)
- Vercel AI SDK (`streamText`, `tool`, `DefaultChatTransport`) in a Worker
- Cloudflare Vectorize for semantic retrieval and in-worker BM25 for keyword
  retrieval, mirroring the Python matchers' scoring
- Workers AI `@cf/nvidia/nemotron-3-120b-a12b`
- AI Gateway spending limits and response caching, Turnstile

The agent has two tools, matching the paper's design:

| Tool | Backend | Use |
| --- | --- | --- |
| `semantic_skill_search` | Vectorize + LLM rerank | meaning-based matches |
| `keyword_skill_search` | in-worker BM25 | jargon, acronyms, exact terms |

The model must call both before it can submit matches.

## Local development

```bash
bun install
bun run dev      # http://localhost:4321
```

`src/data/skills.json` and `src/data/records.json` are checked-in snapshots of
the SFIA catalogue and skill-level descriptions. Builds use these files directly.

`astro dev` serves the static pages but not the Worker API. To exercise the API,
run `bun run dev:worker` in another terminal; `/api` is proxied to
`http://localhost:8787`. Vectorize and Workers AI are remote bindings, so use
`bunx wrangler dev --remote` when you need real retrieval.

Turnstile is skipped when `PUBLIC_TURNSTILE_SITE_KEY` is unset. The API also
skips server verification when the `TURNSTILE_SECRET` binding is unset. Set
both for production; setting only the secret will reject every request.

## Cloudflare setup

Requires a Workers Paid plan for Vectorize and paid Workers AI models.

### 1. Vectorize index

Retrieval mirrors the Python matchers: one vector per skill-level record,
embedding `"<skill name>: <level description>"`, with no chunking, so a record
is the atomic retrieval unit on both sides. The keyword tool runs the same
BM25 scoring in the worker over the record bodies bundled at build time.

Seeding needs the same Cloudflare credentials the Python matchers use:

```bash
export CF_ACCOUNT_ID=...
export CF_API_EMAIL=...
export CF_API_KEY=...
bun run seed
```

`bun run seed` embeds all 669 records through the AI Gateway and writes
`vectors.ndjson`. It prints the index creation and upsert commands with the
observed embedding dimension:

```bash
bunx wrangler vectorize create sfia-skill-level-records --dimensions=1024 --metric=cosine
bunx wrangler vectorize upsert sfia-skill-level-records --file=vectors.ndjson
```

The index name must match `index_name` in `wrangler.jsonc`. Re-seeding is
idempotent: vector ids are `CODE-LEVEL`, so an upsert replaces in place.

### 2. Retrieval behaviour

Shared constants live in `src/lib/retrieval-config.ts`, mirroring
`embedding-matcher/src/embedding_matcher/__init__.py`:

- semantic search retrieves `RETRIEVAL_K = 20`, reranks every candidate with
  `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, and keeps scores at or above
  `RERANK_THRESHOLD = 0.6`
- keyword search scores BM25 over the record bodies, normalises by the top
  score, and keeps scores at or above `KEYWORD_THRESHOLD = 0.7`
- both tools return at most `TOOL_RESULT_LIMIT = 10` records

Reranking costs one LLM call per retrieved candidate, so a single semantic
search is 20 calls. The agent's `SEARCH_LIMIT` caps a request at 6 searches.

### 3. AI Gateway and secrets

Create an AI Gateway named `sfia-explorer` in the same Cloudflare account.
`ai-gateway.json` contains the creation payload. With a Cloudflare API token
that has AI Gateway Edit permission available as `CLOUDFLARE_API_TOKEN`, run
from `explorer/`:

```bash
curl --fail-with-body \
  "https://api.cloudflare.com/client/v4/accounts/6503f7d355399abee9e748d3100675d4/ai-gateway/gateways" \
  --header "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary @ai-gateway.json
```

The payload configures:

- Enable response caching with a 30-day TTL (2,592,000 seconds).
- Add a shared $2.50 rolling 30-day spend limit, with no model or provider filters.
- Keep Workers AI billing on postpaid.

The agent, query embeddings, and reranker all route through this gateway.
`AI_GATEWAY_ID` in `wrangler.jsonc` selects its name. Changing the JSON payload
alone does not update an existing gateway; use its dashboard settings or API.
Gateway caching reuses identical model requests; it does not provide semantic
similarity caching. See the [caching documentation](https://developers.cloudflare.com/ai-gateway/features/caching/).

```bash
bunx wrangler secret put TURNSTILE_SECRET
```

Create a Turnstile widget for `sfia.prdai.dev`, then put the site key in
`.env` before building:

```bash
cp .env.example .env
# PUBLIC_TURNSTILE_SITE_KEY=...
```

### 4. Deploy

```bash
bun run deploy
```

`wrangler.jsonc` already routes `sfia.prdai.dev` as a custom domain. Change the
route if you deploy under a different host.

## Limits and cost

- Shared $2.50 rolling 30-day model-spending limit configured in AI Gateway
- Identical model requests can be served from the Gateway cache
- No application result cache or per-IP daily counter
- Nemotron is roughly $0.009 per match; reranking adds 20 llama-3.3-70b calls
  per semantic search, and keyword search costs nothing beyond worker CPU

Adjust spending limits and caching in the AI Gateway dashboard. Spend limits
are eventually consistent, so concurrent requests can briefly exceed the cap.
They cover routed model inference, not Vectorize or Worker charges. See
[spend limits](https://developers.cloudflare.com/ai-gateway/features/spend-limits/).

## Differences from the paper

See `/method/` in the deployed app. The important ones:

- Qdrant is replaced by Vectorize; the indexing unit, embedding model, BM25
  scoring and retrieval constants match the Python matchers.
- The model is the fastest sweep model, not the paper's final GLM run.
- The agent loop is a TypeScript port, not CrewAI.

These make the deployed configuration a variant of the evaluated one. Re-run
the 30-role harness before citing demo numbers.

## Content note

Skill pages show short excerpts from the public SFIA 9 documentation and link
to the official pages. SFIA is a trademark of the SFIA Foundation; this project
is independent and not endorsed by the Foundation. See the repository root for
the corpus and the paper.
