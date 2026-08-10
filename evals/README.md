# evals/

Ground-truth eval data for the skill matchers in this repo: the 30 EU ICT
professional role profiles (CWA 16458-1:2018), each mapped to SFIA 7 skills
and levels. Matchers (keyword, embedding, LLM, LLM+RAG) can be scored against
this by feeding each role's summary/mission text as input and checking
whether the predicted skills/levels match `roles[].skills`.

## Files

- `eu-ict-sfia-role-profiles.json` — the 30 roles, each with title, summary
  statement, generic SFIA responsibility level, and its list of SFIA skills
  with level and core/optional flag.

## How this was extracted (current process)

Done by hand, through Claude Code, in one session:

1. Fetched the EU ICT SFIA skills profiles listing page
   (sfia-online.org, paginated via `?b_start:int=`) to get all 30 role names
   and their individual PDF URLs.
2. For each of the 30 roles, fetched the PDF's `@@download/file/` URL (the
   `/view` landing page does not expose PDF bytes to a fetch) and read the
   binary directly with a PDF-native reader.
3. Transcribed each role's "SFIA Generic Responsibility Levels" and "SFIA
   Professional Skills for the Role" tables verbatim into JSON.
4. Verified every one of the 30 PDFs individually (not in batches) after
   noticing that batched reads silently dropped documents' content in some
   cases — single-file reads were the only mode that reliably surfaced text
   every time.

The grid PDF (`grid-mapping-of-sfia-skills-to-eu-ict-profiles.pdf`, which
maps all 30 roles x all skills in one table) was deliberately **not** used
as the extraction source: its text layer does not preserve column alignment
across 30 columns, so a naive text extraction risks silently assigning the
wrong level to the wrong role. The per-role PDFs are the authoritative,
unambiguous source (one role per document, no alignment problem).

## Re-verification (2026-08-09)

Ran a second pass re-reading all 30 source PDFs against the JSON, role by
role, skill by skill. Result: **skill names, levels, and core/optional flags
for all 30 roles matched the source exactly** — no corrections needed there.

Two real issues found and fixed:

- Roles 11 (Information Security Manager), 12 (Information Security
  Specialist), and 13 (Digital Educator) are explicitly flagged in their
  source PDFs as "(NB this could be a multi-level role)" — the JSON was
  missing `multi_level_role: true` for these three. Added.
- `summary_statement` for roles 1–14 had been paraphrased rather than copied
  verbatim from the source "Summary statement" table cell. Replaced with the
  exact source wording for all 14. Roles 15–30 were transcribed directly
  from visible source text during the original extraction and are believed
  verbatim already, but were not independently re-diffed word-for-word in
  this pass — worth a follow-up check if summary_statement text is going to
  be used as matcher input text (see FUTURE.md).

## Known gaps in the current data

- No SFIA skill codes (e.g. the `BUAN`, `PROG` style codes) — the per-role
  PDFs print skill names and levels only, not codes. Codes would need to be
  cross-referenced against the full SFIA 7 skill list if needed downstream.
- `mission`, `deliverables` (accountable/responsible/contributor), and
  `main tasks` from each role's profile table were read but not carried into
  the JSON, to keep the file to what the matchers need (skill/level ground
  truth). They're in the source PDFs if ever needed.
- Several roles are marked `multi_level_role: true` in the source PDFs
  themselves (the source explicitly flags these as illustrative, not
  exhaustive, level assignments) — treat their exact levels as one
  reasonable profile among several valid ones for that role, not a single
  ground truth.
