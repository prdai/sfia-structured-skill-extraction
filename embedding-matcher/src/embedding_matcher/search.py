import json
import sys

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from . import COLLECTION, MODEL_NAME, QDRANT_URL

TOP_K = 3


def main() -> None:
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    if not text.strip():
        sys.exit("usage: search <free text describing a job/course/skill>")

    model = SentenceTransformer(MODEL_NAME)
    client = QdrantClient(url=QDRANT_URL)
    vector = model.encode(text, normalize_embeddings=True).tolist()

    hits = client.query_points(
        collection_name=COLLECTION, query=vector, limit=TOP_K
    ).points

    results = [
        {
            "skill": hit.payload["skill"],
            "name": hit.payload["name"],
            "level": hit.payload["level"],
            "score": round(hit.score, 4),
        }
        for hit in hits
    ]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
