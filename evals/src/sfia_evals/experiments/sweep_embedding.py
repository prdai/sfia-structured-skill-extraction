import json
import time
from pathlib import Path

from embedding_matcher import EMBEDDING_MODEL, RERANKER_MODEL, RETRIEVAL_K
from embedding_matcher.matcher import EmbeddingMatcher

from ..harness import _mean, _score_role

REPO_ROOT = Path(__file__).resolve().parents[4]
ROLES_PATH = REPO_ROOT / "evals" / "eu-ict-sfia-role-profiles.json"
EXPERIMENTS_PATH = REPO_ROOT / "evals" / "experiments.json"

THRESHOLDS = [0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]


def score_all_roles(matcher: EmbeddingMatcher, roles: list[dict]) -> tuple[list, list[float]]:
    # Rerank scores don't depend on the threshold, so score each role's
    # candidates once (threshold=0) and derive every threshold offline.
    pools = []
    durations = []
    for role in roles:
        start = time.perf_counter()
        pools.append(matcher.search(role["summary_statement"], threshold=0.0))
        durations.append(time.perf_counter() - start)
    return pools, durations


def metrics_at(threshold: float, roles: list[dict], pools: list, durations: list[float]) -> dict:
    results = []
    for role, pool in zip(roles, pools):
        predicted = list({(m.skill, m.level) for m in pool if m.rerank_score >= threshold})
        results.append(_score_role(role, predicted))

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
    }


def main():
    roles = json.loads(ROLES_PATH.read_text())["roles"]
    pools, durations = score_all_roles(EmbeddingMatcher(), roles)

    experiments = json.loads(EXPERIMENTS_PATH.read_text()) if EXPERIMENTS_PATH.exists() else []
    for threshold in THRESHOLDS:
        metrics = metrics_at(threshold, roles, pools, durations)
        experiments.append({
            "implementation": "embedding-qwen3-llm-rerank",
            "config": {
                "embedding_model": EMBEDDING_MODEL,
                "reranker_model": RERANKER_MODEL,
                "retrieval_k": RETRIEVAL_K,
                "rerank_threshold": threshold,
            },
            "metrics": metrics,
        })
        print(f"threshold={threshold}: P={metrics['mean_precision']:.3f} "
              f"R={metrics['mean_recall']:.3f} F1={metrics['mean_f1']:.3f}")

    EXPERIMENTS_PATH.write_text(json.dumps(experiments, indent=2))
    print(f"logged {len(THRESHOLDS)} configs to {EXPERIMENTS_PATH}")


if __name__ == "__main__":
    main()
