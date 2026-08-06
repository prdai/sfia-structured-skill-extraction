# llm-matcher

Pure LLM matching, no retrieval. A local llama.cpp model gets the input text
plus the list of valid SFIA skill codes and returns structured JSON: up to 3
matches, each with skill code, level (1-7 or null) and reason. Structured
output is enforced with a JSON schema grammar.

Model: Qwen2.5 0.5B Instruct GGUF (small on purpose for now; may swap later).

```
make model    # download the GGUF into models/
uv run match "leads solution architecture for complex systems"
```
