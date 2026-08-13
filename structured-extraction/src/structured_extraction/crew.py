import json

from crewai import Agent, Crew, Process, Task

from .workers_ai_llm import WorkersAILLM

EXTRACTOR_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
VERIFIER_MODEL = "@cf/qwen/qwen2.5-coder-32b-instruct"


def build_extract_crew() -> Crew:
    extractor_llm = WorkersAILLM(model=EXTRACTOR_MODEL, temperature=0.1, max_tokens=2048)

    extractor = Agent(
        role="SFIA skill-page extractor",
        goal="Turn a raw SFIA skill page's markdown into clean per-level skill-specific description records",
        backstory=(
            "SFIA skill pages have '### <Skill>: Level N' sections for levels 2-7 (not "
            "all skills have all levels). Each section has a generic 'Essence of the "
            "level' sentence (identical across every skill, discard it), then a '---' "
            "separator, then skill-specific behaviour text (keep this, verbatim, no "
            "summarizing). Ignore level 1, nav links, and page footer/related-skills "
            "content entirely."
        ),
        llm=extractor_llm,
        verbose=False,
    )

    extract_task = Task(
        description=(
            "Constraints: only extract sections whose header literally matches "
            "'### <Skill>: Level N' for N in 2-7 and that actually appear in the text "
            "below - do not output a record for any level whose header is not present, "
            "even if you expect it to exist; a level's section starts at its header "
            "and ends at the next '### ' header or the page footer (Keywords/Links/"
            "related-skills content), whichever comes first; within a section, ignore "
            "the 'Essence of the level' sentence before the '---' separator entirely, "
            "only the text after '---' is skill-specific.\n\n"
            "Extract:\n"
            "  skill: the skill name as it appears on the page,\n"
            "  records: one entry per matching level header actually found (could be "
            "as few as one, never invent a level that has no header), each with:\n"
            "    level: the level number as an integer,\n"
            "    text: the skill-specific description for that level, verbatim, "
            "no markdown links,\n"
            "    reasoning: one short sentence on what was kept and discarded\n\n"
            "from the following text:\n\n{page_markdown}\n\n"
            "Return ONLY the JSON object, no text outside it."
        ),
        expected_output='{"skill": "...", "records": [{"level": 2, "text": "...", "reasoning": "..."}, ...]}',
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
            "Constraints: only compare against the '### {skill_name}: Level {level}' "
            "section of page_markdown; within that section, only the text after the "
            "'---' separator is in scope (the sentence before it is generic "
            "boilerplate, ignore it).\n\n"
            "page_markdown:\n{page_markdown}\n\nextracted_text (claimed to be the "
            "Level {level} skill-specific text):\n{extracted_text}\n\n"
            "Reply with exactly one line: either 'VALID' or 'INVALID: <reason>'."
        ),
        expected_output="'VALID' or 'INVALID: <reason>'",
        agent=verifier,
    )

    return Crew(agents=[verifier], tasks=[verify_task], process=Process.sequential)


def _parse_extraction(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return json.loads(raw)


def _run_extraction(page: dict) -> dict:
    extract_crew = build_extract_crew()
    extract_crew.kickoff(inputs={"page_markdown": page["markdown"]})
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


def extract_page(page: dict) -> list[dict]:
    parsed = _run_extraction(page)
    skill_name = parsed["skill"]
    entries = [e for e in parsed["records"] if e["text"].strip()]

    by_text: dict[str, dict] = {}
    for entry in entries:
        record = by_text.setdefault(entry["text"], {
            "text": entry["text"],
            "mappings": [],
            "reasoning": entry.get("reasoning", ""),
            "source_url": page["url"],
            "verification": [],
        })
        record["mappings"].append({"skill": skill_name, "level": entry["level"]})
        record["verification"].append(_run_verification(page, skill_name, entry))

    return list(by_text.values())
