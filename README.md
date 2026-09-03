# sfia-structured-skill-extraction

Maps free-text job, course, and skill descriptions to SFIA skills and
responsibility levels (1-7). Multiple matching strategies live side by side so
they can be compared on the same dataset.

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
```
