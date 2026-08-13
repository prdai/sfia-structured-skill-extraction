from abc import ABC, abstractmethod


class SkillMatcher(ABC):
    @abstractmethod
    def match(self, text: str) -> list[tuple[str, int]]:
        """Return (skill, level) pairs predicted for the given input text."""
