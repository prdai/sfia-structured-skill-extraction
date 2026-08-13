from llm_matcher.matcher import LLMMatcher

from ..base import SkillMatcher


class LLMMatcherAdapter(SkillMatcher):
    def __init__(self, model: str | None = None):
        self._matcher = LLMMatcher(model) if model else LLMMatcher()

    def match(self, text: str) -> list[tuple[str, int]]:
        return [(m.skill, m.level) for m in self._matcher.match(text)]
