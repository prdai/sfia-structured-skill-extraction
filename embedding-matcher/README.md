# embedding-matcher

Embeds the SFIA dataset (skill descriptions plus each level description) into
a local Qdrant instance and answers free-text queries with the top-3 nearest
skills, each with its level when the hit came from a level description.

Model: `all-MiniLM-L6-v2` via sentence-transformers, cosine distance.

```
docker compose up -d      # start Qdrant
uv run ingest             # embed data/sfia-dataset.json into Qdrant
uv run search "builds and tests python services"
```
