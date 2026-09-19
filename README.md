# sfia-structured-skill-extraction

Maps free-text job, course, and skill descriptions to SFIA skills and
responsibility levels (1-7). Multiple matching strategies live side by side so
they can be compared on the same dataset.

This repo is organized so someone can either:

1. **Replicate matcher results quickly** using the checked-in datasets, or
2. **Rebuild the pipeline end-to-end** from a fresh SFIA crawl.

## Layout

- `data/` — crawled SFIA pages, the SFIA 9 summary chart, and the extracted
  skill-level corpus used by the matchers.
- `crawler/` — Cloudflare Worker that crawls sfia-online.org (Browser
  Rendering `/crawl` REST endpoint) and stores the raw dataset in R2.
- `structured-extraction/` — extracts and verifies the skill-level corpus
  from the raw crawl output.
- `keyword-matcher/` — BM25 lexical-matching baseline.
- `embedding-matcher/` — Qdrant retrieval with pointwise LLM reranking.
- `llm-matcher/` — pure Workers AI LLM matching with constrained JSON output.
- `agentic-rag-matcher/` — single-agent RAG over dense and BM25 retrieval.
- `multi-agent-rag-matcher/` — retriever, matcher, and verifier RAG crew.

## Usage

Each implementation dir is a uv-managed Python project (except `crawler/`,
which is a Worker). The root `Makefile` orchestrates them:

```
make help
make vector-db
make ingest
make search TEXT="builds and tests python services"
make llm-match TEXT="leads solution architecture for complex enterprise systems"
```

## Replication quickstart (from checked-in data)

This path is for reproducing matcher behavior/evals without re-crawling SFIA.

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (for local Qdrant used by `embedding-matcher` and both RAG matchers)
- Cloudflare credentials in component `.env` files for LLM/embedding calls:
  `CF_ACCOUNT_ID`, `CF_API_EMAIL`, `CF_API_KEY` (and optional `CF_GATEWAY_ID`)

### 1) Run local baselines manually

From repo root:

```bash
make vector-db
make ingest
make search TEXT="builds and tests python services"
make llm-match TEXT="leads solution architecture for complex enterprise systems"
```

### 2) Re-run eval harness

```bash
cd /home/runner/work/sfia-structured-skill-extraction/sfia-structured-skill-extraction/evals
uv venv && uv pip install -e .
uv run eval-keyword
uv run eval-embedding
uv run eval-llm
uv run eval-agentic-rag
uv run eval-multi-agent-rag
uv run eval-compare
```

Outputs are written to `evals/results.json` (and model/config sweeps log to
`evals/experiments.json`).

## End-to-end data rebuild workflow (crawl -> extract -> match)

Use this if you need to regenerate the underlying SFIA corpus, not just rerun
matchers on the existing checked-in files.

1. **Crawl SFIA pages** (`crawler/`) and produce raw dataset JSON.
2. **Extract skill-level records** (`structured-extraction/`) from crawl output.
3. **Refresh shared matcher corpus** by copying:
   - `structured-extraction/output/skill-level-records.json` ->
     `data/sfia-skill-level-records.json`
4. **Re-ingest vectors + rerun matchers/evals** using the quickstart commands
   above.

See component READMEs for full per-module setup details:
`crawler/README.md`, `structured-extraction/README.md`, `embedding-matcher/README.md`,
`llm-matcher/README.md`, `agentic-rag-matcher/README.md`, `multi-agent-rag-matcher/README.md`,
and `evals/README.md`.
