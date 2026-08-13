import json
import time
from pathlib import Path

from pydantic import BaseModel

from .base import SkillMatcher


class RoleResult(BaseModel):
    title: str
    precision: float
    recall: float
    f1: float
    level_mae: float | None
    level_accuracy_exact: float | None
    level_accuracy_within_1: float | None


class EvalReport(BaseModel):
    role_results: list[RoleResult]
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_level_mae: float | None
    mean_level_accuracy_exact: float | None
    mean_level_accuracy_within_1: float | None
    mean_seconds_per_record: float


def _score_role(role: dict, predicted: list[tuple[str, int]]) -> RoleResult:
    true_skills = {s["name"]: s["level"] for s in role["skills"]}
    predicted_skills = {skill: level for skill, level in predicted}

    correct_names = set(predicted_skills) & set(true_skills)
    precision = len(correct_names) / len(predicted_skills) if predicted_skills else 0.0
    recall = len(correct_names) / len(true_skills) if true_skills else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    level_diffs = [abs(predicted_skills[name] - true_skills[name]) for name in correct_names]
    level_mae = sum(level_diffs) / len(level_diffs) if level_diffs else None
    level_acc_exact = sum(d == 0 for d in level_diffs) / len(level_diffs) if level_diffs else None
    level_acc_1 = sum(d <= 1 for d in level_diffs) / len(level_diffs) if level_diffs else None

    return RoleResult(
        title=role["title"],
        precision=precision,
        recall=recall,
        f1=f1,
        level_mae=level_mae,
        level_accuracy_exact=level_acc_exact,
        level_accuracy_within_1=level_acc_1,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def save_report(name: str, report: EvalReport, results_path: Path) -> None:
    """Store report keyed by implementation name, overwriting any prior
    result for that name - one row per implementation, not one file per run."""
    results = json.loads(results_path.read_text()) if results_path.exists() else {}
    results[name] = report.model_dump(exclude={"role_results"})
    results_path.write_text(json.dumps(results, indent=2))


def run_eval(matcher: SkillMatcher, roles_path: Path) -> EvalReport:
    data = json.loads(roles_path.read_text())

    role_results = []
    durations = []
    for role in data["roles"]:
        start = time.perf_counter()
        predicted = matcher.match(role["summary_statement"])
        durations.append(time.perf_counter() - start)
        role_results.append(_score_role(role, predicted))

    level_maes = [r.level_mae for r in role_results if r.level_mae is not None]
    level_accs_exact = [r.level_accuracy_exact for r in role_results if r.level_accuracy_exact is not None]
    level_accs_1 = [r.level_accuracy_within_1 for r in role_results if r.level_accuracy_within_1 is not None]

    return EvalReport(
        role_results=role_results,
        mean_precision=_mean([r.precision for r in role_results]),
        mean_recall=_mean([r.recall for r in role_results]),
        mean_f1=_mean([r.f1 for r in role_results]),
        mean_level_mae=_mean(level_maes) if level_maes else None,
        mean_level_accuracy_exact=_mean(level_accs_exact) if level_accs_exact else None,
        mean_level_accuracy_within_1=_mean(level_accs_1) if level_accs_1 else None,
        mean_seconds_per_record=_mean(durations),
    )
