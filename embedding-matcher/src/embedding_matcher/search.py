import json
import sys

from .matcher import EmbeddingMatcher


def main() -> None:
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    if not text.strip():
        sys.exit("usage: search <free text describing a job/course/skill>")

    matches = EmbeddingMatcher().search(text)
    print(json.dumps([m.model_dump(exclude={"text"}) for m in matches], indent=2))


if __name__ == "__main__":
    main()
