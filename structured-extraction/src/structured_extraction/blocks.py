import json
import re
from pathlib import Path

SKILL_PAGE_URL = re.compile(r"https://sfia-online\.org/en/sfia-9/skills/[a-z0-9-]+$")


def load_completed_pages(dataset_path: Path) -> list[dict]:
    dataset = json.loads(dataset_path.read_text())
    return [r for r in dataset["records"] if r.get("status") == "completed"]


def load_skill_pages(dataset_path: Path) -> list[dict]:
    """Completed pages that are individual skill pages.

    The crawl also completes index/about/framework pages; extracting from
    those wastes model calls and would count non-skill extractions into the
    range-rejection metrics, so the extraction run is scoped to skill URLs.
    """
    return [
        r for r in load_completed_pages(dataset_path)
        if SKILL_PAGE_URL.fullmatch(r.get("url", ""))
        and not r["url"].endswith("/all-skills-a-z")
    ]


def load_context_pages(dataset_path: Path) -> list[dict]:
    """Completed pages that are NOT individual skill pages.

    About/framework/reference pages carry general SFIA context (what the
    responsibility levels mean, how skill pages are structured, terminology)
    that the context agent distills into a briefing for the extractor.
    """
    skill_urls = {p["url"] for p in load_skill_pages(dataset_path)}
    return [
        r for r in load_completed_pages(dataset_path)
        if r.get("markdown") and r["url"] not in skill_urls
    ]
