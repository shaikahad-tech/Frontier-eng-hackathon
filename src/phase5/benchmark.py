"""Phase 5 — Benchmark Metrics, Runner, and Validation Tests

Evaluation metrics (MAE, RMSE, Spearman, Pearson, pairwise accuracy),
benchmark runner, ablation testing, weight sensitivity, invariance tests,
causal sensitivity tests, and dashboard generation.

Full spec compliance: 15 synthetic repos (12 standard + 3 adversarial),
ground truth manifests, scoring rubrics, ablation testing, weight sensitivity,
invariance tests, causal sensitivity tests, verification metrics, and dashboard.
"""
from __future__ import annotations
import os, re, json, math, time, shutil, hashlib, statistics
from typing import Any, Optional
from collections import defaultdict

from src.phase5.repos import GROUND_TRUTH, SCORING_RUBRICS, generate_all_repos, REPO_GENERATORS


# ═══════════════════════════════════════════════════════════════
# EVALUATION METRICS
# ═══════════════════════════════════════════════════════════════

def mean_absolute_error(predicted: list[float], actual: list[float]) -> float:
    n = min(len(predicted), len(actual))
    if n == 0: return 0.0
    return sum(abs(p - a) for p, a in zip(predicted, actual)) / n

def root_mean_square_error(predicted: list[float], actual: list[float]) -> float:
    n = min(len(predicted), len(actual))
    if n == 0: return 0.0
    return math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / n)

def pearson_correlation(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 2: return 0.0
    x, y = x[:n], y[:n]
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx == 0 or sy == 0: return 0.0
    return cov / (sx * sy)

def spearman_correlation(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 2: return 0.0
    def rank(vals):
        sorted_vals = sorted(enumerate(vals), key=lambda v: v[1])
        ranks = [0] * len(vals)
        i = 0
        while i < len(sorted_vals):
            j = i
            while j < len(sorted_vals) and sorted_vals[j][1] == sorted_vals[i][1]: j += 1
            avg_rank = (i + j - 1) / 2 + 1
            for k in range(i, j): ranks[sorted_vals[k][0]] = avg_rank
            i = j
        return ranks
    rx, ry = rank(x[:n]), rank(y[:n])
    return pearson_correlation(rx, ry)

def pairwise_ranking_accuracy(predicted: list[float], actual: list[float]) -> float:
    n = min(len(predicted), len(actual))
    if n < 2: return 0.0
    correct = 0; total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if actual[i] != actual[j]:
                total += 1
                if (predicted[i] > predicted[j]) == (actual[i] > actual[j]): correct += 1
    return correct / total if total > 0 else 0.0

def median_absolute_error(predicted: list[float], actual: list[float]) -> float:
    n = min(len(predicted), len(actual))
    if n == 0: return 0.0
    return statistics.median([abs(p - a) for p, a in zip(predicted, actual)])


# ═══════════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ═══════════════════════════════════════════════════════════════

def run_benchmark(repos: dict[str, str], verbose: bool = True) -> dict[str, Any]:
    """Run the full benchmark: baseline vs advanced on all repos."""
    from src.phase3.baseline import evaluate_baseline
    from src.phase4.advanced import evaluate_advanced

    results = {}
    for repo_name, repo_path in repos.items():
        if verbose: print(f"  Evaluating {repo_name}...")
        gt = GROUND_TRUTH.get(repo_name, {})
        gt_overall = gt.get("ground_truth", {}).get("overall", 5.0)

        try:
            baseline_result = evaluate_baseline(repo_path)
            baseline_score = baseline_result["score"]
        except Exception as e:
            baseline_result = {"error": str(e)}; baseline_score = 0.0

        try:
            advanced_result = evaluate_advanced(repo_path)
            advanced_score = advanced_result["score"] / 10.0
        except Exception as e:
            advanced_result = {"error": str(e)}; advanced_score = 0.0

        results[repo_name] = {
            "ground_truth": gt_overall,
            "ground_truth_full": gt.get("ground_truth", {}),
            "baseline_score": round(baseline_score, 2),
            "advanced_score": round(advanced_score, 2),
            "baseline_result": baseline_result,
            "advanced_result": advanced_result,
            "known_conditions": gt.get("known_conditions", []),
        }

    gt_scores = [results[r]["ground_truth"] for r in results]
    baseline_scores = [results[r]["baseline_score"] for r in results]
    advanced_scores = [results[r]["advanced_score"] for r in results]

    aggregate = {
        "baseline": {
            "MAE": round(mean_absolute_error(baseline_scores, gt_scores), 3),
            "RMSE": round(root_mean_square_error(baseline_scores, gt_scores), 3),
            "MdAE": round(median_absolute_error(baseline_scores, gt_scores), 3),
            "Pearson": round(pearson_correlation(baseline_scores, gt_scores), 3),
            "Spearman": round(spearman_correlation(baseline_scores, gt_scores), 3),
            "PairwiseAccuracy": round(pairwise_ranking_accuracy(baseline_scores, gt_scores), 3),
        },
        "advanced": {
            "MAE": round(mean_absolute_error(advanced_scores, gt_scores), 3),
            "RMSE": round(root_mean_square_error(advanced_scores, gt_scores), 3),
            "MdAE": round(median_absolute_error(advanced_scores, gt_scores), 3),
            "Pearson": round(pearson_correlation(advanced_scores, gt_scores), 3),
            "Spearman": round(spearman_correlation(advanced_scores, gt_scores), 3),
            "PairwiseAccuracy": round(pairwise_ranking_accuracy(advanced_scores, gt_scores), 3),
        },
    }

    b_mae = aggregate["baseline"]["MAE"]; a_mae = aggregate["advanced"]["MAE"]
    improvement = {
        "MAE_improvement_pct": round((b_mae - a_mae) / b_mae * 100, 1) if b_mae > 0 else 0,
        "Spearman_improvement": round(aggregate["advanced"]["Spearman"] - aggregate["baseline"]["Spearman"], 3),
        "PairwiseAccuracy_improvement": round(aggregate["advanced"]["PairwiseAccuracy"] - aggregate["baseline"]["PairwiseAccuracy"], 3),
    }

    return {"repos": results, "aggregate": aggregate, "improvement": improvement,
            "repo_count": len(results), "scoring_rubrics": SCORING_RUBRICS}


# ═══════════════════════════════════════════════════════════════
# ABLATION TESTING
# ═══════════════════════════════════════════════════════════════

def run_ablation(repos: dict[str, str]) -> dict[str, Any]:
    """Run ablation tests with components removed."""
    from src.phase3.baseline import evaluate_baseline
    from src.phase4.agents import EvidenceCollector
    from src.phase4.specialists import StructureAgent, TestAgent, CodeQualityAgent, MaintenanceAgent
    from src.phase4.verification import VerificationAgent
    from src.phase4.orchestrator import Orchestrator

    configs = {
        "baseline": ["baseline"],
        "full_advanced": ["structure", "testing", "code_quality", "maintenance"],
        "advanced_no_verification": ["structure", "testing", "code_quality", "maintenance", "no_verification"],
        "advanced_no_test_agent": ["structure", "code_quality", "maintenance"],
        "advanced_no_code_agent": ["structure", "testing", "maintenance"],
        "advanced_no_maintenance": ["structure", "testing", "code_quality"],
        "advanced_no_structure": ["testing", "code_quality", "maintenance"],
    }

    ablation_results = {}
    for config_name, agents_to_run in configs.items():
        scores = []; gt_scores = []
        for repo_name, repo_path in repos.items():
            gt = GROUND_TRUTH.get(repo_name, {}).get("ground_truth", {}).get("overall", 5.0)
            gt_scores.append(gt)

            if config_name == "baseline":
                result = evaluate_baseline(repo_path)
                score = result["score"]
            else:
                evidence = EvidenceCollector(repo_path)
                evidence.collect()
                agent_classes = {"structure": StructureAgent, "testing": TestAgent,
                                "code_quality": CodeQualityAgent, "maintenance": MaintenanceAgent}
                agents = [agent_classes[a](evidence) for a in agents_to_run if a in agent_classes]
                agent_results = [a.evaluate() for a in agents]

                if "no_verification" in agents_to_run:
                    verifications = []
                else:
                    verifier = VerificationAgent(evidence)
                    verifications = verifier.verify_all(agent_results)

                orchestrator = Orchestrator()
                report = orchestrator.orchestrate(agent_results, verifications, evidence)
                score = report["score"] / 10.0
            scores.append(score)

        ablation_results[config_name] = {
            "MAE": round(mean_absolute_error(scores, gt_scores), 3),
            "Spearman": round(spearman_correlation(scores, gt_scores), 3),
            "PairwiseAccuracy": round(pairwise_ranking_accuracy(scores, gt_scores), 3),
            "agents": agents_to_run,
        }
    return ablation_results


# ═══════════════════════════════════════════════════════════════
# WEIGHT SENSITIVITY, INVARIANCE, CAUSAL SENSITIVITY
# ═══════════════════════════════════════════════════════════════

def run_weight_ablation(repos: dict[str, str]) -> dict[str, Any]:
    from src.phase4.orchestrator import evaluate_advanced
    weight_configs = {
        "testing_heavy": {"testing": 0.40, "code_quality": 0.20, "structure": 0.15, "maintenance": 0.10, "documentation": 0.05, "dependencies": 0.10},
        "security_heavy": {"testing": 0.15, "code_quality": 0.40, "structure": 0.10, "maintenance": 0.10, "documentation": 0.05, "dependencies": 0.20},
        "equal_weight": {"testing": 0.20, "code_quality": 0.20, "structure": 0.20, "maintenance": 0.15, "documentation": 0.10, "dependencies": 0.15},
        "default": {"testing": 0.25, "code_quality": 0.25, "structure": 0.20, "maintenance": 0.15, "documentation": 0.05, "dependencies": 0.10},
    }
    results = {}
    for config_name, weights in weight_configs.items():
        scores = []; gt_scores = []
        for repo_name, repo_path in repos.items():
            gt = GROUND_TRUTH.get(repo_name, {}).get("ground_truth", {}).get("overall", 5.0)
            gt_scores.append(gt)
            try:
                result = evaluate_advanced(repo_path, weights=weights)
                scores.append(result["score"] / 10.0)
            except: scores.append(0.0)
        results[config_name] = {
            "MAE": round(mean_absolute_error(scores, gt_scores), 3),
            "Spearman": round(spearman_correlation(scores, gt_scores), 3),
            "PairwiseAccuracy": round(pairwise_ranking_accuracy(scores, gt_scores), 3),
            "weights": weights,
        }
    return results


def run_invariance_test(repo_path: str) -> dict[str, Any]:
    """Modify irrelevant properties and check score stability."""
    from src.phase3.baseline import evaluate_baseline
    from src.phase4.orchestrator import evaluate_advanced
    orig_baseline = evaluate_baseline(repo_path)["score"]
    try: orig_advanced = evaluate_advanced(repo_path)["score"] / 10.0
    except: orig_advanced = 0.0

    readme_path = os.path.join(repo_path, "README.md")
    original_readme = ""
    if os.path.exists(readme_path):
        with open(readme_path, "r") as f: original_readme = f.read()
        with open(readme_path, "a") as f: f.write("\n\n<!-- Generated with care -->\n")

    mod_baseline = evaluate_baseline(repo_path)["score"]
    try: mod_advanced = evaluate_advanced(repo_path)["score"] / 10.0
    except: mod_advanced = 0.0

    if original_readme:
        with open(readme_path, "w") as f: f.write(original_readme)

    baseline_delta = abs(mod_baseline - orig_baseline)
    advanced_delta = abs(mod_advanced - orig_advanced)
    return {
        "original_baseline": round(orig_baseline, 2), "modified_baseline": round(mod_baseline, 2),
        "baseline_delta": round(baseline_delta, 2), "original_advanced": round(orig_advanced, 2),
        "modified_advanced": round(mod_advanced, 2), "advanced_delta": round(advanced_delta, 2),
        "baseline_stable": baseline_delta < 1.0, "advanced_stable": advanced_delta < 5.0,
    }


def run_causal_sensitivity_test(repo_path: str) -> dict[str, Any]:
    """Make controlled changes to repository quality and check score response."""
    from src.phase4.orchestrator import evaluate_advanced
    try: orig = evaluate_advanced(repo_path)["score"]
    except: orig = 0.0

    secret_path = os.path.join(repo_path, "secret.txt")
    with open(secret_path, "w") as f: f.write("API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890\n")
    try: with_secret = evaluate_advanced(repo_path)["score"]
    except: with_secret = 0.0
    os.remove(secret_path)

    test_path = os.path.join(repo_path, "tests/test_causal_fail.py")
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "w") as f: f.write('def test_causal_failure():\n    assert False\n')
    try: with_failing = evaluate_advanced(repo_path)["score"]
    except: with_failing = 0.0
    os.remove(test_path)

    return {
        "original_score": round(orig, 2), "score_with_secret": round(with_secret, 2),
        "secret_score_drop": round(orig - with_secret, 2),
        "score_with_failing_tests": round(with_failing, 2),
        "failing_test_score_drop": round(orig - with_failing, 2),
        "secret_responsive": (orig - with_secret) > 10,
        "failing_test_responsive": (orig - with_failing) > 5,
    }


def compute_verification_metrics(benchmark_results: dict) -> dict[str, Any]:
    """Aggregate verification metrics across all repos."""
    all_verify_rates = []; all_contradiction_rates = []; all_unsupported_rates = []
    for repo_name, result in benchmark_results.get("repos", {}).items():
        adv_result = result.get("advanced_result", {})
        verify_metrics = adv_result.get("verification_metrics", {})
        if verify_metrics:
            all_verify_rates.append(verify_metrics.get("verification_rate", 0))
            all_contradiction_rates.append(verify_metrics.get("contradiction_rate", 0))
            all_unsupported_rates.append(verify_metrics.get("unsupported_rate", 0))
    return {
        "avg_verification_rate": round(sum(all_verify_rates) / len(all_verify_rates), 3) if all_verify_rates else 0,
        "avg_contradiction_rate": round(sum(all_contradiction_rates) / len(all_contradiction_rates), 3) if all_contradiction_rates else 0,
        "avg_unsupported_rate": round(sum(all_unsupported_rates) / len(all_unsupported_rates), 3) if all_unsupported_rates else 0,
        "evidence_integrity_score": round(sum(all_verify_rates) / len(all_verify_rates) * 100 if all_verify_rates else 0, 2),
    }


def generate_dashboard(benchmark_results: dict, ablation_results: dict = None,
                       weight_results: dict = None, invariance: dict = None, causal: dict = None) -> dict[str, Any]:
    """Generate a complete benchmark dashboard."""
    agg = benchmark_results.get("aggregate", {})
    imp = benchmark_results.get("improvement", {})
    verify = compute_verification_metrics(benchmark_results)
    dim_analysis = {}
    for repo_name, result in benchmark_results.get("repos", {}).items():
        gt_full = result.get("ground_truth_full", {})
        adv_result = result.get("advanced_result", {})
        agent_breakdown = adv_result.get("agent_breakdown", {})
        for dim, gt_score in gt_full.items():
            if dim == "overall": continue
            if dim not in dim_analysis: dim_analysis[dim] = {"gt_scores": [], "adv_scores": []}
            dim_analysis[dim]["gt_scores"].append(gt_score)
            if dim in agent_breakdown:
                dim_analysis[dim]["adv_scores"].append(agent_breakdown[dim]["score"] / 10)
            elif dim == "documentation":
                dim_analysis[dim]["adv_scores"].append(agent_breakdown.get("structure", {}).get("score", 50) / 10)
            elif dim == "dependencies":
                dim_analysis[dim]["adv_scores"].append(50 / 10)

    failure_modes = {}
    for repo_name, result in benchmark_results.get("repos", {}).items():
        for condition in result.get("known_conditions", []):
            if condition not in failure_modes: failure_modes[condition] = {"count": 0, "detected": 0}
            failure_modes[condition]["count"] += 1
            adv_result = result.get("advanced_result", {})
            top_risks = adv_result.get("top_risks", [])
            if any(condition.replace("_", " ") in r.lower() for r in top_risks):
                failure_modes[condition]["detected"] += 1

    return {
        "overall": {
            "baseline_MAE": agg.get("baseline", {}).get("MAE", 0),
            "advanced_MAE": agg.get("advanced", {}).get("MAE", 0),
            "improvement_pct": imp.get("MAE_improvement_pct", 0),
            "baseline_spearman": agg.get("baseline", {}).get("Spearman", 0),
            "advanced_spearman": agg.get("advanced", {}).get("Spearman", 0),
            "baseline_pairwise": agg.get("baseline", {}).get("PairwiseAccuracy", 0),
            "advanced_pairwise": agg.get("advanced", {}).get("PairwiseAccuracy", 0),
        },
        "by_dimension": {dim: {"MAE": round(mean_absolute_error(d["adv_scores"], d["gt_scores"]), 3),
                              "Spearman": round(spearman_correlation(d["adv_scores"], d["gt_scores"]), 3)}
                        for dim, d in dim_analysis.items() if len(d["gt_scores"]) >= 2},
        "by_failure_mode": failure_modes,
        "verification": verify,
        "ablation": ablation_results,
        "weight_sensitivity": weight_results,
        "invariance": invariance,
        "causal_sensitivity": causal,
        "repo_count": benchmark_results.get("repo_count", 0),
    }


def run_full_benchmark(base_path: str = None, verbose: bool = True) -> dict[str, Any]:
    """Run the complete benchmark suite (7 steps)."""
    if base_path is None: base_path = "/scratch/work/benchmark_repos"
    if verbose: print("Phase 5 Benchmark Suite\n" + "=" * 60)

    if verbose: print("\n[1/7] Generating synthetic repositories...")
    repos = generate_all_repos(base_path)
    if verbose: print(f"  Generated {len(repos)} repositories")

    if verbose: print("\n[2/7] Running baseline vs advanced evaluation...")
    benchmark = run_benchmark(repos, verbose=verbose)

    if verbose: print("\n[3/7] Running ablation tests...")
    try: ablation = run_ablation(repos)
    except Exception as e: ablation = {"error": str(e)}

    if verbose: print("\n[4/7] Running weight sensitivity tests...")
    try: weight_sens = run_weight_ablation(repos)
    except Exception as e: weight_sens = {"error": str(e)}

    if verbose: print("\n[5/7] Running invariance tests...")
    try: invariance = run_invariance_test(list(repos.values())[0])
    except Exception as e: invariance = {"error": str(e)}

    if verbose: print("\n[6/7] Running causal sensitivity tests...")
    try: causal = run_causal_sensitivity_test(list(repos.values())[0])
    except Exception as e: causal = {"error": str(e)}

    if verbose: print("\n[7/7] Generating dashboard...")
    dashboard = generate_dashboard(benchmark, ablation, weight_sens, invariance, causal)

    if verbose:
        print("\n" + "=" * 60 + "\nBENCHMARK RESULTS SUMMARY\n" + "=" * 60)
        agg = benchmark["aggregate"]
        print(f"\nBaseline MAE:     {agg['baseline']['MAE']}")
        print(f"Advanced MAE:     {agg['advanced']['MAE']}")
        print(f"Improvement:      {benchmark['improvement']['MAE_improvement_pct']}%")
        print(f"\nBaseline Spearman:    {agg['baseline']['Spearman']}")
        print(f"Advanced Spearman:    {agg['advanced']['Spearman']}")
        print(f"\nBaseline Pairwise:    {agg['baseline']['PairwiseAccuracy']}")
        print(f"Advanced Pairwise:    {agg['advanced']['PairwiseAccuracy']}")
        print(f"\nVerification Rate:    {dashboard['verification']['avg_verification_rate']}")
        print(f"Repo count:           {benchmark['repo_count']}")

    return {"benchmark": benchmark, "ablation": ablation, "weight_sensitivity": weight_sens,
            "invariance": invariance, "causal_sensitivity": causal, "dashboard": dashboard}
