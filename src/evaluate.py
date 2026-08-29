"""
Evaluation framework — runs both baseline and advanced solutions on all
test repositories and produces a comprehensive comparison report.

Primary metric: Score accuracy — how close the assessment score is to the
ground truth score (mean absolute error, lower is better).

Secondary metrics:
- Ranking correlation — does the solution rank repos in the same order?
- Finding specificity — does the solution cite specific evidence?
- Verification rate — what fraction of findings are verified?
- Human time per task — how long does the assessment take?
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.baseline import run_baseline
from src.advanced import run_advanced
from src.generate_test_repos import GROUND_TRUTH, generate_all


def run_evaluation(test_repos_dir: str = None, output_dir: str = "evaluation") -> dict:
    """
    Run the full evaluation: baseline vs advanced on all test repos.

    Args:
        test_repos_dir: Directory containing test repositories.
        output_dir: Directory to save evaluation results.

    Returns:
        Full evaluation report.
    """
    if test_repos_dir is None:
        test_repos_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_repos"
        )

    os.makedirs(output_dir, exist_ok=True)

    # Ensure test repos exist
    if not os.path.exists(os.path.join(test_repos_dir, "platinum_repo")):
        print("Test repos not found. Generating...")
        generate_all()

    # Load ground truth
    gt_path = os.path.join(test_repos_dir, "ground_truth.json")
    if os.path.exists(gt_path):
        with open(gt_path) as f:
            ground_truth = json.load(f)
    else:
        ground_truth = GROUND_TRUTH

    # Get all test repos (directories in the test_repos dir)
    repo_names = []
    for name in sorted(os.listdir(test_repos_dir)):
        repo_path = os.path.join(test_repos_dir, name)
        # Accept any directory that's in ground truth (don't require .git)
        if os.path.isdir(repo_path) and name in ground_truth:
            repo_names.append(name)

    print(f"Found {len(repo_names)} test repositories")

    results = {
        "baseline": [],
        "advanced": [],
        "ground_truth": ground_truth,
    }

    # Run baseline on each repo
    print("\n--- Running Baseline ---")
    for name in repo_names:
        repo_path = os.path.join(test_repos_dir, name)
        print(f"  Baseline: {name}...", end=" ")

        start = time.time()
        result = run_baseline(repo_path)
        elapsed = time.time() - start

        result["repo_name"] = name
        result["elapsed_seconds"] = round(elapsed, 3)
        result["ground_truth_score"] = ground_truth[name]["score"]
        result["score_error"] = abs(result["overall_score"] - ground_truth[name]["score"])

        results["baseline"].append(result)
        print(f"score={result['overall_score']} (truth={ground_truth[name]['score']}, error={result['score_error']:.1f})")

    # Run advanced on each repo
    print("\n--- Running Advanced ---")
    for name in repo_names:
        repo_path = os.path.join(test_repos_dir, name)
        print(f"  Advanced: {name}...", end=" ")

        start = time.time()
        result = run_advanced(repo_path)
        elapsed = time.time() - start

        result["repo_name"] = name
        result["elapsed_seconds"] = round(elapsed, 3)
        result["ground_truth_score"] = ground_truth[name]["score"]
        result["score_error"] = abs(result["overall_score"] - ground_truth[name]["score"])

        results["advanced"].append(result)
        print(f"score={result['overall_score']} (truth={ground_truth[name]['score']}, error={result['score_error']:.1f})")

    # Compute metrics
    report = compute_metrics(results)

    # Save full results
    results_path = os.path.join(output_dir, "full_results.json")
    with open(results_path, "w") as f:
        # Remove non-serializable fields
        clean_results = _clean_for_json(results)
        json.dump(clean_results, f, indent=2, default=str)

    # Save report
    report_path = os.path.join(output_dir, "report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Save markdown report
    md_report = _generate_markdown_report(report)
    md_path = os.path.join(output_dir, "report.md")
    with open(md_path, "w") as f:
        f.write(md_report)

    # Print summary table
    print_summary(report)

    return report


def compute_metrics(results: dict) -> dict:
    """Compute comparison metrics between baseline and advanced."""
    baseline_results = results["baseline"]
    advanced_results = results["advanced"]
    ground_truth = results["ground_truth"]

    # --- Score accuracy (MAE: Mean Absolute Error) ---
    baseline_mae = sum(r["score_error"] for r in baseline_results) / len(baseline_results)
    advanced_mae = sum(r["score_error"] for r in advanced_results) / len(advanced_results)

    # --- Ranking correlation (Spearman-like: count of concordant pairs) ---
    baseline_ranking = [r["repo_name"] for r in sorted(baseline_results, key=lambda x: x["overall_score"])]
    advanced_ranking = [r["repo_name"] for r in sorted(advanced_results, key=lambda x: x["overall_score"])]
    truth_ranking = [name for name, _ in sorted(ground_truth.items(), key=lambda x: x[1]["score"])]

    baseline_rank_score = _ranking_accuracy(baseline_ranking, truth_ranking)
    advanced_rank_score = _ranking_accuracy(advanced_ranking, truth_ranking)

    # --- Finding specificity (count of specific evidence-backed findings) ---
    baseline_evidence = sum(len(r.get("strengths", []) + r.get("weaknesses", [])) for r in baseline_results)
    advanced_evidence = sum(len(r.get("strengths", []) + r.get("weaknesses", [])) for r in advanced_results)

    # --- Verification rate (advanced only) ---
    advanced_verification_rates = [r.get("verification", {}).get("verification_rate", 0) for r in advanced_results]
    avg_verification_rate = sum(advanced_verification_rates) / len(advanced_verification_rates) if advanced_verification_rates else 0

    # --- Human time per task ---
    baseline_time = sum(r.get("elapsed_seconds", 0) for r in baseline_results) / len(baseline_results)
    advanced_time = sum(r.get("elapsed_seconds", 0) for r in advanced_results) / len(advanced_results)

    # --- Recommendation accuracy ---
    baseline_rec_correct = sum(
        1 for r in baseline_results
        if r.get("recommendation") == ground_truth[r["repo_name"]]["rec"]
    )
    advanced_rec_correct = sum(
        1 for r in advanced_results
        if r.get("recommendation") == ground_truth[r["repo_name"]]["rec"]
    )

    # --- Per-repo comparison ---
    per_repo = []
    for b, a in zip(baseline_results, advanced_results):
        per_repo.append({
            "repo": b["repo_name"],
            "ground_truth_score": b["ground_truth_score"],
            "baseline_score": b["overall_score"],
            "advanced_score": a["overall_score"],
            "baseline_error": b["score_error"],
            "advanced_error": a["score_error"],
            "baseline_findings": len(b.get("strengths", []) + b.get("weaknesses", [])),
            "advanced_findings": len(a.get("strengths", []) + a.get("weaknesses", [])),
            "baseline_time": b.get("elapsed_seconds", 0),
            "advanced_time": a.get("elapsed_seconds", 0),
            "advanced_verification_rate": a.get("verification", {}).get("verification_rate", 0),
        })

    report = {
        "primary_metric": {
            "name": "Mean Absolute Error (score accuracy)",
            "description": "Lower is better. Measures how far the assessment score is from ground truth.",
            "baseline": round(baseline_mae, 2),
            "advanced": round(advanced_mae, 2),
            "improvement": round(baseline_mae - advanced_mae, 2),
            "improvement_pct": round((baseline_mae - advanced_mae) / baseline_mae * 100, 1) if baseline_mae > 0 else 0,
        },
        "ranking_accuracy": {
            "name": "Ranking accuracy",
            "description": "Fraction of repo pairs ranked in the same order as ground truth.",
            "baseline": round(baseline_rank_score, 3),
            "advanced": round(advanced_rank_score, 3),
            "improvement": round(advanced_rank_score - baseline_rank_score, 3),
        },
        "finding_specificity": {
            "name": "Total findings",
            "description": "Total number of specific strengths/weaknesses identified.",
            "baseline": baseline_evidence,
            "advanced": advanced_evidence,
            "improvement": advanced_evidence - baseline_evidence,
        },
        "verification_rate": {
            "name": "Verification rate",
            "description": "Fraction of findings backed by tool evidence (advanced only).",
            "advanced": round(avg_verification_rate, 3),
        },
        "time_per_task": {
            "name": "Average time per task (seconds)",
            "baseline": round(baseline_time, 3),
            "advanced": round(advanced_time, 3),
        },
        "recommendation_accuracy": {
            "name": "Recommendation accuracy",
            "description": "Correct adopt/investigate/avoid recommendations.",
            "baseline": f"{baseline_rec_correct}/{len(baseline_results)}",
            "advanced": f"{advanced_rec_correct}/{len(advanced_results)}",
            "baseline_pct": round(baseline_rec_correct / len(baseline_results) * 100, 1),
            "advanced_pct": round(advanced_rec_correct / len(advanced_results) * 100, 1),
        },
        "per_repo": per_repo,
        "total_repos": len(baseline_results),
    }

    return report


def _ranking_accuracy(predicted: list, truth: list) -> float:
    """Compute fraction of concordant pairs."""
    if len(predicted) < 2:
        return 1.0
    concordant = 0
    total = 0
    for i in range(len(predicted)):
        for j in range(i + 1, len(predicted)):
            pi, pj = predicted[i], predicted[j]
            ti_idx = truth.index(pi) if pi in truth else -1
            tj_idx = truth.index(pj) if pj in truth else -1
            if ti_idx >= 0 and tj_idx >= 0:
                total += 1
                if (ti_idx < tj_idx) == (i < j):
                    concordant += 1
    return concordant / total if total > 0 else 0.0


def _clean_for_json(obj):
    """Remove non-serializable fields from results."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items() if k != "_trajectory" and not callable(v)}
    if isinstance(obj, list):
        return [_clean_for_json(x) for x in obj]
    return obj


def _generate_markdown_report(report: dict) -> str:
    """Generate a human-readable markdown report."""
    lines = ["# Evaluation Report", ""]

    pm = report["primary_metric"]
    lines.append(f"## Primary Metric: {pm['name']}")
    lines.append(f"")
    lines.append(f"{pm['description']}")
    lines.append(f"")
    lines.append(f"| | Baseline | Advanced | Change |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| MAE | {pm['baseline']} | {pm['advanced']} | {pm['improvement']} ({pm['improvement_pct']}%) |")
    lines.append("")

    ra = report["ranking_accuracy"]
    lines.append(f"## Ranking Accuracy")
    lines.append(f"| | Baseline | Advanced | Change |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| Concordant pairs | {ra['baseline']:.1%} | {ra['advanced']:.1%} | {ra['improvement']:+.1%} |")
    lines.append("")

    fs = report["finding_specificity"]
    lines.append(f"## Finding Specificity")
    lines.append(f"| | Baseline | Advanced | Change |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| Total findings | {fs['baseline']} | {fs['advanced']} | +{fs['improvement']} |")
    lines.append("")

    vr = report["verification_rate"]
    lines.append(f"## Verification Rate (advanced only)")
    lines.append(f"{vr['advanced']:.1%} of findings backed by tool evidence")
    lines.append("")

    rec = report["recommendation_accuracy"]
    lines.append(f"## Recommendation Accuracy")
    lines.append(f"| | Baseline | Advanced |")
    lines.append(f"|---|---|---|")
    lines.append(f"| Correct | {rec['baseline']} | {rec['advanced']} |")
    lines.append(f"| Percentage | {rec['baseline_pct']}% | {rec['advanced_pct']}% |")
    lines.append("")

    lines.append(f"## Per-Repository Comparison")
    lines.append(f"")
    lines.append(f"| Repo | Truth | Baseline | Advanced | B-Error | A-Error | B-Findings | A-Findings |")
    lines.append(f"|---|---|---|---|---|---|---|---|")
    for r in report["per_repo"]:
        lines.append(f"| {r['repo']} | {r['ground_truth_score']} | {r['baseline_score']} | {r['advanced_score']} | {r['baseline_error']:.1f} | {r['advanced_error']:.1f} | {r['baseline_findings']} | {r['advanced_findings']} |")
    lines.append("")

    return "\n".join(lines)


def print_summary(report: dict):
    """Print a summary table of the evaluation."""
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total test repositories: {report['total_repos']}")
    print()

    pm = report["primary_metric"]
    print(f"PRIMARY METRIC: {pm['name']}")
    print(f"  Baseline MAE:  {pm['baseline']}")
    print(f"  Advanced MAE:  {pm['advanced']}")
    print(f"  Improvement:   {pm['improvement']} ({pm['improvement_pct']}%)")
    print()

    ra = report["ranking_accuracy"]
    print(f"Ranking accuracy:")
    print(f"  Baseline:  {ra['baseline']}")
    print(f"  Advanced:  {ra['advanced']}")
    print(f"  Improvement: {ra['improvement']}")
    print()

    fs = report["finding_specificity"]
    print(f"Finding specificity:")
    print(f"  Baseline:  {fs['baseline']} findings")
    print(f"  Advanced:  {fs['advanced']} findings")
    print(f"  Improvement: {fs['improvement']} more findings")
    print()

    vr = report["verification_rate"]
    print(f"Verification rate (advanced only): {vr['advanced']:.1%}")
    print()

    tt = report["time_per_task"]
    print(f"Time per task:")
    print(f"  Baseline:  {tt['baseline']}s")
    print(f"  Advanced:  {tt['advanced']}s")
    print()

    rec = report["recommendation_accuracy"]
    print(f"Recommendation accuracy:")
    print(f"  Baseline:  {rec['baseline']} ({rec['baseline_pct']}%)")
    print(f"  Advanced:  {rec['advanced']} ({rec['advanced_pct']}%)")
    print()

    print("-" * 70)
    print("PER-REPO COMPARISON")
    print("-" * 70)
    print(f"{'Repo':<22} {'Truth':>5} {'Base':>5} {'Adv':>5} {'B-Err':>5} {'A-Err':>5} {'B-Find':>6} {'A-Find':>6}")
    print("-" * 70)
    for r in report["per_repo"]:
        print(f"{r['repo']:<22} {r['ground_truth_score']:>5} {r['baseline_score']:>5} {r['advanced_score']:>5} {r['baseline_error']:>5.1f} {r['advanced_error']:>5.1f} {r['baseline_findings']:>6} {r['advanced_findings']:>6}")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
