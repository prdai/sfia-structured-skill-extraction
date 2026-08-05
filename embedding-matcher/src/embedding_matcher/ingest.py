import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from . import COLLECTION, DATASET_PATH, MODEL_NAME, QDRANT_URL


def load_points(model: SentenceTransformer) -> list[PointStruct]:
    dataset = json.loads(Path(DATASET_PATH).read_text())
    texts: list[str] = []
    payloads: list[dict] = []

    for skill in dataset["skills"]:
        # One point for the overall skill description (no level), plus one
        # point per level description so a hit can carry a specific level.
        texts.append(f"{skill['name']}. {skill['description']}")
        payloads.append({"skill": skill["code"], "name": skill["name"], "level": None})
        for level, desc in skill["levels"].items():
            texts.append(f"{skill['name']}, level {level}. {desc}")
            payloads.append(
                {"skill": skill["code"], "name": skill["name"], "level": int(level)}
            )

    vectors = model.encode(texts, normalize_embeddings=True)
    return [
        PointStruct(id=i, vector=vec.tolist(), payload={**payload, "text": text})
        for i, (vec, payload, text) in enumerate(zip(vectors, payloads, texts))
    ]


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)
    client = QdrantClient(url=QDRANT_URL)
    dim = model.get_sentence_embedding_dimension()

    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    points = load_points(model)
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"ingested {len(points)} points into '{COLLECTION}'")


if __name__ == "__main__":
    main()
