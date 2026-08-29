"""
Phase 2 Regression Comparison — compares analysis results between two repositories
or two commits to identify new/resolved findings and score deltas.
"""
from __future__ import annotations
import json
from typing import Any


class RegressionComparator:
    """Compares two analysis results and produces a delta report."""

    def compare(self, result_a: dict, result_b: dict) -> dict:
        """
        Compare result A (before) with result B (after).

        Returns:
            dict with new_findings, resolved_findings, score_delta, metric_deltas
        """
        findings_a = self._collect_findings(result_a)
        findings_b = self._collect_findings(result_b)

        # Create finding keys for comparison
        keys_a = {self._finding_key(f) for f in findings_a}
        keys_b = {self._finding_key(f) for f in findings_b}

        new_findings = [f for f in findings_b if self._finding_key(f) not in keys_a]
        resolved_findings = [f for f in findings_a if self._finding_key(f) not in keys_b]

        # Score delta
        score_a = result_a.get("scores", {}).get("overall_score", 0)
        score_b = result_b.get("scores", {}).get("overall_score", 0)
        score_delta = score_b - score_a

        # Category score deltas
        cat_a = result_a.get("scores", {}).get("category_scores", {})
        cat_b = result_b.get("scores", {}).get("category_scores", {})
        category_deltas = {}
        for cat in set(list(cat_a.keys()) + list(cat_b.keys())):
            category_deltas[cat] = cat_b.get(cat, 0) - cat_a.get(cat, 0)

        # Grade and maturity changes
        grade_a = result_a.get("scores", {}).get("grade", "F")
        grade_b = result_b.get("scores", {}).get("grade", "F")
        maturity_a = result_a.get("scores", {}).get("maturity_level", 0)
        maturity_b = result_b.get("scores", {}).get("maturity_level", 0)

        # Hard gates changes
        gates_a = set(g.get("gate_id") for g in result_a.get("scores", {}).get("hard_gates_triggered", []))
        gates_b = set(g.get("gate_id") for g in result_b.get("scores", {}).get("hard_gates_triggered", []))
        new_gates = gates_b - gates_a
        resolved_gates = gates_a - gates_b

        # Finding count changes
        severity_counts_a = self._severity_counts(findings_a)
        severity_counts_b = self._severity_counts(findings_b)

        return {
            "score_delta": score_delta,
            "score_before": score_a,
            "score_after": score_b,
            "grade_before": grade_a,
            "grade_after": grade_b,
            "grade_changed": grade_a != grade_b,
            "maturity_before": maturity_a,
            "maturity_after": maturity_b,
            "maturity_changed": maturity_a != maturity_b,
            "new_findings": new_findings,
            "resolved_findings": resolved_findings,
            "new_finding_count": len(new_findings),
            "resolved_finding_count": len(resolved_findings),
            "category_deltas": category_deltas,
            "new_hard_gates": list(new_gates),
            "resolved_hard_gates": list(resolved_gates),
            "severity_before": severity_counts_a,
            "severity_after": severity_counts_b,
            "summary": self._generate_summary(score_delta, len(new_findings), len(resolved_findings),
                                             grade_a, grade_b, maturity_a, maturity_b),
        }

    def _finding_key(self, f: dict) -> tuple:
        """Create a stable key for a finding."""
        files = tuple(sorted(tuple(ff.get("path", "")) for ff in f.get("files", [])))
        return (f.get("category", ""), f.get("title", ""), files)

    def _collect_findings(self, result: dict) -> list[dict]:
        findings = []
        for tr in result.get("tool_results", []):
            if isinstance(tr, dict):
                findings.extend(tr.get("findings", []))
        return findings

    def _severity_counts(self, findings: list) -> dict:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = f.get("severity", "info")
            if sev in counts:
                counts[sev] += 1
        return counts

    def _generate_summary(self, score_delta, new_count, resolved_count,
                          grade_a, grade_b, mat_a, mat_b) -> str:
        parts = []
        if score_delta > 0:
            parts.append(f"Score improved by {score_delta} points")
        elif score_delta < 0:
            parts.append(f"Score decreased by {abs(score_delta)} points")
        else:
            parts.append("Score unchanged")

        if new_count > 0:
            parts.append(f"{new_count} new finding(s)")
        if resolved_count > 0:
            parts.append(f"{resolved_count} finding(s) resolved")
        if grade_a != grade_b:
            parts.append(f"Grade changed from {grade_a} to {grade_b}")
        if mat_a != mat_b:
            parts.append(f"Maturity changed from Level {mat_a} to Level {mat_b}")

        return "; ".join(parts) + "."


def run_regression(repo_path_a: str, repo_path_b: str) -> dict:
    """Run analysis on two repos and compare results."""
    from src.phase2.pipeline import Pipeline

    pipeline_a = Pipeline(repo_path_a, verbose=False)
    result_a = pipeline_a.run()

    pipeline_b = Pipeline(repo_path_b, verbose=False)
    result_b = pipeline_b.run()

    comparator = RegressionComparator()
    return comparator.compare(result_a, result_b)
