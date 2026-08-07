# llm-rag-matcher

LLM + RAG pipeline: retrieve candidate SFIA skills and level descriptions from
the vector store, then have the LLM pick and justify the final skill/level
mapping with structured output.

Current focus of work. Skeleton only for now — will reuse the Qdrant instance
and dataset ingestion from `../embedding-matcher/` and the local llama.cpp
setup from `../llm-matcher/`.
