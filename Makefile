.PHONY: help vector-db vector-db-down ingest search llm-model llm-match scraper-dev

help:
	@echo "Targets:"
	@echo "  vector-db       start local Qdrant (docker compose, embedding-matcher/)"
	@echo "  vector-db-down  stop Qdrant"
	@echo "  ingest          embed data/sfia-dataset.json into Qdrant"
	@echo "  search TEXT=..  top-3 embedding search"
	@echo "  llm-model       download the local GGUF model (llm-matcher/)"
	@echo "  llm-match TEXT=..  pure LLM matching, structured output"
	@echo "  scraper-dev     run the scraper Worker locally (wrangler dev)"

vector-db:
	cd embedding-matcher && docker compose up -d

vector-db-down:
	cd embedding-matcher && docker compose down

ingest:
	cd embedding-matcher && uv run ingest

search:
	cd embedding-matcher && uv run search "$(TEXT)"

llm-model:
	$(MAKE) -C llm-matcher model

llm-match:
	cd llm-matcher && uv run match "$(TEXT)"

scraper-dev:
	cd scraper && npm run dev
