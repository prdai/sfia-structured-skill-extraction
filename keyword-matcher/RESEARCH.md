# keyword-matcher — research basis

Reference papers found and the exact algorithm we're adopting, before writing
any code. This satisfies the "needs a research paper reference before
implementation" note in `keyword-matcher/README.md`.

## Skill detection stage — Calanca et al. 2019

**Calanca, F., Sayfullina, L., Minkus, L., Wagner, C., & Malmi, E. (2019).
"Responsible team players wanted: an analysis of soft skill requirements in
job advertisements." EPJ Data Science, 8(1), 13.**

- arXiv (free full text): https://arxiv.org/abs/1810.07781
- Published version: https://link.springer.com/article/10.1140/epjds/s13688-019-0190-z

Method, from their Section 2.2.4 "Soft Skill Detection" (this is the part we
adopt — their skill *dictionary construction* via crowdsourcing/word2vec
clustering is not needed since our dictionary is the fixed SFIA skill list):

1. **Preprocess** both the input text and the skill dictionary: lowercase,
   strip stopwords (NLTK English stopword list).
2. **Strip "competence terms"** ("able", "skills", etc.) from most skill
   phrases before matching, to catch more matches (so "capable of handling
   multiple tasks" still matches "abilities in handling multiple tasks").
   Exception: keep competence terms on skills where dropping them causes
   false positives — e.g. keep "skills" in "communication skills", because
   bare "communication" alone is too ambiguous a match.
3. **Matching rule:** for a multi-token skill phrase, search the text
   allowing **up to 2 extra (non-skill) words before each token**, in
   addition to removable stopwords. A bounded gap window, not full fuzzy
   matching.
4. **Explicitly tested and rejected:** ignoring word order, and lemmatizing
   tokens — both were found to **significantly decrease precision**. Do not
   do either.

Skills were detected in 78% of their job ads corpus (245,000 UK job ads);
45.5% of ads mentioned at least 3 soft skills.

## What this paper does NOT cover: levels

Confirmed across this entire literature area (see also the Khaouja et al.
2021 survey, `IEEE Access`, DOI 10.1109/ACCESS.2021.3106120 — "A Survey on
Skill Identification from Online Job Ads", 108 papers reviewed): every
keyword/skill-count method detects skill *presence*, never skill *level* or
*proficiency*. This is a genuine gap in the literature, not something we
missed by not looking hard enough.

## Level stage — separate step, precedented

**Deng, et al. (2020). "Competence-Level Prediction and Resume & Job
Description Matching Using Context-Aware Transformer Models."**
arXiv: https://arxiv.org/abs/2011.02998

Treats competence-level classification as its own separate task/model,
distinct from skill extraction/matching — two explicitly independent tasks
(T1: level from resume text alone; T2: match given a job description).
Cited here as precedent that splitting "detect the skill" and "classify its
level" into two separate pipeline stages is standard practice, not an ad hoc
shortcut — same shape as NER followed by a separate attribute/relation
classification step.

## Adopted architecture for this repo

```
input text
   |
   v
[Stage 1: skill detection]   <- Calanca et al. 2019 algorithm, above
   | dictionary = SFIA skill names from evals/eu-ict-sfia-role-profiles.json
   v
matched skills (no level yet)
   |
   v
[Stage 2: level classification]   <- separate step, precedented by Deng et al. 2020
   | keyword/cue dictionary per SFIA level 1-7, derived from the
   | "Generic Responsibility Levels" text in the source PDFs
   | (not itself from a paper — our own addition on top of a cited base)
   v
(skill, level) pairs
```

## Data we have to build this

- `evals/eu-ict-sfia-role-profiles.json` — 30 EU ICT roles, each with SFIA
  skill names + levels (1-7) + core/optional flag. This is ground truth for
  evaluation, and its skill-name list is the seed for the Stage 1 dictionary.
- **Missing, needed before Stage 1 works well:** a synonym/alias list per
  skill. SFIA skill names alone (e.g. "Programming/software development")
  are narrow — real-world text says "coding", "dev", "software engineering".
  Calanca et al. built this via crowdsourcing; we don't have that budget, so
  this needs to be authored by hand or generated and reviewed.
- **Missing, needed for Stage 2:** a level-cue keyword dictionary (level 1-7
  cues like "sets strategy", "leads", "under supervision"). Derivable from
  the "SFIA Generic Responsibility Levels" tables already present in every
  role's source PDF (see `evals/README.md` for source PDF details) — these
  describe autonomy/influence/complexity/knowledge/business-skills language
  per level, generically, not per-role.

## Not yet decided / open questions

- Exact stopword list and tokenizer (NLTK vs. something else).
- Whether to build the skill-alias list by hand, semi-automatically (e.g.
  synonym expansion via an embedding model), or some other way.
- Whether Stage 2's level-cue dictionary is authored manually from the
  Generic Responsibility Levels text, or bootstrapped some other way.
- Scoring/output format when multiple skills or levels match ambiguously.
