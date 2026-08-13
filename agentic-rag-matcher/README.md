# agentic-rag-matcher

Agentic RAG: a single CrewAI agent maps free text to SFIA skills and levels by
querying two retrieval tools over the same skill-level corpus, then emitting a
structured match list. The agent decides its own retrieval queries and can
search repeatedly before answering.

Tools:

- `semantic_skill_search` — the embedding-matcher pipeline (Workers AI
  qwen3-embedding into Qdrant, LLM rerank).
- `keyword_skill_search` — the keyword-matcher BM25 pipeline.

The LLM is a Workers AI model behind the AI Gateway OpenAI-compatible endpoint
(`.../compat`), which supports the OpenAI `tools` parameter for function
calling. The Global API Key is rejected as a Bearer token there, so the client
sends the legacy `X-Auth-Email`/`X-Auth-Key` headers.

```
uv run match "leads solution architecture for complex enterprise systems"
```

Requires the embedding-matcher Qdrant instance running and ingested
(`docker compose up -d` + `uv run ingest` in `../embedding-matcher/`), and the
same `.env` credentials as the other matchers (`CF_ACCOUNT_ID`, `CF_API_EMAIL`,
`CF_API_KEY`, `CF_GATEWAY_ID`).

## Design justification

- **RAG** — grounding the LLM's answer in retrieved corpus text: Lewis et al.,
  "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
  (NeurIPS 2020, arXiv:2005.11401); the frozen-LLM, retrieval-in-prompt
  variant used here is Ram et al., "In-Context Retrieval-Augmented Language
  Models" (TACL 2023, arXiv:2302.00083); taxonomy of RAG designs in Gao et
  al., "Retrieval-Augmented Generation for Large Language Models: A Survey"
  (arXiv:2312.10997).
- **Retrieval-shortlist-then-LLM for skill taxonomies**: Clavie and Soulie
  (arXiv:2307.03539) retrieve ESCO candidate skills and have an LLM pick from
  the shortlist; Achananuparp et al. (ICWSM 2026, arXiv:2503.12989) do the
  same for occupation taxonomies. No SFIA-specific prior work found.
- **Agentic RAG** — the agent controls when and what to retrieve: Singh et
  al., "Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG"
  (arXiv:2501.09136). The reason+act tool loop is ReAct (Yao et al., ICLR
  2023, arXiv:2210.03629); adaptive retrieval decisions are Self-RAG (Asai et
  al., ICLR 2024, arXiv:2310.11511), FLARE (Jiang et al., EMNLP 2023,
  arXiv:2305.06983) and IRCoT (Trivedi et al., ACL 2023, arXiv:2212.10509).
- **Two retrievers (dense + sparse) as separate tools**: dense and BM25
  retrieval are complementary — Karpukhin et al., "Dense Passage Retrieval"
  (EMNLP 2020, arXiv:2004.04906), Ma et al. (arXiv:2104.05740, hybrid beats
  either alone), Luan et al. (TACL 2021, arXiv:2005.00181), and BEIR (Thakur
  et al., NeurIPS 2021, arXiv:2104.08663, BM25 as robust zero-shot baseline).
  Hybrid retrieval inside RAG: Blended RAG (Sawarkar et al., arXiv:2404.07220)
  and the Gao et al. survey. Letting a model route across multiple retrievers:
  RouterRetriever (Lee et al., AAAI 2025, arXiv:2409.02685), LTRR (Kim and
  Diaz, arXiv:2506.13743) and MoR (Kalra et al., arXiv:2506.15862). No prior
  paper studies exactly one LLM agent holding dense and BM25 search as two
  tool calls; the routing literature is the nearest analogue. BM25 itself is
  Robertson and Zaragoza (Foundations and Trends in IR, 2009,
  DOI 10.1561/1500000019).
- **Single-agent architecture and prompt**: the role/goal/backstory persona
  prompt CrewAI uses is backed by Kong et al., "Better Zero-Shot Reasoning
  with Role-Play Prompting" (NAACL 2024, arXiv:2308.07702); general agent
  framing in Wang et al., "A Survey on Large Language Model based Autonomous
  Agents" (Frontiers of Computer Science 2024, arXiv:2308.11432).
- **CrewAI** has no first-party paper; cite the repository (Moura, 2023,
  github.com/crewAIInc/crewAI). Framework comparisons that benchmark CrewAI:
  arXiv:2508.10146 (highest F1 among frameworks tested, 55-140% slower) and
  the agentic RAG survey above.

## Model sweep

Candidate pool: every Workers AI text model flagged `function_calling: true`
in the model catalog that survives a full CrewAI tool-calling turn against
the AI Gateway compat endpoint. This is a platform + framework constraint,
not a claim about model quality in general: cross-model variance in
tool-calling reliability is well established (Berkeley Function-Calling
Leaderboard, Patil et al., ICML 2025, PMLR v267; ToolLLM/ToolBench, Qin et
al., arXiv:2307.16789), but no benchmark covers function-calling on
Cloudflare's own serving stack, which is a custom inference engine ("Infire"),
not a vanilla vLLM wrapper (Cloudflare engineering blog). That gap is the
justification for sweeping empirically here rather than trusting a general
leaderboard to transfer.

30-role eval harness, all runs logged in `evals/experiments.json`:

| model | P | R | F1 | lvl exact | lvl within-1 | lvl MAE | s/record | failed roles |
|---|---|---|---|---|---|---|---|---|
| @cf/nvidia/nemotron-3-120b-a12b | 0.462 | 0.179 | **0.230** | 0.341 | 0.898 | 0.76 | 9.1 | 0 |
| @cf/zai-org/glm-4.7-flash | 0.355 | 0.186 | 0.223 | 0.432 | 0.727 | 0.91 | 173.6 | 0 |
| @cf/moonshotai/kimi-k2.7-code | 0.467 | 0.146 | 0.211 | 0.425 | 0.925 | 0.68 | 21.7 | 0 |
| @cf/moonshotai/kimi-k2.6 | 0.494 | 0.145 | 0.211 | 0.611 | 0.889 | 0.50 | 47.2 | 0 |
| @cf/mistralai/mistral-small-3.1-24b-instruct | 0.321 | 0.152 | 0.186 | 0.342 | 0.895 | 0.76 | 17.1 | 1 |
| @cf/google/gemma-4-26b-a4b-it | 0.289 | 0.086 | 0.128 | 0.423 | 0.846 | 0.73 | 69.0 | 6 |
| @cf/zai-org/glm-5.2 | 0.194 | 0.088 | 0.112 | 0.633 | 0.867 | 0.57 | 26.8 | 20 |
| @cf/meta/llama-4-scout-17b-16e-instruct | 0.000 | 0.000 | 0.000 | n/a | n/a | n/a | 4.5 | 0 |

`@cf/nvidia/nemotron-3-120b-a12b` wins on mean F1 and is also the fastest of
the working models (9.1s/record, one clean call chain with no retries) - it
is the saved default. `kimi-k2.6` has the best level-exact accuracy (0.611)
despite lower F1, so it is the better pick if level precision matters more
than skill-name F1. `glm-4.7-flash` is close on F1 but ~19x slower than
nemotron (173.6s/record), likely burning many extra turns/retries per role.
glm-5.2's high failure count is a rate-limit artifact of the 16-way parallel
sweep, not a model or format failure - most of its 30 roles hit Workers AI's
per-minute inference rate limit rather than returning a bad result, so this
row understates it and is not a clean comparison; re-run at lower
concurrency before drawing conclusions about it specifically. llama-4-scout
scored zero cleanly (no failures, no matches) because it never emits a tool
call in this crew despite being flagged function-calling-capable - excluded
in practice, kept in the table for completeness.
