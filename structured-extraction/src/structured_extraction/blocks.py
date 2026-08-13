import json
from pathlib import Path


def load_completed_pages(dataset_path: Path) -> list[dict]:
    dataset = json.loads(dataset_path.read_text())
    return [r for r in dataset["records"] if r.get("status") == "completed"]
