# llm-matcher

Pure LLM matching, no retrieval. A Workers AI model (via the AI Gateway) gets
only the free-text description; it must map to SFIA skills from its own
parametric knowledge. The output is forced to valid SFIA entries by a JSON
schema whose `skill` field is an enum of the 147 skill names from
`data/sfia-skill-level-records.json` and whose `level` is an integer 1-7.

```
uv run match "leads solution architecture for complex enterprise systems"
```

Credentials come from `.env` (`CF_ACCOUNT_ID`, `CF_API_EMAIL`, `CF_API_KEY`,
`CF_GATEWAY_ID`), same as the other matchers.

## Design justification

- **Zero-shot prompting against a closed label set** follows Clavie and Soulie,
  "Large Language Models as Batteries-Included Zero-Shot ESCO Skills Matchers"
  (RecSys in HR 2023, arXiv:2307.03539): a role-instructed zero-shot prompt
  with a hard constraint that the model may only answer with labels from the
  fixed taxonomy. They enforced the constraint in prose and via a structured
  (function-style) output trick; we enforce it mechanically with constrained
  decoding.
- **Enum-constrained JSON output**: Geng et al., "Grammar-Constrained Decoding
  for Structured NLP Tasks without Finetuning" (EMNLP 2023, arXiv:2305.13971)
  show constraining decoding to a task's valid output space improves
  off-the-shelf LLM accuracy on closed-set prediction. The mechanism (JSON
  schema as a decoding grammar) is Willard and Louf, "Efficient Guided
  Generation for Large Language Models" (arXiv:2307.09702). Tam et al., "Let
  Me Speak Freely?" (EMNLP 2024 Industry, arXiv:2408.02442) find format
  constraints hurt free-form reasoning but help or do not hurt classification,
  which is our case.
- **Model selection** is empirical, mirroring the multi-model comparison in
  Clavie and Soulie: the candidate pool is every non-deprecated Workers AI
  text model with working JSON-schema structured output support (Cloudflare
  Workers AI JSON Mode docs), each evaluated on the 30-role harness, winner by
  mean F1. All runs are logged in `evals/experiments.json`.

## Model sweep

30-role eval harness, all runs logged in `evals/experiments.json`:

| model | P | R | F1 | lvl exact | lvl within-1 | s/record |
|---|---|---|---|---|---|---|
| @cf/meta/llama-3.1-8b-instruct-fast | 0.305 | 0.139 | **0.173** | 0.130 | 0.509 | 2.25 |
| @cf/qwen/qwen3-30b-a3b-fp8 | 0.308 | 0.095 | 0.141 | 0.467 | 0.733 | 11.34 |
| @cf/meta/llama-4-scout-17b-16e-instruct | 0.190 | 0.130 | 0.137 | 0.658 | 0.947 | 3.63 |

Sweep s/record is measured under 8-way parallel calls, so it is inflated by
contention; the serial eval of the winning model measures 0.27 s/record.
llama-4-scout is notably better at level placement (0.658 exact, 0.947
within-1) but weakest at picking the right skills.

Selection optimizes mean F1 on skill names, consistent with the config sweeps
in the other matchers. F1 weights precision and recall equally, which is a
choice: a use case that penalizes wrong suggestions would prefer qwen3-30b
(best precision), and one where level placement matters as much as skill
identity would prefer llama-4-scout. Level metrics are conditional on
correctly-named skills, so optimizing them directly would reward models that
match very few skills.

`@cf/meta/llama-3.1-8b-instruct-fast` wins on mean F1. The configured default
is `@cf/google/gemma-4-26b-a4b-it`. Earlier sweep rounds (also in
experiments.json) ran without `max_tokens`; Workers AI's default output cap
truncated long responses mid-JSON, so those rows carry high failed-role
counts. The final round sets `max_tokens` 8192 plus `maxItems` 20 on the
matches array: zero failures across all three models.

Excluded: `@cf/meta/llama-3.3-70b-instruct-fp8-fast` fails constrained
generation deterministically on some inputs (Workers AI error 5024, "JSON
Model couldn't be met") with the 147-name enum schema;
`@hf/nousresearch/hermes-2-pro-mistral-7b` was deprecated 2026-05-30.
