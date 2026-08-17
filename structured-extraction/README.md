# structured-extraction

Agentic pipeline that turns the crawler's raw pages
(`data/sfia-dataset.json`, markdown + HTML per page) into
`{skill, level, text}` records for `keyword-matcher`'s BM25 corpus (and
any other matcher that needs per-skill, per-level description text
instead of full pages).

Each SFIA skill page has `### <Skill>: Level N` sections for the levels
that skill is defined at. Not every skill spans levels 1-7 (most don't:
16 skills define level 1, only some reach 7), and the pipeline does not
hard-code any level range — the extractor is asked for whatever
skill-named level sections the page actually contains, and a
deterministic range guard checks the result afterwards. An earlier
version excluded level 1 by prompt on the assumption it was always
generic boilerplate; that assumption was wrong for 16 skills and cost
their level-1 records, and the same run let 7 generic level-7 blurbs
through — the guard + generalized prompt replace it.

Two agents run per page (not per level block — see below), then the
guard:

1. **Extractor** (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) — given
   the page's markdown and raw HTML, returns one JSON record per
   skill-named level section actually present, each with the generic
   essence preamble and page nav/footer noise stripped, plus a one-line
   `reasoning` on what was kept/discarded. The HTML is supplied for
   structural cues (section containers, anchors); the markdown is the
   text source.
2. **Range guard** (no LLM) — the extractor generates a skill code per
   record, and each `(code, level)` is checked against
   `data/sfia-9-summary-chart.json`, a hand transcription of the
   official SFIA 9 summary chart (cross-checked against every page's
   "Levels of responsibility" table, 147/147 agree). The chart is
   external to both the crawled page text and any LLM output. Records
   whose code is unknown or whose level the chart does not define for
   that code are dropped and counted, so the corpus can never contain a
   combination SFIA does not define, and the model's invalid-combo rate
   is measured rather than hidden — reported per page and in total in
   `output/extraction-metrics.json`.
3. **Verifier** (`@cf/qwen/qwen2.5-coder-32b-instruct`) — checks each
   surviving record's text is a verbatim, complete copy of that level's
   source span in the page, not a paraphrase or a mismatch. Different
   model family from the extractor, so its errors aren't correlated
   with the extractor's. Runs once per record; records flagged
   `INVALID` are dropped from the corpus and counted in the metrics
   file (an earlier run kept one flagged record in the corpus).

Extraction is whole-page, not pre-split into per-level blocks by a
regex, to match the granularity of the cited ScrapeGraphAI-100k paper
below: "each extraction event [is] an atomic unit mapping complete
Markdown content to a single JSON response ... no intermediate document
segmentation step before LLM invocation." An earlier version of this
pipeline pre-split each page into level blocks with a regex and ran the
extractor per block; that worked but didn't match what the cited
methodology actually does, and used ~5x more extraction calls per page.

Both run on Cloudflare Workers AI. Output is one record per unique
`text` on a page, each tagged with the `(skill code, level)` pairs that
text applies to (`mappings: [{"code": ..., "level": ...}, ...]`; skill
names live in `data/sfia-9-summary-chart.json`, keyed by code) —
grouping by text rather than always emitting one row per level covers a
page producing duplicate text without duplicate rows.

## Why this design (citations)

- Arora, S., Yang, B., Eyuboglu, S., et al. (2023). ["Language Models
  Enable Simple Systems for Generating Structured Views of
  Heterogeneous Data Lakes"](https://arxiv.org/abs/2304.09433)
  (Evaporate). VLDB 2023.
  Justifies using an LLM to turn semi-structured web documents into
  structured records without hand-written per-page parsers. This
  pipeline doesn't go as far as Evaporate's function-synthesis approach
  (147 pages is small enough for direct per-block extraction), but the
  underlying justification — LLM extraction over bespoke per-source
  code — is the same.
- Brach, W., Zuppichini, F., Vinciguerra, M., Padoan, L. (2026).
  ["ScrapeGraphAI-100k: Dataset for Schema-Constrained LLM
  Generation"](https://arxiv.org/abs/2602.15189).
  Justifies the input/output contract: clean markdown in, explicit
  schema out, natural-language extraction instruction — the same shape
  used for the extractor's prompt and JSON output here. (Earlier
  versions of this README cited the paper under its v1 title, "A
  Large-Scale Dataset for LLM-Based Web Information Extraction".)
- Hart, S.N., Bergamaschi, T.S. (2026). ["Agent-based large language
  model system for extracting structured data from breast cancer
  synoptic reports: a dual-validation
  study"](https://academic.oup.com/jamiaopen/article/9/1/ooag016/8496817).
  JAMIA Open 9(1), ooag016. Justifies the two-agent extract-then-verify
  structure — an independent second agent checking the first agent's
  output against the source, rather than trusting single-pass
  extraction. Cited for methodology (agentic extraction +
  dual-validation), not for its medical domain content.
- Ji, Z., Lee, N., Frieske, R., et al. (2023). ["Survey of Hallucination
  in Natural Language Generation"](https://doi.org/10.1145/3571730).
  ACM Computing Surveys 55(12). Justifies the range guard's design
  stance: measure source-faithfulness — the rate of generated content
  unsupported by the source — and report it as an evaluation metric,
  rather than hiding failures inside constrained decoding. The guard
  drops and counts `(skill, level)` combinations the source page does
  not define instead of making them unrepresentable.
- Moundas, M., White, J., Schmidt, D.C. (2024). ["Prompt Patterns for
  Structured Data Extraction from Unstructured
  Text"](https://www.cs.wm.edu/~dcschmidt/PDF/Prompt_Patterns_for_Structured_Data_Extraction_from_Unstructured_Text___Final.pdf).
  Proceedings of PLoP 2024.
  Justifies the actual wording/structure of the extractor and verifier
  task descriptions: the *Specify Constraints* pattern (declare scope
  boundaries first, separately from the extraction instruction) chained
  into the *Semantic Extractor* pattern (`Extract: field: semantic
  description ... from the following text: [text]`, each field given a
  natural-language description rather than a rigid rule). Both agents'
  task descriptions in `crew.py` follow this shape explicitly, not just
  in spirit.
- Sainz, O., Garcia-Ferrero, I., Agerri, R., et al. (2024). ["GoLLIE:
  Annotation Guidelines improve Zero-Shot
  Information-Extraction"](https://arxiv.org/abs/2310.03668). ICLR
  2024. Justifies writing the extractor prompt as numbered,
  definition-style annotation guidelines (what a level section is,
  where it spans, what to skip) rather than bare field names — its
  ablations show detailed guidelines are key to zero-shot IE quality.
- Shrimal, A., Jain, A., Chowdhury, S., Yenigalla, P. (2025).
  ["PARSE: LLM Driven Schema Optimization for Reliable Entity
  Extraction"](https://arxiv.org/abs/2510.08623). EMNLP 2025 Industry
  Track. Justifies LLM-oriented field descriptions in the output
  schema (ambiguous schema descriptions measurably cause extraction
  hallucinations on web pages) and a reflection/verification pass
  after extraction — this pipeline's extractor + verifier split.
- Liu, N.F., Lin, K., Hewitt, J., et al. (2024). ["Lost in the Middle:
  How Language Models Use Long
  Contexts"](https://arxiv.org/abs/2307.03172). TACL 12, 157-173.
  Justifies the extractor prompt's layout: rules stated before the
  page content and recapped after it, so no critical instruction sits
  mid-context behind a long markdown+HTML document (model recall is
  U-shaped over position — worst in the middle).
- Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). ["Judging
  LLM-as-a-Judge with MT-Bench and Chatbot
  Arena"](https://arxiv.org/abs/2306.05685). NeurIPS 2023 Datasets and
  Benchmarks. Justifies the verifier's design as an LLM judge:
  evaluation criteria enumerated in the prompt, a single structured
  verdict token, temperature 0, and a different model family from the
  extractor (its self-enhancement-bias caution — a model grading its
  own output scores it too favourably).
- Jang, J., Ye, S., Seo, M. (2023). ["Can Large Language Models Truly
  Understand Prompts? A Case Study with Negated
  Prompts"](https://arxiv.org/abs/2209.12711). PMLR 203 (Transfer
  Learning for NLP @ NeurIPS 2022). Justifies phrasing constraints
  positively (the skill-named header "is the only source of truth" for
  a level's existence) rather than leaning on bare negations — LMs
  handle negated instructions unreliably, and the effect worsens with
  scale. Negations in these prompts reinforce a positive rule, never
  stand alone.

## Verifier reliability (R&D note)

An earlier version wrapped both agents in CrewAI's `Agent`/`Task`
abstractions with full role/goal/backstory framing and used CrewAI's
automatic `context=[...]` mechanism to pass the extractor's output to
the verifier. That produced a ~5% false-`INVALID` rate — confirmed by
hand that at least one flagged record was actually a correct
extraction.

To isolate the cause, the same verifier prompt was sent as a single
direct Workers AI call (bypassing CrewAI) to four candidate models
(`qwen2.5-coder-32b-instruct`, `llama-3.1-8b-instruct-fp8`,
`llama-3.3-70b-instruct-fp8-fast`, `mistral-small-3.1-24b-instruct`) at
temperature 0, checked against a programmatic ground truth (word-overlap
between extracted text and its source span, not the verifier's own
judgment). All four scored 19/19 correct — the models were never the
problem.

The fix was to trim the verifier `Agent`'s role/goal/backstory to
near-nothing and pass `raw_block`/`extracted_text` as explicit task
inputs instead of relying on CrewAI's automatic context injection. That
change alone took the false-`INVALID` rate from ~5% to 0/65 across two
follow-up test batches (19 + 46 records, none overlapping the tuning
set). Conclusion: CrewAI's default agent-role scaffolding was diluting
instruction-following on this task, not any component model.

## Known limitations

- `verification` can still be wrong in principle (only tested against
  a specific 65-record sample after the fix). Flagged records are now
  auto-dropped and counted in `output/extraction-metrics.json` rather
  than shipped; the per-record verdicts in the metrics file are the
  place to audit for false `INVALID`s.
- The HTML input only exists in datasets produced by a crawl with
  `formats: ["markdown", "html"]`; on older markdown-only datasets the
  extractor runs with an empty HTML section (works, verified on two
  pages, but without the structural cues).
- Cross-skill relationships (a page's "Related SFIA skills" links) are
  dropped entirely, not modeled. That section doesn't state which level
  of a related skill applies, and inventing one would be fabricating
  ground truth rather than extracting it.
- This produces the BM25 *corpus* only. Labeled query -> `(skill,
  level)` ground truth for evaluating matcher accuracy is a separate
  artifact (`evals/eu-ict-sfia-role-profiles.json`).

## Running

```
uv venv && uv pip install -e .
python -m structured_extraction.run        # all skill pages
python -m structured_extraction.run 10     # first 10 pages, for testing
```

Outputs `output/skill-level-records.json` (the corpus) and
`output/extraction-metrics.json` (per-page and total counts of
extracted / range-rejected / verifier-rejected / kept records).

Requires `CF_ACCOUNT_ID`, `CF_API_EMAIL`, `CF_API_KEY` in
`structured-extraction/.env` (gitignored, not committed).
