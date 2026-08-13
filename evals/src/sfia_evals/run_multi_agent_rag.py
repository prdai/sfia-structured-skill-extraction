from pathlib import Path

from .adapters.multi_agent_rag import MultiAgentRAGMatcherAdapter
from .harness import run_eval, save_report

REPO_ROOT = Path(__file__).resolve().parents[3]
ROLES_PATH = REPO_ROOT / "evals" / "eu-ict-sfia-role-profiles.json"
RESULTS_PATH = REPO_ROOT / "evals" / "results.json"


def main():
    matcher = MultiAgentRAGMatcherAdapter()
    report = run_eval(matcher, ROLES_PATH)
    save_report("multi-agent-rag-crewai", report, RESULTS_PATH)

    for r in report.role_results:
        mae = f"{r.level_mae:.2f}" if r.level_mae is not None else "n/a"
        print(f"{r.title}: P={r.precision:.2f} R={r.recall:.2f} F1={r.f1:.2f} level_mae={mae}")

    print()
    print(f"mean precision:  {report.mean_precision:.3f}")
    print(f"mean recall:     {report.mean_recall:.3f}")
    print(f"mean F1:         {report.mean_f1:.3f}")
    if report.mean_level_mae is not None:
        print(f"mean level MAE (on correctly-matched skills): {report.mean_level_mae:.3f}")
        print(f"mean level accuracy (exact): {report.mean_level_accuracy_exact:.3f}")
        print(f"mean level accuracy (within-1): {report.mean_level_accuracy_within_1:.3f}")
    print(f"mean time per record: {report.mean_seconds_per_record:.2f} s")


if __name__ == "__main__":
    main()
