import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_PATH = REPO_ROOT / "evals" / "results.json"


def main():
    if not RESULTS_PATH.exists():
        print(f"no results yet at {RESULTS_PATH}")
        return

    results = json.loads(RESULTS_PATH.read_text())
    cols = ["mean_precision", "mean_recall", "mean_f1", "mean_level_accuracy_exact",
            "mean_level_accuracy_within_1", "mean_seconds_per_record"]

    header = f"{'implementation':<20}" + "".join(f"{c:>16}" for c in ["P", "R", "F1", "lvl_exact", "lvl_within_1", "sec/record"])
    print(header)
    for name, report in results.items():
        row = f"{name:<20}"
        for col in cols:
            value = report.get(col)
            row += f"{value:>16.3f}" if value is not None else f"{'n/a':>16}"
        print(row)


if __name__ == "__main__":
    main()
