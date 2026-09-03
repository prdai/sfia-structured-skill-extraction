# evals/

Ground-truth eval data for the skill matchers in this repo: the 30 EU ICT
professional role profiles (CWA 16458-1:2018), each mapped to SFIA 7 skills
and levels. Matchers (keyword, embedding, LLM, LLM+RAG) can be scored against
this by feeding each role's summary/mission text as input and checking
whether the predicted skills/levels match `roles[].skills`.

## Standard matcher interface

`sfia_evals.base.SkillMatcher` is the abstract class every matcher
implements to be evaluated by the shared harness:

```python
class SkillMatcher(ABC):
    @abstractmethod
    def match(self, text: str) -> list[tuple[str, int]]:
        """Return (skill, level) pairs predicted for the given input text."""
```

One query per role (the role's `summary_statement`), expecting the matcher
to surface all the skills it thinks apply — mirrors real usage (a job/course
description in, multiple skills out), not one query per individual skill.

Each matcher directory implements this by adapter, e.g.
`sfia_evals.adapters.keyword.KeywordMatcherAdapter` wraps
`keyword_matcher.matcher.KeywordMatcher`.

## Metrics (`sfia_evals.harness`)

Two different things are being measured, scored separately per the relevant
literature rather than folded into one number:

**Skill identification** — precision/recall/F1 on skill *names* only
(ignoring level), the standard Exact-Match-and-F1 pairing from:

> Rajpurkar, P., Zhang, J., Lopyrev, K., Liang, P. (2016). "SQuAD:
> 100,000+ Questions for Machine Comprehension of Text." EMNLP 2016.
> https://doi.org/10.18653/v1/D16-1264

**Level accuracy** — computed only on skills the matcher got right by name
(scoring level correctness on a skill that wasn't even identified doesn't
mean anything). SFIA levels are ordinal (1-7, not independent categories),
so a level-2-vs-3 miss is not as wrong as a level-2-vs-7 miss — mean
absolute error and accuracy-within-k capture that where plain accuracy
wouldn't:

> Baccianella, S., Esuli, A., Sebastiani, F. (2009). "Evaluation Measures
> for Ordinal Regression." ISDA 2009, 283-287.
> https://doi.org/10.1109/ISDA.2009.230

`level_accuracy_exact` is k=0 (level must match exactly);
`level_accuracy_within_1` is k=1 ("off by at most one level"), matching
that paper's accuracy-within-k concept — report both, since exact-match
alone is a strict standard and within-1 alone hides how often a matcher
gets the level exactly right.

**Speed** — `mean_seconds_per_record`, wall-clock time per `match()` call
averaged across the 30 roles. Not from a paper, just a practical number for
comparing matchers that may differ by orders of magnitude (BM25 vs. an LLM
call per query).

## Running

```
uv venv && uv pip install -e .
eval-keyword
```

## Files

- `eu-ict-sfia-role-profiles.json` — the 30 roles, each with title, summary
  statement, generic SFIA responsibility level, and its list of SFIA skills
  with level and core/optional flag.
- `src/sfia_evals/base.py` — the `SkillMatcher` interface.
- `src/sfia_evals/harness.py` — `run_eval(matcher, roles_path)`, scoring
  logic above.
- `src/sfia_evals/adapters/` — one adapter module per matcher directory.

## Known baseline result (keyword-matcher, BM25)

Mean precision 0.141, recall 0.133, F1 0.128 across all 30 roles; mean level
MAE 0.938, exact-level accuracy 0.260, accuracy-within-1 0.875, on the
skills it did identify correctly. Mean time per record: 0.8ms. Low
recall/precision is expected for a lexical baseline against
short, abstract `summary_statement` text (see `keyword-matcher/README.md`
for the reasoning) — the intended comparison point against the
embedding/LLM matchers, not a bug in this harness.

## How this was extracted (current process)

Done by hand in one session:

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
