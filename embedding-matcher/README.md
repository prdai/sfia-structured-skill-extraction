# embedding-matcher

Retrieve-and-rerank semantic matcher over the
`data/sfia-skill-level-records.json` corpus (from `structured-extraction/`):
bi-encoder embedding retrieval into a local Qdrant, then LLM-based pointwise
reranking, both model calls on Cloudflare Workers AI through the shared AI
Gateway (`structured-extraction`) for per-request cost visibility.

## Pipeline

1. **Ingest** — each corpus record's `(skill, level)` mapping becomes one
   Qdrant point. The embedded text is `"<skill name>: <level text>"`, not the
   level text alone (label + description concatenation, per the ESCO linking
   paper below). Embeddings: `@cf/qwen/qwen3-embedding-0.6b`, cosine distance.
2. **Retrieve** — query text embedded with the same model, top-20 nearest
   points fetched (k=20 per SkillRouter's compact-pipeline precedent).
3. **Rerank** — each of the 20 candidates scored pointwise by
   `@cf/meta/llama-3.3-70b-instruct-fp8-fast` ("how relevant is this
   candidate to the query, 0-1"). Everything scoring >= 0.6 is returned; no
   fixed top-n cap, since one input text can legitimately map to many
   `(skill, level)` pairs. Threshold chosen by sweep (below).

## Why this design (citations)

- ["Overview of the TalentCLEF 2026: Skill and Job Title Intelligence for
  Human Capital Management"](https://arxiv.org/abs/2606.31692) (CLEF; 2025
  edition: [DOI 10.1007/978-3-032-04354-2_24](https://doi.org/10.1007/978-3-032-04354-2_24)).
  Domain-exact precedent (job-skill matching shared task): the top Task B
  systems are all bi-encoder retrieval followed by a reranking stage; the
  winning systems used Qwen3-Embedding-family encoders, and two of the top
  three used LLM-based pointwise reranking - the architecture, encoder
  family, and reranking method adopted here.
- Zhang et al. (2025). ["Qwen3 Embedding: Advancing Text Embedding and
  Reranking Through Foundation Models"](https://arxiv.org/abs/2506.05176).
  The embedding model itself (0.6B is the compact size of the family; the
  larger siblings topped the TalentCLEF systems). Also describes the
  pointwise LLM relevance-scoring formulation this pipeline's reranker
  follows.
- ["Enhancing Job Matching: Occupation, Skill and Qualification Linking with
  the ESCO and EQF taxonomies"](https://arxiv.org/abs/2512.03195). Closest
  published analog to SFIA matching (linking free text to a competency
  taxonomy): cosine-similarity top-k sentence linking, and the finding that
  embedding the concatenation of label + description outperforms description
  alone - the reason ingest embeds `"<skill>: <text>"`.
- ["SkillRouter: Skill Routing for LLM Agents at Scale"](https://arxiv.org/abs/2603.22455).
  Cited for the retrieve-then-rerank budget only (top-20 retrieval before
  reranking in its compact 0.6B pipeline, same encoder as used here). Note
  its domain is agent tool-skill routing, not occupational skills - cited for
  pipeline configuration, not domain claims.

## Running

```
docker compose up -d      # local Qdrant
uv venv && uv pip install -e .
ingest                    # embed the corpus into Qdrant (one-off, ~700 points)
search "builds and tests python services"
```

Requires `CF_ACCOUNT_ID`, `CF_API_EMAIL`, `CF_API_KEY` (and optionally
`CF_GATEWAY_ID`) in `embedding-matcher/.env` (gitignored).

## Threshold sweep

Rerank threshold swept over all 30 eval roles (`sweep-embedding`; every
config's full metrics are in `evals/experiments.json`). Candidates are
scored once per role and thresholds derived offline, so the sweep costs one
eval, not eight. Clear precision/level-accuracy vs recall tradeoff:

| threshold | precision | recall | F1 | lvl_exact | lvl_within_1 |
|---|---|---|---|---|---|
| 0.95 | 0.000 | 0.000 | 0.000 | - | - |
| 0.9 | 0.167 | 0.050 | 0.075 | 0.500 | 0.833 |
| 0.8 | 0.187 | 0.106 | 0.125 | 0.364 | 0.682 |
| 0.7 | 0.207 | 0.155 | 0.157 | 0.244 | 0.533 |
| **0.6** | **0.242** | **0.222** | **0.210** | **0.175** | **0.470** |
| 0.5 | 0.242 | 0.222 | 0.210 | 0.175 | 0.470 |
| 0.4 | 0.225 | 0.242 | 0.214 | 0.116 | 0.407 |
| 0.3 | 0.225 | 0.242 | 0.214 | 0.116 | 0.407 |

0.6 is the saved default: 0.4 edges it on F1 by 0.004, but 0.6 is better on
precision and both level-accuracy metrics — near-tied on F1, strictly
better elsewhere. Identical rows (0.6/0.5, 0.4/0.3) are because the
pointwise LLM emits scores in coarse steps, not a continuum.

## Known baseline result

At the saved 0.6 threshold (stored as `embedding-qwen3-llm-rerank` in
`evals/results.json`): mean precision 0.266, recall 0.243, F1 0.232; level
MAE 1.604, exact-level accuracy 0.181, within-1 0.436 on correctly-named
skills; ~6.17s per query.

Against keyword-bm25 (F1 0.128, exact-level 0.260, within-1 0.875): better
at finding the right skills (F1 +65%), worse at placing exact levels on the
ones found. The retrieval stage surfaces semantically-close level texts
across adjacent levels, and the pointwise reranker doesn't discriminate
level wording finely - a rerank prompt that sees the level definitions, or
the bge reranker, are candidate next experiments.

## Cost note

One query = 1 embedding call + 20 LLM rerank calls. The rerank stage
dominates cost/latency; all calls are logged in the AI Gateway dashboard.
