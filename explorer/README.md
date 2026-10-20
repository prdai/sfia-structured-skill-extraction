# SFIA Explorer

Public web demo for the single-agent SFIA matcher. Paste a role description,
get SFIA 9 skills and responsibility levels with short evidence excerpts.

This is a port of the research implementation, not the Python/CrewAI artifact.
It keeps the prompt, the two retrieval tools, and the structured output, and
runs on Cloudflare Workers with AI Search and Workers AI. The Python matchers,
corpus pipeline, and evaluation harness live in the repository root.

## Stack

- Astro static pages + one React island (`@ai-sdk/react`)
- Vercel AI SDK (`streamText`, `tool`, `DefaultChatTransport`) in a Worker
- Cloudflare AI Search for retrieval: `retrieval_type: "vector"` for semantic
  search and `retrieval_type: "keyword"` for BM25
- Workers AI `@cf/nvidia/nemotron-3-120b-a12b`
- KV result cache, Durable Object budget counters, Turnstile, Analytics Engine

The agent has two tools, matching the paper's design:

| Tool | Backend | Use |
| --- | --- | --- |
| `semantic_skill_search` | AI Search vector | meaning-based matches |
| `keyword_skill_search` | AI Search BM25 | jargon, acronyms, exact terms |

The model must call both before it can submit matches.

## Local development

```bash
npm install
npm run data     # regenerate src/data/skills.json from ../data
npm run dev      # http://localhost:4321
```

`astro dev` serves the static pages but not the Worker API. To exercise the API,
run `npm run dev:worker` in another terminal; `/api` is proxied to
`http://localhost:8787`. AI Search and Workers AI are remote bindings, so use
`npx wrangler dev --remote` when you need real retrieval.

Turnstile is skipped when `PUBLIC_TURNSTILE_SITE_KEY` is unset. The API also
skips server verification when the `TURNSTILE_SECRET` binding is unset. Set
both for production; setting only the secret will reject every request.

## Cloudflare setup

Requires a Workers Paid plan (AI Search paid models and Durable Objects).

### 1. R2 corpus

```bash
npx wrangler r2 bucket create sfia-corpus
```

Create an R2 API token with object read/write access, then:

```bash
export R2_ACCOUNT_ID=...
export R2_ACCESS_KEY_ID=...
export R2_SECRET_ACCESS_KEY=...
export R2_BUCKET=sfia-corpus
npm run seed
```

The seed script uploads one object per skill-level record
(`records/CODE-LEVEL.txt`) with `code`, `skill`, `level`, and `source_url`
metadata.

### 2. AI Search instance

The keyword tool needs hybrid search enabled at the instance level:

```bash
npx wrangler ai-search create sfia-corpus \
  --type r2 \
  --source sfia-corpus \
  --hybrid-search \
  --chunk-size 256 \
  --chunk-overlap 0 \
  --max-num-results 10 \
  --custom-metadata code:text \
  --custom-metadata skill:text \
  --custom-metadata level:number \
  --custom-metadata source_url:text

npx wrangler ai-search jobs create sfia-corpus
```

The instance name must match `instance_name` in `wrangler.jsonc`.

### 3. KV cache and secrets

```bash
npx wrangler kv namespace create MATCH_CACHE
# put the returned id into wrangler.jsonc

npx wrangler secret put TURNSTILE_SECRET
```

Create a Turnstile widget for `sfia.prdai.dev`, then put the site key in
`.env` before building:

```bash
cp .env.example .env
# PUBLIC_TURNSTILE_SITE_KEY=...
```

### 4. Deploy

```bash
npm run deploy
```

`wrangler.jsonc` already routes `sfia.prdai.dev` as a custom domain. Change the
route if you deploy under a different host.

## Limits and cost

- `PER_IP_DAILY = 3` analyses per IP, per day
- `MONTHLY_MATCH_BUDGET = 500` paid matches per month
- KV cache keyed by normalized input, 30-day TTL
- Query text is logged anonymously to Analytics Engine; no IP addresses are stored
- Nemotron is roughly $0.009 per match; AI Search includes 1,000 semantic and
  1,000 full-text queries per month, and the corpus is ~70k ingestion tokens

Adjust the limits in `worker/index.ts` and `wrangler.jsonc`.

## Differences from the paper

See `/method/` in the deployed app. The important ones:

- The 20-candidate llama-3.3-70b reranker is removed.
- Qdrant is replaced by AI Search.
- The model is the fastest sweep model, not the paper's final GLM run.
- The agent loop is a TypeScript port, not CrewAI.

These make the deployed configuration a variant of the evaluated one. Re-run
the 30-role harness before citing demo numbers.

## Content note

Skill pages show short excerpts from the public SFIA 9 documentation and link
to the official pages. SFIA is a trademark of the SFIA Foundation; this project
is independent and not endorsed by the Foundation. See the repository root for
the corpus and the paper.
