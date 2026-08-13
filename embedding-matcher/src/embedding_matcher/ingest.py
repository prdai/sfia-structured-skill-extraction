import json

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from . import COLLECTION, CORPUS_PATH, QDRANT_URL
from .workers_ai import embed

BATCH_SIZE = 50


def load_entries() -> list[dict]:
    records = json.loads(CORPUS_PATH.read_text())
    # One entry per (record, mapping): the embedded text concatenates the
    # skill name with the level description (label + description beats
    # description alone for taxonomy linking - see README citations).
    return [
        {
            "embed_text": f"{m['skill']}: {r['text']}",
            "skill": m["skill"],
            "level": m["level"],
            "text": r["text"],
            "source_url": r["source_url"],
        }
        for r in records
        for m in r["mappings"]
    ]


def main() -> None:
    entries = load_entries()

    vectors: list[list[float]] = []
    for start in range(0, len(entries), BATCH_SIZE):
        batch = entries[start:start + BATCH_SIZE]
        vectors.extend(embed([e["embed_text"] for e in batch]))
        print(f"embedded {min(start + BATCH_SIZE, len(entries))}/{len(entries)}")

    client = QdrantClient(url=QDRANT_URL)
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )
    points = [
        PointStruct(id=i, vector=vector, payload={k: v for k, v in entry.items() if k != "embed_text"})
        for i, (vector, entry) in enumerate(zip(vectors, entries))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"ingested {len(points)} points into '{COLLECTION}'")


if __name__ == "__main__":
    main()
