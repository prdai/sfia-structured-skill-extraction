import json
import re
from functools import cache
from pathlib import Path

from crewai import Agent, Crew, Process, Task

from .workers_ai_llm import WorkersAILLM

EXTRACTOR_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
VERIFIER_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"

CHART_PATH = Path(__file__).resolve().parents[3] / "data" / "sfia-9-summary-chart.json"


CONTEXT_MODEL = EXTRACTOR_MODEL


def build_context_notes_crew() -> Crew:
    llm = WorkersAILLM(model=CONTEXT_MODEL, temperature=0.0, max_tokens=512)
    scout = Agent(
        role="SFIA framework context scout",
        goal="Judge whether a non-skill page of sfia-online.org holds general framework context useful to a skill-page extraction agent, and note it if so",
        backstory="",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "The page below is from sfia-online.org (SFIA 9) and is NOT an "
            "individual skill page. Decide whether it contains general "
            "framework context that would help an agent extracting per-level "
            "skill descriptions from the skill pages - for example: what the "
            "responsibility levels 1-7 mean, the attributes behind them "
            "(autonomy, influence, complexity), why skills are not defined at "
            "all seven levels, how skill pages are structured, or framework "
            "terminology. Page navigation, news, licensing and marketing text "
            "are not useful context.\n\n"
            "Extract:\n"
            "  relevant: true or false,\n"
            "  notes: when relevant, 3-6 short factual sentences stating the "
            "useful context in your own words; empty string when not\n\n"
            "from the following page markdown:\n\n{page_markdown}\n\n"
            "Return ONLY the JSON object, no text outside it."
        ),
        expected_output='{"relevant": true, "notes": "..."}',
        agent=scout,
    )
    return Crew(agents=[scout], tasks=[task], process=Process.sequential)


SYNTHESIZER_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"
BRIEFING_MAX_TOKENS = 400


def build_context_synthesizer_crew() -> Crew:
    # Long-context model: all notes go in as one call, no chunked reduce.
    # The output token cap is the hard size enforcement on the briefing;
    # the word limit in the prompt is the soft one.
    llm = WorkersAILLM(model=SYNTHESIZER_MODEL, temperature=0.0, max_tokens=BRIEFING_MAX_TOKENS)
    synthesizer = Agent(
        role="SFIA framework briefing synthesizer",
        goal="Synthesize per-page context notes into one condensed framework briefing for extraction agents",
        backstory="",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "The notes below were gathered from every non-skill page of "
            "sfia-online.org (SFIA 9). Synthesize them into a single "
            "briefing of at most 250 words for an agent that extracts "
            "per-level skill descriptions from SFIA skill pages. Keep only "
            "what helps that task: the meaning of responsibility levels 1-7 "
            "and their attributes, why skills are defined at only some "
            "levels, how skill pages are structured, and framework "
            "terminology. Merge duplicates, drop trivia, state facts "
            "plainly, as condensed as possible.\n\n"
            "Notes:\n\n{notes}\n\n"
            "Return ONLY the briefing text, no preamble."
        ),
        expected_output="A plain-text briefing of at most 250 words.",
        agent=synthesizer,
    )
    return Crew(agents=[synthesizer], tasks=[task], process=Process.sequential)


SCOUT_CHUNK_CHARS = 20000


def collect_context_notes(page: dict) -> dict | None:
    """Run the context scout on one non-skill page; None when irrelevant.

    Pages longer than the model's payload budget are scouted in chunks and
    the chunk notes merged - the scout synthesizes each chunk instead of the
    page being cut off at an arbitrary length."""
    markdown = page["markdown"]
    chunks = [
        markdown[i:i + SCOUT_CHUNK_CHARS]
        for i in range(0, len(markdown), SCOUT_CHUNK_CHARS)
    ]
    notes = []
    for chunk in chunks:
        crew = build_context_notes_crew()
        crew.kickoff(inputs={"page_markdown": chunk})
        try:
            parsed = _parse_extraction(crew.tasks[0].output.raw)
        except (json.JSONDecodeError, KeyError):
            continue
        if parsed.get("relevant") and str(parsed.get("notes", "")).strip():
            notes.append(str(parsed["notes"]).strip())
    if not notes:
        return None
    return {"url": page["url"], "notes": " ".join(notes)}


def synthesize_context_briefing(notes: list[dict]) -> str:
    """One synthesizer call over all notes; no cutting, no recursion."""
    crew = build_context_synthesizer_crew()
    joined = "\n".join(f"- ({n['url']}) {n['notes']}" for n in notes)
    crew.kickoff(inputs={"notes": joined})
    return crew.tasks[0].output.raw.strip()


def build_extract_crew() -> Crew:
    extractor_llm = WorkersAILLM(model=EXTRACTOR_MODEL, temperature=0.1, max_tokens=2048)

    extractor = Agent(
        role="SFIA skill-page extractor",
        goal="Turn a raw SFIA skill page into clean per-level skill-specific description records",
        backstory=(
            "SFIA skill pages describe one skill at the responsibility levels that "
            "skill is defined at - different skills are defined at different levels, "
            "and the page itself is the only authority on which. A level's "
            "skill-specific section is headed '### <Skill>: Level N' in the markdown, "
            "where <Skill> is this page's skill name. Each such section starts with a "
            "generic 'Essence of the level' sentence (identical across every skill, "
            "discard it), then a '---' separator, then the skill-specific behaviour "
            "text (keep this, verbatim, no summarizing). Sections headed just "
            "'### Level N' without the skill name are generic framework blurbs, not "
            "descriptions of this skill. Ignore nav links and page "
            "footer/related-skills content."
        ),
        llm=extractor_llm,
        verbose=False,
    )

    extract_task = Task(
        description=(
            "Extraction guidelines - apply each rule to the page content given "
            "below:\n"
            "1. Scope: a level exists exactly when the page contains a "
            "'### <Skill>: Level N' header naming this page's skill. Output one "
            "record per such header, however many there are (could be as few as "
            "one); the set of levels varies per skill and the headers present are "
            "the only source of truth. Headers reading just '### Level N' without "
            "the skill name are generic framework text: skip them.\n"
            "2. Section span: a level's section starts at its skill-named header "
            "and ends at the next '### ' header or the page footer "
            "(Keywords/Links/related-skills content), whichever comes first.\n"
            "3. Within a section: the sentence before the '---' separator is the "
            "generic 'Essence of the level' (identical across every skill) - skip "
            "it; the text after '---' is the skill-specific description - copy it "
            "word for word.\n"
            "4. Sources: the page is given twice, markdown then raw HTML (the HTML "
            "part may be empty). Take all extracted text from the markdown; use "
            "the HTML's structure (section containers, anchors such as "
            "'skill_level_section_N') only to resolve where sections start and "
            "end.\n\n"
            "Framework briefing (background distilled from the rest of "
            "sfia-online.org; use it to understand the framework, never as a "
            "source of extracted text - all text comes from the page markdown "
            "below):\n{framework_context}\n\n"
            "Extract:\n"
            "  skill: the skill name exactly as the page's top-level '# ' title "
            "states it,\n"
            "  records: one entry per skill-named level header found (rule 1), "
            "each with:\n"
            "    code: the short uppercase skill code that follows the skill name "
            "in the page's top-level '# ' title,\n"
            "    level: the level number as an integer,\n"
            "    text: the complete skill-specific description after '---' (rule "
            "3), copied verbatim, with markdown link syntax removed,\n"
            "    reasoning: one short sentence on what was kept and discarded\n\n"
            "Page markdown:\n\n{page_markdown}\n\n"
            "Page HTML (same page, structural reference only):\n\n{page_html}\n\n"
            "Reminder of the rules above: one record per skill-named "
            "'### <Skill>: Level N' header only; skip generic "
            "'### Level N' sections and 'Essence of the level' sentences; copy the "
            "text after '---' verbatim and complete. "
            "Return ONLY the JSON object, no text outside it."
        ),
        expected_output='{"skill": "...", "records": [{"code": "...", "level": 2, "text": "...", "reasoning": "..."}, ...]}',
        agent=extractor,
    )

    return Crew(agents=[extractor], tasks=[extract_task], process=Process.sequential)


def build_verify_crew() -> Crew:
    verifier_llm = WorkersAILLM(model=VERIFIER_MODEL, temperature=0.0, max_tokens=150)

    verifier = Agent(
        role="Fidelity checker",
        goal="Say whether extracted_text is a verbatim copy of skill-specific content in page_markdown for the given level",
        backstory="",
        llm=verifier_llm,
        verbose=False,
    )

    verify_task = Task(
        description=(
            "Verification criteria - apply each to the content given below:\n"
            "1. Locate the section headed exactly '### {skill_name}: Level {level}' "
            "in page_markdown. If no section carries that skill-named header, the "
            "verdict is 'INVALID: no such section' - a bare '### Level {level}' "
            "header without the skill name does not count.\n"
            "2. The reference text is what follows the '---' separator inside that "
            "section; the sentence before '---' is generic boilerplate and out of "
            "scope.\n"
            "3. extracted_text must be a verbatim and complete copy of the "
            "reference text (markdown link syntax may be removed): a paraphrase, a "
            "missing sentence, added content, or text belonging to a different "
            "level all fail.\n\n"
            "page_markdown:\n{page_markdown}\n\nextracted_text (claimed to be the "
            "Level {level} skill-specific text):\n{extracted_text}\n\n"
            "Apply the three criteria in order and reply with exactly one line: "
            "'VALID' if all pass, otherwise 'INVALID: <the failed criterion and "
            "why>'."
        ),
        expected_output="'VALID' or 'INVALID: <reason>'",
        agent=verifier,
    )

    return Crew(agents=[verifier], tasks=[verify_task], process=Process.sequential)


@cache
def chart_levels() -> dict[str, frozenset[int]]:
    """Skill code -> defined levels, from the transcribed SFIA 9 summary chart."""
    chart = json.loads(CHART_PATH.read_text())
    return {s["code"]: frozenset(s["levels"]) for s in chart["skills"]}


def _parse_extraction(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return json.loads(raw)


def _trim_html(html: str) -> str:
    """Deterministically shrink page HTML to fit the extractor's context.

    Full pages (nav, scripts, inline SVG) exceed the model's context window;
    the structural cues the prompt uses (section containers,
    skill_level_section_N anchors) all live inside <main>. Keep <main> when
    present, then drop script/style/svg/comment blocks and collapse
    whitespace.
    """
    main = re.search(r"<main\b.*?</main>", html, re.DOTALL)
    if main:
        html = main.group(0)
    html = re.sub(
        r"<script\b.*?</script>|<style\b.*?</style>|<svg\b.*?</svg>|<!--.*?-->",
        "", html, flags=re.DOTALL,
    )
    return re.sub(r"\s+", " ", html)


def _run_extraction(page: dict, framework_context: str) -> dict:
    extract_crew = build_extract_crew()
    html = page.get("html", "")
    extract_crew.kickoff(inputs={
        "page_markdown": page["markdown"],
        "page_html": _trim_html(html) if html else "(no HTML was extracted for this page)",
        "framework_context": framework_context or "(no briefing available)",
    })
    try:
        return _parse_extraction(extract_crew.tasks[0].output.raw)
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"unparseable extraction for {page['url']}: {e}") from e


def _run_verification(page: dict, skill_name: str, entry: dict) -> str:
    verify_crew = build_verify_crew()
    verify_crew.kickoff(inputs={
        "page_markdown": page["markdown"],
        "skill_name": skill_name,
        "level": entry["level"],
        "extracted_text": entry["text"],
    })
    return verify_crew.tasks[0].output.raw.strip()


def extract_page(page: dict, framework_context: str = "") -> tuple[list[dict], dict]:
    """Extract one page's records: extract, range-check against the chart,
    verify, and count what each check rejected.

    Returns (records, metrics). A record is one (code, level, text)."""
    parsed = _run_extraction(page, framework_context)
    skill_name = parsed["skill"]
    chart = chart_levels()

    records, range_rejected, verifier_rejected = [], [], []
    for entry in parsed["records"]:
        if not entry["text"].strip():
            continue
        code = entry.get("code", "")
        if entry["level"] not in chart.get(code, frozenset()):
            range_rejected.append({"code": code, "level": entry["level"]})
            continue
        verdict = _run_verification(page, skill_name, entry)
        if verdict != "VALID":
            verifier_rejected.append({"code": code, "level": entry["level"], "verdict": verdict})
            continue
        records.append({
            "code": code,
            "level": entry["level"],
            "text": entry["text"],
            "reasoning": entry.get("reasoning", ""),
            "source_url": page["url"],
        })

    metrics = {
        "url": page["url"],
        "skill": skill_name,
        "html_available": bool(page.get("html")),
        "extracted": sum(1 for e in parsed["records"] if e["text"].strip()),
        "range_rejected": range_rejected,
        "verifier_rejected": verifier_rejected,
        "kept": len(records),
    }
    return records, metrics
