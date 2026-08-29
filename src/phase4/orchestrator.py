"""Phase 4 — Orchestrator and Entry Point

Combines agent outputs, applies verification, gates, and produces final score.
"""
from __future__ import annotations
import json
import time
from typing import Any
from collections import defaultdict

from src.phase4.agents import (
    SpecialistAgent, StructureAgent, TestAgent,
    CodeQualityAgent, MaintenanceAgent, EvidenceCollector,
    AgentFinding, AgentResult, DEFAULT_WEIGHTS, PROFILE_WEIGHTS, HARD_GATES,
)
from src.phase4.verification import VerificationAgent, VerificationResult


class Orchestrator:
    """Combines agent outputs, applies verification, gates, and produces final score."""

    def __init__(self, weights: dict[str, float] = None, gates: dict = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.gates = gates or HARD_GATES

    def _apply_hard_gates(self, score: float, agent_results: list[AgentResult],
                          evidence: EvidenceCollector) -> tuple[float, list[str]]:
        """Apply hard gates that override weighted averages."""
        gated_score = score
        gate_reasons = []

        sec_findings = evidence.get_findings("security_sast")
        secrets_findings = evidence.get_findings("secrets")
        vuln_findings = evidence.get_findings("vulnerability")

        critical_sec = [f for f in sec_findings + secrets_findings + vuln_findings
                       if f.get("severity") == "critical"]
        high_sec = [f for f in sec_findings + secrets_findings + vuln_findings
                   if f.get("severity") == "high"]

        if critical_sec:
            gate = self.gates["critical_security"]
            gated_score = min(gated_score, gate["max_score"])
            gate_reasons.append(f"Hard gate: {gate['description']} (score capped at {gate['max_score']})")

        confirmed_secrets = [f for f in secrets_findings if f.get("status") == "FAIL"]
        if confirmed_secrets:
            gate = self.gates["committed_secret"]
            gated_score = min(gated_score, gate["max_score"])
            gate_reasons.append(f"Hard gate: {gate['description']}")

        exec_raw = evidence.get_raw_data("test_execution")
        if exec_raw.get("failed", 0) > 0 or exec_raw.get("errors", 0) > 0:
            gate = self.gates["failing_tests"]
            gated_score = min(gated_score, gate["max_score"])
            gate_reasons.append(f"Hard gate: {gate['description']}")

        testing_raw = evidence.get_raw_data("testing")
        if not testing_raw.get("has_tests", False):
            gate = self.gates["no_tests"]
            gated_score = min(gated_score, gate["max_score"])
            gate_reasons.append(f"Hard gate: {gate['description']}")

        return gated_score, gate_reasons

    def _generate_recommendation(self, score: float, confidence: float,
                                 gate_reasons: list[str]) -> dict[str, Any]:
        """Generate ADOPT/INVESTIGATE/AVOID recommendation."""
        if gate_reasons and any("critical" in r.lower() or "secret" in r.lower() for r in gate_reasons):
            return {"recommendation": "AVOID",
                    "criteria": "Critical security issues or committed secrets detected",
                    "reasons": gate_reasons}

        if score >= 70 and confidence >= 0.7:
            return {"recommendation": "ADOPT",
                    "criteria": "Score >= 70, confidence >= 0.7, no critical issues",
                    "reasons": []}

        if score < 30:
            return {"recommendation": "AVOID",
                    "criteria": "Score < 30 indicates unacceptable quality",
                    "reasons": gate_reasons or ["Low overall score"]}

        return {"recommendation": "INVESTIGATE",
                "criteria": "Quality is mixed or important unknowns exist",
                "reasons": gate_reasons or ["Score in middle range — requires investigation"]}

    def _get_top_strengths(self, agent_results: list[AgentResult]) -> list[str]:
        strengths = []
        for result in agent_results:
            for finding in result.findings:
                if finding.score >= 7.0 and finding.confidence >= 0.7:
                    strengths.append(f"[{result.dimension}] {finding.claim}")
        return strengths[:5]

    def _get_top_risks(self, agent_results: list[AgentResult]) -> list[str]:
        risks = []
        for result in agent_results:
            for finding in result.findings:
                if finding.score <= 3.0:
                    risks.append(f"[{result.dimension}] {finding.claim}")
        return risks[:5]

    def _score_to_grade(self, score: float) -> str:
        if score >= 90: return "A"
        if score >= 80: return "A-"
        if score >= 70: return "B+"
        if score >= 60: return "B"
        if score >= 50: return "B-"
        if score >= 40: return "C+"
        if score >= 30: return "C"
        return "F"

    def orchestrate(self, agent_results: list[AgentResult],
                    verifications: list[VerificationResult],
                    evidence: EvidenceCollector) -> dict[str, Any]:
        """Produce the final evaluation."""
        contradicted_ids = {v.finding_id for v in verifications if v.status == "CONTRADICTED"}

        for result in agent_results:
            for finding in result.findings:
                fid = f"{finding.agent}_{finding.dimension}"
                if fid in contradicted_ids:
                    finding.status = "CONTRADICTED"
                else:
                    for v in verifications:
                        if v.finding_id == fid:
                            finding.status = v.status
                            break

        dim_map = {
            "structure": "structure", "testing": "testing",
            "code_quality": "code_quality", "maintenance": "maintenance",
        }

        agent_scores = {}
        total_weight = 0
        weighted_sum = 0

        for result in agent_results:
            dim = result.dimension
            weight_key = dim_map.get(dim, dim)
            weight = self.weights.get(weight_key, 0)
            agent_scores[dim] = result.score * 10
            weighted_sum += agent_scores[dim] * weight
            total_weight += weight

        final_score = weighted_sum / total_weight if total_weight > 0 else 0
        gated_score, gate_reasons = self._apply_hard_gates(final_score, agent_results, evidence)

        avg_confidence = sum(r.confidence for r in agent_results) / len(agent_results) if agent_results else 0
        avg_coverage = sum(r.evidence_coverage for r in agent_results) / len(agent_results) if agent_results else 0

        verifier = VerificationAgent(evidence)
        verify_metrics = verifier.compute_verification_rate(verifications)

        adjusted_confidence = avg_confidence * verify_metrics["verification_rate"]
        recommendation = self._generate_recommendation(gated_score, adjusted_confidence, gate_reasons)

        report = {
            "system": "advanced",
            "score": round(gated_score, 2),
            "confidence": round(adjusted_confidence, 3),
            "evidence_coverage": round(avg_coverage, 3),
            "verification_rate": verify_metrics["verification_rate"],
            "weighted_verification_rate": verify_metrics["weighted_verification_rate"],
            "verification_metrics": verify_metrics,
            "grade": self._score_to_grade(gated_score),
            "recommendation": recommendation["recommendation"],
            "recommendation_criteria": recommendation["criteria"],
            "gate_reasons": gate_reasons,
            "agent_breakdown": {
                dim: {"score": round(agent_scores.get(dim, 0), 2),
                      "confidence": next((r.confidence for r in agent_results if r.dimension == dim), 0),
                      "evidence_coverage": next((r.evidence_coverage for r in agent_results if r.dimension == dim), 0),
                      "unknowns": next((r.unknowns for r in agent_results if r.dimension == dim), [])}
                for dim in dim_map.values()
            },
            "weights": self.weights,
            "top_strengths": self._get_top_strengths(agent_results),
            "top_risks": self._get_top_risks(agent_results),
            "uncertainties": [u for r in agent_results for u in r.unknowns],
            "verification_details": [
                {"finding_id": v.finding_id, "claim": v.claim, "status": v.status,
                 "supporting": v.supporting_evidence, "contradicting": v.contradicting_evidence}
                for v in verifications
            ],
            "hard_gates_applied": self.gates,
            "metadata": {
                "agent_count": len(agent_results),
                "total_findings": len(verifications),
                "contradicted_findings": len(contradicted_ids),
            },
        }

        return report


def evaluate_advanced(repo_path: str,
                      weights: dict[str, float] = None,
                      gates: dict = None) -> dict[str, Any]:
    """Run the full advanced multi-agent evaluation."""
    start_time = time.time()

    evidence = EvidenceCollector(repo_path)
    evidence.collect()

    agents = [
        StructureAgent(evidence),
        TestAgent(evidence),
        CodeQualityAgent(evidence),
        MaintenanceAgent(evidence),
    ]

    agent_results = [agent.evaluate() for agent in agents]

    verifier = VerificationAgent(evidence)
    verifications = verifier.verify_all(agent_results)

    orchestrator = Orchestrator(weights=weights, gates=gates)
    report = orchestrator.orchestrate(agent_results, verifications, evidence)

    report["metadata"]["evaluation_time_seconds"] = round(time.time() - start_time, 3)
    report["metadata"]["agents_run"] = [a.AGENT_NAME for a in agents]

    return report


def track_disagreements(agent_results: list[AgentResult]) -> list[dict]:
    """Track when agents disagree on the same dimension."""
    disagreements = []
    dim_scores = defaultdict(dict)

    for result in agent_results:
        for finding in result.findings:
            dim_scores[finding.dimension][finding.agent] = finding.score

    for dim, scores in dim_scores.items():
        if len(scores) > 1:
            values = list(scores.values())
            if max(values) - min(values) > 2.0:
                disagreements.append({
                    "dimension": dim,
                    **scores,
                    "spread": round(max(values) - min(values), 2),
                })

    return disagreements
