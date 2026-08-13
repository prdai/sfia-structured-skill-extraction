import sys
from pathlib import Path

from .matcher import KeywordMatcher

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATH = REPO_ROOT / "data" / "sfia-skill-level-records.json"


def main():
    query = " ".join(sys.argv[1:])
    if not query:
        print("usage: match <query text>", file=sys.stderr)
        raise SystemExit(1)

    matcher = KeywordMatcher.from_corpus(CORPUS_PATH)
    matches = matcher.search(query)

    if not matches:
        print("no match")
        return

    for m in matches:
        print(f"{m.skill} (level {m.level}) score={m.score:.3f}")


if __name__ == "__main__":
    main()
