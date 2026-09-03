# Future work on embedding-matcher

Current state: retrieve-and-rerank with a pointwise relevance prompt,
threshold tuned by sweep (see README). Skill identification beats the BM25
baseline (F1 0.232 vs 0.128); exact-level placement is behind it (0.181 vs
0.260).

Not doing this now, but worth doing later:

- **Level-aware reranking.** The current rerank prompt asks only "how
  relevant is this candidate to the query" - pure topical relevance.
  Retrieval typically surfaces several adjacent levels of the same skill
  (all topically equal), so they all pass, and exact-level accuracy suffers.
  Two candidate designs:
  - Pointwise with level context: include SFIA's generic level definitions
    in the prompt and ask whether the query's autonomy/responsibility
    signals match the candidate's level.
  - Listwise within skill: show all retrieved levels of one skill together
    and have the LLM pick which level(s) the query supports - the listwise
    LLM reranking used by TalentCLEF 2026's third-place system, so it stays
    citable.
  Expected: exact-level accuracy up without losing skill identification. If
  query text carries no seniority signal, no improvement - also a finding.
- **bge-reranker-base comparison.** `@cf/baai/bge-reranker-base` is on the
  account: one dedicated cross-encoder call per candidate instead of an LLM
  call - much cheaper/faster. Weaker citation (no TalentCLEF winner used
  it), but worth logging in evals/experiments.json as a cost/quality point.
- **Retrieval-k sweep.** k=20 was adopted from SkillRouter's compact
  pipeline, not tuned on our data. Same offline-derivation trick as the
  threshold sweep applies (score once at large k, derive smaller k).
