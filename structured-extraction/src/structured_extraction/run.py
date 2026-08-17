import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from .blocks import load_skill_pages
from .crew import extract_page

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = REPO_ROOT / "data" / "sfia-dataset.json"
OUTPUT_PATH = REPO_ROOT / "structured-extraction" / "output" / "skill-level-records.json"
METRICS_PATH = REPO_ROOT / "structured-extraction" / "output" / "extraction-metrics.json"
CONCURRENCY = 8


def main():
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    pages = load_skill_pages(DATASET_PATH)
    if limit:
        pages = pages[:limit]

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(extract_page, page): page for page in pages}
        results = [_collect(future, futures[future]) for future in as_completed(futures)]

    records = [record for page_records, _ in results for record in page_records]
    page_metrics = [metrics for _, metrics in results if metrics]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, indent=2))

    totals = {
        "pages": len(page_metrics),
        "pages_with_html": sum(1 for m in page_metrics if m["html_available"]),
        "extracted": sum(m["extracted"] for m in page_metrics),
        "range_rejected": sum(len(m["range_rejected"]) for m in page_metrics),
        "verifier_rejected": sum(len(m["verifier_rejected"]) for m in page_metrics),
        "kept": sum(m["kept"] for m in page_metrics),
    }
    METRICS_PATH.write_text(json.dumps({"totals": totals, "pages": page_metrics}, indent=2))

    print(f"wrote {len(records)} records to {OUTPUT_PATH}", file=sys.stderr)
    print(
        f"metrics: {totals['extracted']} extracted, "
        f"{totals['range_rejected']} range-rejected, "
        f"{totals['verifier_rejected']} verifier-rejected, "
        f"{totals['kept']} kept -> {METRICS_PATH}",
        file=sys.stderr,
    )


def _collect(future, page):
    try:
        result = future.result()
    except Exception as e:
        print(f"FAILED {page['url']}: {e}", file=sys.stderr)
        return [], None
    print(f"done {page['url']}", file=sys.stderr)
    return result


if __name__ == "__main__":
    main()
