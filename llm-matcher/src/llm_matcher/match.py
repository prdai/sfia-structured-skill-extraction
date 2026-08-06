import json
import sys
from pathlib import Path

from llama_cpp import Llama

# Small model for now; may swap for something bigger later.
MODEL_PATH = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
DATASET_PATH = "../data/sfia-dataset.json"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "level": {"type": ["integer", "null"], "minimum": 1, "maximum": 7},
                    "reason": {"type": "string"},
                },
                "required": ["skill", "level", "reason"],
            },
        }
    },
    "required": ["matches"],
}


def build_prompt(text: str, skills: list[dict]) -> str:
    # No retrieval: the model only sees skill codes and names, not the full
    # descriptions, and must map from its own understanding of the text.
    catalogue = "\n".join(f"- {s['code']}: {s['name']}" for s in skills)
    return (
        "You map free-text job, course, or skill descriptions to SFIA skills.\n"
        f"Valid SFIA skill codes:\n{catalogue}\n\n"
        "Given the following text, pick up to 3 matching skill codes, each "
        "with a responsibility level 1-7 (or null if the text gives no level "
        "signal) and a one-sentence reason.\n\n"
        f"Text:\n{text}"
    )


def main() -> None:
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    if not text.strip():
        sys.exit("usage: match <free text describing a job/course/skill>")

    skills = json.loads(Path(DATASET_PATH).read_text())["skills"]
    llm = Llama(model_path=MODEL_PATH, n_ctx=4096, verbose=False)

    out = llm.create_chat_completion(
        messages=[{"role": "user", "content": build_prompt(text, skills)}],
        response_format={
            "type": "json_object",
            "schema": RESPONSE_SCHEMA,
        },
        temperature=0.0,
    )
    print(out["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
