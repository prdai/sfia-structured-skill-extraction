from embedding_matcher.matcher import EmbeddingMatcher

from ..base import SkillMatcher


class EmbeddingMatcherAdapter(SkillMatcher):
    def __init__(self):
        self._matcher = EmbeddingMatcher()

    def match(self, text: str) -> list[tuple[str, int]]:
        seen = set()
        pairs = []
        for m in self._matcher.search(text):
            if (m.skill, m.level) not in seen:
                seen.add((m.skill, m.level))
                pairs.append((m.skill, m.level))
        return pairs
