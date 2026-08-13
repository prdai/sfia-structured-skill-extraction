import json
import sys

from .matcher import LLMMatcher


def main() -> None:
    text = " ".join(sys.argv[1:]) or sys.stdin.read()
    if not text.strip():
        sys.exit("usage: match <free text describing a job/course/skill>")

    matches = LLMMatcher().match(text)
    print(json.dumps([m.model_dump() for m in matches], indent=2))


if __name__ == "__main__":
    main()
