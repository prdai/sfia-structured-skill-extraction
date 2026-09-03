.PHONY: help vector-db vector-db-down ingest search llm-match crawler-dev

help:
	@echo "Targets:"
	@echo "  vector-db       start local Qdrant (docker compose, embedding-matcher/)"
	@echo "  vector-db-down  stop Qdrant"
	@echo "  ingest          embed data/sfia-skill-level-records.json into Qdrant"
	@echo "  search TEXT=..  threshold-filtered embedding search"
	@echo "  llm-match TEXT=..  pure LLM matching, structured output"
	@echo "  crawler-dev     run the crawler Worker locally (wrangler dev)"

vector-db:
	cd embedding-matcher && docker compose up -d

vector-db-down:
	cd embedding-matcher && docker compose down

ingest:
	cd embedding-matcher && uv run ingest

search:
	cd embedding-matcher && uv run search "$(TEXT)"

llm-match:
	cd llm-matcher && uv run match "$(TEXT)"

crawler-dev:
	cd crawler && npm run dev
