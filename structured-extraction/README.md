# structured-extraction

Agentic pipeline that turns the crawler's raw per-page markdown
(`data/sfia-dataset.json`) into `{skill, level, text}` records for
`keyword-matcher`'s BM25 corpus (and any other matcher that needs
per-skill, per-level description text instead of full pages).

Each SFIA skill page has `### <Skill>: Level N` sections. Level 1 is
excluded — it is a generic "essence of the level" sentence repeated
verbatim across every skill, not skill-specific content. Two agents run
per page (not per level block — see below):

1. **Extractor** (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) — given
   the whole page's markdown, returns one JSON record per level (2-7,
   however many exist on that page), each with the generic essence
   preamble and page nav/footer noise stripped, plus a one-line
   `reasoning` on what was kept/discarded.
2. **Verifier** (`@cf/qwen/qwen2.5-coder-32b-instruct`) — checks each
   extracted record's text is a verbatim, complete copy of that level's
   source span in the page, not a paraphrase or a mismatch. Different
   model family from the extractor, so its errors aren't correlated
   with the extractor's. Runs once per extracted record.

Extraction is whole-page, not pre-split into per-level blocks by a
regex, to match the granularity of the cited ScrapeGraphAI-100k paper
below: "each extraction event [is] an atomic unit mapping complete
Markdown content to a single JSON response ... no intermediate document
segmentation step before LLM invocation." An earlier version of this
pipeline pre-split each page into level blocks with a regex and ran the
extractor per block; that worked but didn't match what the cited
methodology actually does, and used ~5x more extraction calls per page.

Both run on Cloudflare Workers AI. Output is one record per unique
`text` on a page, each tagged with the `(skill, level)` pairs that text
applies to (`mappings: [{"skill": ..., "level": ...}, ...]`) — grouping
by text rather than always emitting one row per level covers a page
producing duplicate text without duplicate rows.

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
- ["ScrapeGraphAI-100k: A Large-Scale Dataset for LLM-Based Web
  Information Extraction"](https://arxiv.org/html/2602.15189v1).
  Justifies the input/output contract: clean markdown in, explicit
  schema out, natural-language extraction instruction — the same shape
  used for the extractor's prompt and JSON output here.
- ["Agent-based large language model system for extracting structured
  data from breast cancer synoptic reports: a dual-validation
  study"](https://pmc.ncbi.nlm.nih.gov/articles/PMC12932940/).
  medRxiv preprint, 2025. Justifies the two-agent extract-then-verify
  structure — an independent second agent checking the first agent's
  output against the source, rather than trusting single-pass
  extraction. Cited for methodology (agentic extraction +
  dual-validation), not for its medical domain content.
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
  a specific 65-record sample after the fix) — records flagged
  `INVALID` in a full run are worth a quick manual check before being
  dropped from the corpus rather than auto-filtering.
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

Requires `CF_ACCOUNT_ID`, `CF_API_EMAIL`, `CF_API_KEY` in
`structured-extraction/.env` (gitignored, not committed).
