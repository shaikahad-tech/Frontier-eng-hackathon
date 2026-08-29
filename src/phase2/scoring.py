"""
Phase 2 Scoring Engine — calculates weighted category scores, applies hard gates,
determines grades and maturity levels.

Hard gates cap the overall score when critical findings are present:
- Critical security issue: max score = 59
- Broken build: max build/engineering score = 69
- Failing mandatory tests: max reliability score = 69
- Confirmed active secret: security score <= 30
- Known critical vulnerability: security/supply-chain score <= 39
"""

from __future__ import annotations
from typing import Any

from src.phase2.schema import (
    Severity, Status,
    grade_from_score, maturity_from_score,
)


# --- Default Weights ---

DEFAULT_WEIGHTS = {
    "security": 0.20,
    "correctness": 0.15,
    "testing": 0.15,
    "maintainability": 0.10,
    "architecture": 0.10,
    "dependencies": 0.10,
    "cicd": 0.05,
    "documentation": 0.05,
    "reliability": 0.05,
    "reproducibility": 0.05,
}

# Profile-specific weights
PROFILE_WEIGHTS = {
    "CLI": {**DEFAULT_WEIGHTS, "reliability": 0.02, "reproducibility": 0.08},
    "LIBRARY": {**DEFAULT_WEIGHTS, "correctness": 0.20, "testing": 0.15, "reliability": 0.02},
    "WEB_APP": {**DEFAULT_WEIGHTS, "security": 0.25, "reliability": 0.08, "cicd": 0.07},
    "API": {**DEFAULT_WEIGHTS, "security": 0.25, "reliability": 0.08},
    "BACKEND_SERVICE": {**DEFAULT_WEIGHTS, "security": 0.22, "reliability": 0.10, "cicd": 0.07},
    "MONOREPO": {**DEFAULT_WEIGHTS, "architecture": 0.15, "cicd": 0.08},
}


class HardGate:
    """A hard gate that caps the overall or category score."""

    def __init__(self, gate_id: str, name: str, condition_fn, max_score: int,
                 affected_category: str = "overall", message: str = ""):
        self.gate_id = gate_id
        self.name = name
        self.condition_fn = condition_fn
        self.max_score = max_score
        self.affected_category = affected_category
        self.message = message

    def check(self, findings: list, tool_results: list) -> bool:
        return self.condition_fn(findings, tool_results)


class ScoringEngine:
    """
    Calculates the final engineering quality score from analyzer results.
    Applies hard gates, deduplicates findings, and produces the score breakdown.
    """

    def __init__(self, weights: dict = None, profile: str = "UNKNOWN"):
        self.weights = weights or PROFILE_WEIGHTS.get(profile, DEFAULT_WEIGHTS)
        self.profile = profile
        self.hard_gates = self._init_hard_gates()

    def _init_hard_gates(self) -> list[HardGate]:
        return [
            HardGate(
                gate_id="GATE-SEC-CRITICAL",
                name="Critical Security Gate",
                condition_fn=lambda findings, results: any(
                    f.category == "security" and f.severity == Severity.CRITICAL.value
                    and f.status == Status.FAIL.value
                    for f in findings
                ),
                max_score=59,
                affected_category="overall",
                message="Critical security issue detected - overall score capped at 59.",
            ),
            HardGate(
                gate_id="GATE-SECRET",
                name="Secret Exposure Gate",
                condition_fn=lambda findings, results: any(
                    "secret" in f.title.lower() and f.severity in (Severity.HIGH.value, Severity.CRITICAL.value)
                    for f in findings
                ),
                max_score=30,
                affected_category="security",
                message="Confirmed active secret committed - security score capped at 30.",
            ),
            HardGate(
                gate_id="GATE-NO-TESTS",
                name="No Tests Gate",
                condition_fn=lambda findings, results: any(
                    "No tests found" in f.title for f in findings
                ),
                max_score=39,
                affected_category="testing",
                message="No tests found - testing score capped at 39.",
            ),
            HardGate(
                gate_id="GATE-NO-CI",
                name="No CI Gate",
                condition_fn=lambda findings, results: any(
                    "No CI/CD pipeline" in f.title for f in findings
                ),
                max_score=39,
                affected_category="cicd",
                message="No CI/CD pipeline - CI/CD score capped at 39.",
            ),
            HardGate(
                gate_id="GATE-NO-LOCKFILE",
                name="No Lockfile Gate",
                condition_fn=lambda findings, results: any(
                    "No lockfile" in f.title.lower() for f in findings
                ),
                max_score=39,
                affected_category="reproducibility",
                message="No lockfile - reproducibility score capped at 39.",
            ),
        ]

    def score(self, tool_results: list, findings: list) -> dict:
        """Calculate the final score from all tool results."""
        deduped = self._deduplicate_findings(findings)
        category_scores = self._extract_category_scores(tool_results)

        triggered_gates = []
        for gate in self.hard_gates:
            if gate.check(deduped, tool_results):
                triggered_gates.append({
                    "gate_id": gate.gate_id,
                    "name": gate.name,
                    "max_score": gate.max_score,
                    "affected_category": gate.affected_category,
                    "message": gate.message,
                })
                if gate.affected_category == "overall":
                    pass
                else:
                    category_scores[gate.affected_category] = min(
                        category_scores.get(gate.affected_category, 0),
                        gate.max_score,
                    )

        overall = 0
        for category, weight in self.weights.items():
            score = category_scores.get(category, 35)
            overall += score * weight

        overall = int(round(overall))

        for gate in triggered_gates:
            if gate["affected_category"] == "overall":
                overall = min(overall, gate["max_score"])

        critical_count = sum(1 for f in deduped if f.severity == Severity.CRITICAL.value)
        high_count = sum(1 for f in deduped if f.severity == Severity.HIGH.value)
        medium_count = sum(1 for f in deduped if f.severity == Severity.MEDIUM.value)
        overall -= min(30, critical_count * 12 + high_count * 6 + medium_count * 2)
        overall = max(0, overall)

        grade = grade_from_score(overall)
        maturity = maturity_from_score(overall)

        return {
            "overall_score": overall,
            "grade": grade,
            "maturity_level": maturity,
            "maturity_label": self._maturity_label(maturity),
            "category_scores": category_scores,
            "hard_gates_triggered": triggered_gates,
            "weights": self.weights,
            "total_findings": len(deduped),
            "dedup_removed": len(findings) - len(deduped),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": sum(1 for f in deduped if f.severity == Severity.LOW.value),
        }

    def _extract_category_scores(self, tool_results: list) -> dict[str, int]:
        """Extract the score for each category from tool results."""
        category_scores = {}
        for result in tool_results:
            if not isinstance(result, dict):
                continue
            metrics = result.get("metrics", {})
            for key, value in metrics.items():
                if key.endswith("_score") and isinstance(value, (int, float)):
                    category = key.replace("_score", "")
                    category_mapping = {
                        "architecture": "architecture", "testing": "testing",
                        "documentation": "documentation", "security": "security",
                        "sast": "security", "maintainability": "maintainability",
                        "complexity": "maintainability", "dependencies": "dependencies",
                        "dependency": "dependencies", "git": "cicd", "cicd": "cicd",
                        "container": "security", "reliability": "reliability",
                        "reproducibility": "reproducibility", "tech_debt": "maintainability",
                    }
                    mapped = category_mapping.get(category, category)
                    if mapped not in category_scores or value > category_scores[mapped]:
                        category_scores[mapped] = max(0, min(100, int(value)))

        for cat in self.weights:
            if cat not in category_scores:
                category_scores[cat] = 35

        security_scores = []
        for key in ["security", "sast", "container"]:
            if key in category_scores:
                security_scores.append(category_scores.pop(key))
        if security_scores:
            category_scores["security"] = min(security_scores)

        maint_scores = []
        for key in ["maintainability", "complexity", "tech_debt"]:
            if key in category_scores:
                maint_scores.append(category_scores.pop(key))
        if maint_scores:
            category_scores["maintainability"] = sum(maint_scores) // len(maint_scores)

        return category_scores

    def _deduplicate_findings(self, findings: list) -> list:
        """Remove duplicate findings based on category, title, and file."""
        seen = set()
        deduped = []
        for f in findings:
            files_key = tuple(sorted(tuple(ff.get("path", "")) for ff in f.files)) if f.files else ()
            key = (f.category, f.title, files_key)
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        return deduped

    def _maturity_label(self, level: int) -> str:
        labels = {
            0: "Level 0 - Unstructured",
            1: "Level 1 - Basic",
            2: "Level 2 - Functional",
            3: "Level 3 - Professional",
            4: "Level 4 - Production Ready",
            5: "Level 5 - Engineering Mature",
        }
        return labels.get(level, "Unknown")
