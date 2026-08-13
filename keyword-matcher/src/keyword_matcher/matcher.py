import json
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

for resource in ("punkt_tab", "stopwords"):
    try:
        nltk.data.find(f"tokenizers/{resource}" if resource == "punkt_tab" else f"corpora/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

STOPWORDS = set(stopwords.words("english"))


def tokenize(text: str) -> list[str]:
    tokens = word_tokenize(text.lower())
    return [t for t in tokens if t.isalnum() and t not in STOPWORDS]


class Match(BaseModel):
    skill: str
    level: int
    score: float
    text: str
    source_url: str


class KeywordMatcher:
    def __init__(self, records: list[dict]):
        self.records = records
        self.bm25 = BM25Okapi([tokenize(r["text"]) for r in records])

    @classmethod
    def from_corpus(cls, corpus_path: Path) -> "KeywordMatcher":
        return cls(json.loads(corpus_path.read_text()))

    def search(self, query: str, threshold: float = 0.7) -> list[Match]:
        scores = self.bm25.get_scores(tokenize(query))
        top_score = max(scores, default=0.0)
        if top_score <= 0:
            return []

        matches = []
        for record, score in zip(self.records, scores):
            if score / top_score < threshold:
                continue
            for mapping in record["mappings"]:
                matches.append(Match(
                    skill=mapping["skill"],
                    level=mapping["level"],
                    score=score / top_score,
                    text=record["text"],
                    source_url=record["source_url"],
                ))
        return sorted(matches, key=lambda m: m.score, reverse=True)
