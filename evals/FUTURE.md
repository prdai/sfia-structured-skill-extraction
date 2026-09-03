# Future work on evals/ extraction

Current state: this dataset was extracted by hand in one session with manual
fetch, read, and transcription per PDF. That's fine for a one-off 30-document
dataset, but it doesn't scale and has no independent check on accuracy beyond
re-reading each PDF once.

Not doing this now, but worth doing later:

- **Second-model cross-check.** Re-extract the same 30 PDFs with a different
  model (e.g. Gemini) and diff the two JSON outputs. Disagreements flag
  either a transcription error or a genuinely ambiguous source table, either
  way worth a human look.
- **Automated extraction pipeline**, instead of one-off manual prompting:
  script that downloads each role PDF, runs it through a fixed extraction
  prompt/schema, and validates the output against a JSON schema before
  writing it — so re-running against a future SFIA revision (e.g. SFIA 8)
  is a rerun, not a redo.
- **Skill code enrichment.** Cross-reference each skill name against the
  full SFIA skill list to attach the official skill code, since the
  per-role PDFs only print names.
- **Grid PDF as a cross-check, not a source.** Once column alignment can be
  verified (e.g. by extracting the grid's underlying table structure rather
  than flattened text), use it to sanity-check the per-role extraction
  rather than the other way around.
