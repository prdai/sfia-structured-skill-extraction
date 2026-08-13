import json
import os

from crewai import Agent, Crew, Task, LLM
from dotenv import load_dotenv
from pydantic import BaseModel

from . import COMPAT_BASE_URL, CORPUS_PATH, ENV_PATH, MODEL
from .tools import KeywordSearchTool, SemanticSearchTool

load_dotenv(ENV_PATH)
load_dotenv()  # fallback: .env found from cwd, for non-editable installs


class Match(BaseModel):
    skill: str
    level: int


class MatchList(BaseModel):
    matches: list[Match]


def canonical_skill_names() -> dict[str, str]:
    records = json.loads(CORPUS_PATH.read_text())
    return {m["skill"].lower(): m["skill"] for r in records for m in r["mappings"]}


def build_llm(model: str = MODEL) -> LLM:
    base_url = COMPAT_BASE_URL.format(
        account_id=os.environ["CF_ACCOUNT_ID"],
        gateway_id=os.environ.get("CF_GATEWAY_ID", "structured-extraction"),
    )
    # The compat endpoint rejects Bearer auth for Global API Keys, so
    # credentials go through the legacy X-Auth headers instead.
    return LLM(
        model=f"openai/workers-ai/{model}",
        base_url=base_url,
        api_key="unused",
        extra_headers={
            "X-Auth-Email": os.environ["CF_API_EMAIL"],
            "X-Auth-Key": os.environ["CF_API_KEY"],
        },
        temperature=0.0,
    )


class AgenticRAGMatcher:
    def __init__(self, model: str = MODEL):
        self.llm = build_llm(model)
        self.tools = [SemanticSearchTool(), KeywordSearchTool()]
        self.canonical = canonical_skill_names()

    def match(self, text: str) -> list[Match]:
        agent = Agent(
            role="SFIA skill mapping specialist",
            goal=(
                "Map free-text descriptions of jobs, courses and roles to the "
                "SFIA version 9 skills and responsibility levels (1-7) they imply."
            ),
            backstory=(
                "You are an expert in the SFIA framework (Skills Framework for "
                "the Information Age). You ground every mapping in retrieved "
                "SFIA skill-level descriptions rather than memory alone."
            ),
            tools=self.tools,
            llm=self.llm,
            verbose=False,
            max_iter=8,
        )
        task = Task(
            description=(
                "Identify the SFIA skills and responsibility levels (1-7) this "
                "text calls for:\n\n{text}\n\n"
                "Use both search tools: semantic search for meaning-based "
                "matches and keyword search for jargon and exact terms. Query "
                "them with the distinct responsibilities you see in the text. "
                "Only include skills the retrieved descriptions clearly "
                "support, preferring specific skills over generic ones. Copy "
                "the skill names and levels exactly as the tools return them; "
                "levels are integers 1 to 7."
            ),
            expected_output=(
                "The final list of matched SFIA skills, each with its "
                "responsibility level."
            ),
            agent=agent,
            output_pydantic=MatchList,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = crew.kickoff(inputs={"text": text})
        matches = result.pydantic.matches if result.pydantic else []
        seen = set()
        unique = []
        for m in matches:
            skill = self.canonical.get(m.skill.lower())
            if skill is None or not 1 <= m.level <= 7:
                continue
            if (skill, m.level) not in seen:
                seen.add((skill, m.level))
                unique.append(Match(skill=skill, level=m.level))
        return unique
