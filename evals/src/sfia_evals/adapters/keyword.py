from pathlib import Path

from keyword_matcher.matcher import KeywordMatcher

from ..base import SkillMatcher


class KeywordMatcherAdapter(SkillMatcher):
    def __init__(self, corpus_path: Path):
        self._matcher = KeywordMatcher.from_corpus(corpus_path)

    def match(self, text: str) -> list[tuple[str, int]]:
        return [(m.skill, m.level) for m in self._matcher.search(text)]
