from agentic_rag_matcher.matcher import AgenticRAGMatcher

from ..base import SkillMatcher


class AgenticRAGMatcherAdapter(SkillMatcher):
    def __init__(self, model: str | None = None):
        self._matcher = AgenticRAGMatcher(model) if model else AgenticRAGMatcher()

    def match(self, text: str) -> list[tuple[str, int]]:
        return [(m.skill, m.level) for m in self._matcher.match(text)]
