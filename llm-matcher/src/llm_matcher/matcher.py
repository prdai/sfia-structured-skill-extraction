import json

from pydantic import BaseModel

from . import MODEL, REPO_ROOT
from .workers_ai import run

RECORDS_PATH = REPO_ROOT / "data" / "sfia-skill-level-records.json"

PROMPT = (
    "You are an expert in the SFIA framework (Skills Framework for the "
    "Information Age, version 9).\n\n"
    "Given the following free-text description of a job, course, or role, "
    "identify the SFIA skills it maps to, each with the responsibility "
    "level (1-7) the text implies. Only include skills the text clearly "
    "calls for, preferring specific skills over generic ones.\n\n"
    "Text:\n{text}"
)


class Match(BaseModel):
    skill: str
    level: int


def load_skill_names() -> list[str]:
    records = json.loads(RECORDS_PATH.read_text())
    return sorted({m["skill"] for r in records for m in r["mappings"]})


def response_schema(skill_names: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string", "enum": skill_names},
                        "level": {"type": "integer", "minimum": 1, "maximum": 7},
                    },
                    "required": ["skill", "level"],
                },
            }
        },
        "required": ["matches"],
    }


class LLMMatcher:
    def __init__(self, model: str = MODEL):
        self.model = model
        self.schema = response_schema(load_skill_names())

    def match(self, text: str) -> list[Match]:
        result = run(self.model, {
            "messages": [{"role": "user", "content": PROMPT.format(text=text)}],
            "temperature": 0.0,
            "max_tokens": 8192,
            "response_format": {"type": "json_schema", "json_schema": self.schema},
        })
        response = result["response"]
        if isinstance(response, str):
            response = json.loads(response)
        matches = [Match(**m) for m in response.get("matches", [])]
        seen = set()
        unique = []
        for m in matches:
            if (m.skill, m.level) not in seen:
                seen.add((m.skill, m.level))
                unique.append(m)
        return unique
