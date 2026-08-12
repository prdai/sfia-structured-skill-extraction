# sfia-agentic-rag-skill-matcher

Maps free-text job, course, and skill descriptions to SFIA skills and
responsibility levels (1-7). Multiple matching strategies live side by side so
they can be compared on the same dataset.

## Layout

- `data/` — SFIA dataset (crawled skill and level descriptions). Currently a
  placeholder JSON shaped like the crawler output.
- `crawler/` — Cloudflare Worker that crawls sfia-online.org (Browser
  Rendering `/crawl` REST endpoint) and produces the dataset. Code only, not
  deployed yet.
- `keyword-matcher/` — keyword/lexical matching baseline. Not implemented yet.
- `embedding-matcher/` — embeds the dataset into Qdrant (local, docker
  compose), searches input text, returns top-3 skills with levels.
- `llm-matcher/` — pure LLM matching, no retrieval. Local llama.cpp model,
  structured JSON output.
- `llm-rag-matcher/` — LLM + RAG pipeline. Current focus of work.

## Usage

Each implementation dir is a uv-managed Python project (except `crawler/`,
which is a Worker). The root `Makefile` orchestrates them:

```
make help
```
