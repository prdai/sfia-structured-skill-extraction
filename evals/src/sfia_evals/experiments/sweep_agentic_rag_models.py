import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agentic_rag_matcher import SWEEP_MODELS
from agentic_rag_matcher.matcher import AgenticRAGMatcher

from ..harness import _mean, _score_role

REPO_ROOT = Path(__file__).resolve().parents[4]
ROLES_PATH = REPO_ROOT / "evals" / "eu-ict-sfia-role-profiles.json"
EXPERIMENTS_PATH = REPO_ROOT / "evals" / "experiments.json"

WORKERS = 16


def score_role(matcher: AgenticRAGMatcher, role: dict) -> tuple:
    start = time.perf_counter()
    try:
        predicted = [(m.skill, m.level) for m in matcher.match(role["summary_statement"])]
        failed = False
    except Exception:
        predicted = []
        failed = True
    duration = time.perf_counter() - start
    return _score_role(role, predicted), duration, failed


def eval_model(model: str, roles: list[dict]) -> dict:
    matcher = AgenticRAGMatcher(model)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        scored = list(pool.map(lambda role: score_role(matcher, role), roles))

    results = [s[0] for s in scored]
    durations = [s[1] for s in scored]
    failures = sum(s[2] for s in scored)

    level_maes = [r.level_mae for r in results if r.level_mae is not None]
    level_exact = [r.level_accuracy_exact for r in results if r.level_accuracy_exact is not None]
    level_within = [r.level_accuracy_within_1 for r in results if r.level_accuracy_within_1 is not None]
    return {
        "mean_precision": _mean([r.precision for r in results]),
        "mean_recall": _mean([r.recall for r in results]),
        "mean_f1": _mean([r.f1 for r in results]),
        "mean_level_mae": _mean(level_maes) if level_maes else None,
        "mean_level_accuracy_exact": _mean(level_exact) if level_exact else None,
        "mean_level_accuracy_within_1": _mean(level_within) if level_within else None,
        "mean_seconds_per_record": _mean(durations),
        "failed_roles": failures,
    }


def main():
    roles = json.loads(ROLES_PATH.read_text())["roles"]
    new_rows = []

    for model in SWEEP_MODELS:
        metrics = eval_model(model, roles)
        new_rows.append({
            "implementation": "agentic-rag-crewai",
            "config": {"model": model},
            "metrics": metrics,
        })
        print(f"{model}: P={metrics['mean_precision']:.3f} R={metrics['mean_recall']:.3f} "
              f"F1={metrics['mean_f1']:.3f} failed={metrics['failed_roles']}")

    # Re-read right before writing rather than once at the top: another
    # sweep script may have appended its own rows to this file while this
    # one was running, and a read-once-write-once pattern would clobber them.
    experiments = json.loads(EXPERIMENTS_PATH.read_text()) if EXPERIMENTS_PATH.exists() else []
    experiments.extend(new_rows)
    EXPERIMENTS_PATH.write_text(json.dumps(experiments, indent=2))
    print(f"logged {len(SWEEP_MODELS)} configs to {EXPERIMENTS_PATH}")


if __name__ == "__main__":
    main()
