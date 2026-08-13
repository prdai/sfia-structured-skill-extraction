import json
import os

from crewai import Agent, Crew, LLM, Process, Task
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


class MultiAgentRAGMatcher:
    """Retriever -> Matcher -> Verifier crew.

    Splitting retrieval, matching and verification into separate agents
    follows the role-specialized pipeline pattern in ChatDev (Qian et al.,
    ACL 2024, arXiv:2307.07924) and MetaGPT (Hong et al., ICLR 2024,
    arXiv:2308.00352). The verifier agent checking the matcher's output
    against retrieved evidence follows multi-agent debate/critique
    (Du et al., ICML 2024, arXiv:2305.14325; ChatEval, Chan et al., ICLR
    2024, arXiv:2308.07201). See README for full citations.
    """

    def __init__(self, model: str = MODEL):
        self.llm = build_llm(model)
        self.canonical = canonical_skill_names()

    def match(self, text: str) -> list[Match]:
        retriever = Agent(
            role="SFIA retrieval specialist",
            goal="Gather every SFIA skill-level description that could plausibly relate to the given text.",
            backstory=(
                "You retrieve candidate SFIA skills for other agents to judge. "
                "You do not decide final matches yourself; you cast a wide net."
            ),
            tools=[SemanticSearchTool(), KeywordSearchTool()],
            llm=self.llm,
            verbose=False,
            max_iter=8,
        )
        matcher = Agent(
            role="SFIA skill mapping specialist",
            goal="Pick the SFIA skills and responsibility levels (1-7) the text actually calls for, from retrieved candidates.",
            backstory=(
                "You are an expert in the SFIA framework (Skills Framework "
                "for the Information Age, version 9). You only propose "
                "matches grounded in the retrieved candidate descriptions."
            ),
            llm=self.llm,
            verbose=False,
        )
        verifier = Agent(
            role="SFIA match verifier",
            goal="Check each proposed skill/level match against the retrieved evidence and drop any that are not clearly supported.",
            backstory=(
                "You are a skeptical reviewer. For each proposed match, you "
                "check whether the retrieved skill-level description "
                "actually supports it, and remove matches that don't."
            ),
            llm=self.llm,
            verbose=False,
        )

        retrieve_task = Task(
            description=(
                "Text:\n{text}\n\n"
                "Use both search tools (semantic and keyword) with queries "
                "for the distinct responsibilities in the text. Report all "
                "retrieved candidate skills, levels and descriptions."
            ),
            expected_output="The full list of retrieved candidate SFIA skill-level descriptions, unfiltered.",
            agent=retriever,
        )
        match_task = Task(
            description=(
                "From the retrieved candidates, propose the SFIA skills and "
                "responsibility levels (1-7) that the following text clearly "
                "calls for, preferring specific skills over generic ones:\n\n{text}"
            ),
            expected_output="A list of proposed SFIA skill/level matches, each grounded in a retrieved candidate.",
            agent=matcher,
            context=[retrieve_task],
        )
        verify_task = Task(
            description=(
                "Review the proposed matches against the retrieved candidate "
                "descriptions. Drop any match not clearly supported by its "
                "retrieved description. Output only the surviving matches, "
                "with skill names and levels copied exactly as retrieved."
            ),
            expected_output="The final, verified list of SFIA skill/level matches.",
            agent=verifier,
            context=[retrieve_task, match_task],
            output_pydantic=MatchList,
        )

        crew = Crew(
            agents=[retriever, matcher, verifier],
            tasks=[retrieve_task, match_task, verify_task],
            process=Process.sequential,
            verbose=False,
        )
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
