# multi-agent-rag-matcher

Multi-agent agentic RAG: a CrewAI crew of three role-specialized agents maps
free text to SFIA skills and levels, in place of one agent doing everything.

- **Retriever** — owns the same two RAG tools as `agentic-rag-matcher`
  (semantic search, BM25 search) and gathers candidate skill-level
  descriptions.
- **Matcher** — proposes skill/level matches from the retrieved candidates.
- **Verifier** — checks each proposed match against the retrieved evidence
  and drops any that aren't clearly supported.

Tasks run sequentially with each agent's output passed as context to the
next (`Process.sequential`). Same Workers AI compat-endpoint backend, same
credential setup, as `agentic-rag-matcher`.

```
uv run multi-agent-match "leads solution architecture for complex enterprise systems"
```

Requires the same running/ingested Qdrant instance and `.env` credentials as
the other matchers.

## Design justification

RAG and agentic RAG citations are shared with `agentic-rag-matcher`; see that
README. This directory adds citations specific to splitting one agent into
several role-specialized agents:

- **Role-specialized agent pipelines**: MetaGPT (Hong et al., ICLR 2024
  Oral, arXiv:2308.00352) encodes structured roles and hand-offs between
  agents rather than one agent doing everything; ChatDev (Qian et al.,
  ACL 2024, arXiv:2307.07924) uses a pipeline of role-specialized agents for
  a complex task, the closest structural analogue to
  retriever -> matcher -> verifier. AutoGen (Wu et al., COLM 2024,
  arXiv:2308.08155) is the general framework citation for conversable,
  role-differentiated agents sharing tools.
- **A separate verifier/critic agent improves accuracy**: Du et al.,
  "Improving Factuality and Reasoning in Language Models through Multiagent
  Debate" (ICML 2024, arXiv:2305.14325) and ChatEval (Chan et al., ICLR 2024,
  arXiv:2308.07201) both use a second agent to challenge or score a first
  agent's output and catch errors a single pass misses — direct justification
  for the verifier agent here.
- **Multi-agent RAG as a design category**: the agentic RAG survey (Singh et
  al., arXiv:2501.09136, already cited in `agentic-rag-matcher`) taxonomizes
  single-agent vs. multi-agent vs. hierarchical vs. corrective RAG
  architectures; this crew is its multi-agent/corrective pattern applied to
  a closed skill taxonomy.
- No prior work was found applying a multi-agent retriever/matcher/verifier
  split to a closed-label competency taxonomy (SFIA, ESCO, O*NET); the
  closest adjacent work is single-agent or non-agentic multi-stage taxonomy
  classification (Achananuparp et al., ICWSM 2026, arXiv:2503.12989). That
  gap is the contribution of this matcher, not a citable prior design.

## Model sweep

Model pool is narrower than the single-agent matcher's: a model has to
survive not just one function-calling turn but a full multi-turn, multi-agent
conversation over the compat endpoint. `mistral-small-3.1-24b` and
`gemma-4-26b-a4b-it` (both fine for `agentic-rag-matcher`'s single agent)
break mid-crew here with malformed tool-call output from Workers AI.

30-role eval harness, one shared model across all three agents, all runs
logged in `evals/experiments.json`:

| model | P | R | F1 | lvl exact | lvl within-1 | lvl MAE | s/record | failed roles |
|---|---|---|---|---|---|---|---|---|
| @cf/moonshotai/kimi-k2.7-code | 0.506 | 0.133 | **0.198** | 0.528 | 0.917 | 0.56 | 372.6 | 0 |
| @cf/zai-org/glm-4.7-flash | 0.251 | 0.251 | 0.190 | 0.257 | 0.746 | 1.00 | 296.4 | 1 |
| @cf/nvidia/nemotron-3-120b-a12b | 0.357 | 0.132 | 0.161 | 0.438 | 0.812 | 0.84 | 235.8 | 0 |
| @cf/moonshotai/kimi-k2.6 | 0.319 | 0.175 | 0.160 | 0.476 | 0.794 | 0.78 | 319.8 | 0 |
| @cf/zai-org/glm-5.2 | 0.067 | 0.025 | 0.036 | 0.167 | 1.000 | 0.83 | 73.1 | 23 |

`@cf/moonshotai/kimi-k2.7-code` wins on mean F1. The configured default is
`@cf/moonshotai/kimi-k2.6`.
Every working model is 235-373s/record here, an order of magnitude slower
than the same models' single-agent numbers in `agentic-rag-matcher` - three
sequential agents each making their own LLM/tool-call round trips, rather
than one agent's tool loop, is the direct cost of the multi-agent split.
Comparing to the single-agent sweep: nemotron-3-120b-a12b's F1 drops from
0.230 (single-agent, its winning config) to 0.161 here, and every model's
F1 is lower in the crew than that same model's single-agent number where
both were tested. The three-role split does not clearly outperform one
well-grounded agent on this task at this scale; it is markedly slower for
a lower or comparable F1, though `kimi-k2.7-code`'s level-exact accuracy
(0.528) and within-1 (0.917) are competitive with the best single-agent
numbers. glm-5.2's high failure count is again a rate-limit artifact of the
16-way parallel sweep, not a model or format failure; not a clean
comparison for that model specifically.

Currently one model serves all three agents. TODO: once the single-model
sweep has a winner, sweep per-role model combinations where feasible (e.g.
a cheaper/faster model for the retriever, which only calls tools, paired
with the strongest verified model for matcher and verifier) - the crew
doesn't require all three agents to share one model, this just hasn't been
swept yet.
