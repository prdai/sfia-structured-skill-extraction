from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel
from qdrant_client import QdrantClient

from . import COLLECTION, QDRANT_URL, RERANK_THRESHOLD, RETRIEVAL_K
from .workers_ai import embed, rerank_score


class Match(BaseModel):
    skill: str
    level: int
    retrieval_score: float
    rerank_score: float
    text: str
    source_url: str


class EmbeddingMatcher:
    def __init__(self, qdrant_url: str = QDRANT_URL):
        self.client = QdrantClient(url=qdrant_url)

    def search(self, query: str, k: int = RETRIEVAL_K, threshold: float = RERANK_THRESHOLD) -> list[Match]:
        vector = embed([query])[0]
        hits = self.client.query_points(collection_name=COLLECTION, query=vector, limit=k).points

        with ThreadPoolExecutor(max_workers=8) as pool:
            scores = list(pool.map(lambda h: rerank_score(query, h.payload["text"]), hits))

        matches = [
            Match(
                skill=hit.payload["skill"],
                level=hit.payload["level"],
                retrieval_score=hit.score,
                rerank_score=score,
                text=hit.payload["text"],
                source_url=hit.payload["source_url"],
            )
            for hit, score in zip(hits, scores)
            if score >= threshold
        ]
        return sorted(matches, key=lambda m: m.rerank_score, reverse=True)
