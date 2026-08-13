from multi_agent_rag_matcher.matcher import MultiAgentRAGMatcher

from ..base import SkillMatcher


class MultiAgentRAGMatcherAdapter(SkillMatcher):
    def __init__(self, model: str | None = None):
        self._matcher = MultiAgentRAGMatcher(model) if model else MultiAgentRAGMatcher()

    def match(self, text: str) -> list[tuple[str, int]]:
        return [(m.skill, m.level) for m in self._matcher.match(text)]
