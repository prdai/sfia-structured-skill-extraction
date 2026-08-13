# keyword-matcher

Keyword/lexical matching baseline: score input text against SFIA skill and
level descriptions using term overlap (TF-IDF/BM25 or similar) and return the
best skills.

Approach: BM25, per:

- Robertson, S. and Zaragoza, H. (2009). "The Probabilistic Relevance
  Framework: BM25 and Beyond." Foundations and Trends in Information
  Retrieval, 3(4), 333-389. https://doi.org/10.1561/1500000019
- Person-job matching precedent: "A Person-job Matching Method Based on
  BM25 and Pre-trained Language Model." Proceedings of the 2023 6th
  International Conference on Machine Learning and Natural Language
  Processing. https://doi.org/10.1145/3639479.3639494

Implementation uses [`rank-bm25`](https://github.com/dorianbrown/rank_bm25)'s
`BM25Okapi` (Okapi BM25, the specific variant Robertson & Zaragoza cover)
over the `data/sfia-skill-level-records.json` corpus produced by
`structured-extraction/`.

## Scoring

Raw BM25 scores are unbounded and corpus-dependent, not a 0-1 confidence.
Per query, scores are normalized against that query's own top score
(`score / top_score`), and only candidates at or above a relative threshold
are returned as matches. If nothing scores above 0 (no term overlap at all),
returns no match rather than forcing a low-confidence guess.

Threshold is 0.7, chosen by sweeping {0.9, 0.8, 0.7, 0.5, 0.3} against all 30
eval roles and picking the highest mean F1 (see table below) — 0.9 was an
initial guess, not tuned. F1 peaks at 0.7 and falls on both sides: tighter
thresholds miss real matches (recall collapses at 0.9), looser ones flood
results with noise (precision collapses at 0.3).

| threshold | precision | recall | F1 |
|---|---|---|---|
| 0.9 | 0.198 | 0.072 | 0.100 |
| 0.8 | 0.132 | 0.092 | 0.105 |
| **0.7** | **0.138** | **0.133** | **0.127** |
| 0.5 | 0.081 | 0.259 | 0.118 |
| 0.3 | 0.055 | 0.431 | 0.093 |

## Known baseline result

Evaluated against all 30 roles in `evals/eu-ict-sfia-role-profiles.json` via
the shared harness (`evals/`, `eval-keyword`): mean precision 0.138, recall
0.133, F1 0.127; mean level MAE 0.938, exact-level accuracy 0.260,
accuracy-within-1 0.875, on the skills correctly identified by name. Mean
time per record: 0.8ms. Low precision/recall is expected for a
lexical baseline against short, abstract `summary_statement` text that
doesn't necessarily share vocabulary with the detailed SFIA skill
descriptions — this gap is the intended comparison point against the
embedding/LLM matchers in the other directories, not a bug to fix here. See
`evals/README.md` for the metrics' definitions and citations.

## Running

```
uv venv && uv pip install -e .
match "some job or course description text"
```
