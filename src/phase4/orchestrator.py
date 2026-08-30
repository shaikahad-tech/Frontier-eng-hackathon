"""Phase 4 — Rebuilt Orchestrator

Key changes:
1. Verification status AFFECTS score contributions:
   - VERIFIED: full weight
   - PARTIALLY_VERIFIED: 75% weight
   - UNKNOWN: 50% weight
   - UNVERIFIED: 25% weight
   - CONTRADICTED: finding suppressed, score contribution removed
2. Score explainability per dimension
3. Evidence graph (Repository -> Dimension -> Finding -> Tool -> Evidence -> File -> Line)
4. Remediation engine (P0/P1/P2/P3 prioritized plan)
5. Proper confidence and evidence coverage computation
"""
from __future__ import annotations
import json
import time
import hashlib
from typing import Any
from collections import defaultdict

from src.phase4.agents import (
    SpecialistAgent, EvidenceCollector,
    AgentFinding, AgentResult, DEFAULT_WEIGHTS, PROFILE_WEIGHTS, HARD_GATES,
)
from src.phase4.specialists import (
    StructureAgent, TestAgent, CodeQualityAgent, MaintenanceAgent,
)
from src.phase4.verification import VerificationAgent, VerificationResult, _finding_id


# Verification status -> score weight multiplier
# This is what makes verification MATTER for the final score
VERIFICATION_WEIGHTS = {
    "VERIFIED": 1.0,
    "PARTIALLY_VERIFIED": 0.75,
    "UNKNOWN": 0.5,
    "UNVERIFIED": 0.25,
    "CONTRADICTED": 0.0,  # Suppressed entirely
}


class Orchestrator:
    """Combines agent outputs, applies verification, gates, and produces final score.

    Verification status directly affects the score contribution of each finding.
    This means the system WITH verification produces different scores than WITHOUT.
    """

    def __init__(self, weights: dict[str, float] = None, gates: dict = None,
                 profile: str = None):
        if profile and profile.upper() in PROFILE_WEIGHTS:
            self.weights = weights or PROFILE_WEIGHTS[profile.upper()]
        else:
            self.weights = weights or DEFAULT_WEIGHTS
        self.gates = gates or HARD_GATES
        self.profile = profile

    def _apply_hard_gates(self, score: float, agent_results: list[AgentResult],
                          evidence: EvidenceCollector) -> tuple[float, list[str]]:
        """Apply hard gates that override weighted averages."""
        gated_score = score
        gate_reasons = []

        sec_findings = evidence.get_findings("security_sast")
        secrets_findings = evidence.get_findings("secrets")
        vuln_findings = evidence.get_findings("vulnerability")

        critical_sec = [f for f in sec_findings + secrets_findings + vuln_findings
                       if f.get("severity") in ("critical", "CRITICAL")]
        if critical_sec:
            gate = self.gates["critical_security"]
            gated_score = min(gated_score, gate["max_score"])
            gate_reasons.append(
                f"Hard gate: {gate['description']} (score capped at {gate['max_score']})")

        confirmed_secrets = [f for f in secrets_findings if f.get("status") in ("FAIL", "CRITICAL")]
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

        if score >= 70 and confidence >= 0.6:
            return {"recommendation": "ADOPT",
                    "criteria": "Score >= 70, confidence >= 0.6, no critical issues",
                    "reasons": []}

        if score < 30:
            return {"recommendation": "AVOID",
                    "criteria": "Score < 30 indicates unacceptable quality",
                    "reasons": gate_reasons or ["Low overall score"]}

        return {"recommendation": "INVESTIGATE",
                "criteria": "Quality is mixed or important unknowns exist",
                "reasons": gate_reasons or ["Score in middle range"]}

    def _get_top_strengths(self, agent_results: list[AgentResult],
                           verifications: list[VerificationResult]) -> list[str]:
        """Extract top 5 strengths from verified findings."""
        verified_ids = {v.finding_id for v in verifications if v.status == "VERIFIED"}
        strengths = []
        for result in agent_results:
            for finding in result.findings:
                fid = _finding_id(finding)
                if finding.score >= 7.0 and (fid in verified_ids or not verifications):
                    strengths.append(f"[{result.dimension}] {finding.claim}")
        return strengths[:5]

    def _get_top_risks(self, agent_results: list[AgentResult],
                        verifications: list[VerificationResult]) -> list[str]:
        """Extract top 5 risks from verified findings."""
        verified_ids = {v.finding_id for v in verifications
                       if v.status in ("VERIFIED", "PARTIALLY_VERIFIED", "UNKNOWN")}
        risks = []
        for result in agent_results:
            for finding in result.findings:
                fid = _finding_id(finding)
                if finding.score <= 3.0 and (fid in verified_ids or not verifications):
                    risks.append(f"[{result.dimension}] {finding.claim}")
        return risks[:5]

    def _build_evidence_graph(self, agent_results: list[AgentResult],
                               verifications: list[VerificationResult]) -> dict[str, Any]:
        """Build serializable evidence graph."""
        graph = {"repository": "", "dimensions": {}}
        verify_map = {v.finding_id: v for v in verifications}

        for result in agent_results:
            dim = result.dimension
            graph["dimensions"].setdefault(dim, {"findings": []})
            for finding in result.findings:
                fid = _finding_id(finding)
                vr = verify_map.get(fid)
                node = {
                    "finding_id": fid,
                    "claim": finding.claim,
                    "score": finding.score,
                    "confidence": finding.confidence,
                    "agent": finding.agent,
                    "sources": finding.sources,
                    "verification_status": vr.status if vr else "UNKNOWN",
                    "evidence": finding.evidence,
                    "supporting": vr.supporting_evidence if vr else [],
                    "contradicting": vr.contradicting_evidence if vr else [],
                }
                for ev in finding.evidence:
                    if isinstance(ev, dict):
                        if "file" in ev:
                            node["file"] = ev["file"]
                        if "line" in ev:
                            node["line"] = ev["line"]
                graph["dimensions"][dim]["findings"].append(node)

        return graph

    def _build_remediation_plan(self, agent_results: list[AgentResult],
                                verifications: list[VerificationResult],
                                evidence: EvidenceCollector) -> list[dict]:
        """Build prioritized remediation plan (P0/P1/P2/P3)."""
        items = []
        verify_map = {v.finding_id: v for v in verifications}

        all_findings = []
        for result in agent_results:
            for finding in result.findings:
                fid = _finding_id(finding)
                vr = verify_map.get(fid)
                if vr and vr.status == "CONTRADICTED":
                    continue
                all_findings.append((result.dimension, finding, vr))

        all_findings.sort(key=lambda x: x[1].score)

        for dim, finding, vr in all_findings:
            if finding.score >= 5.0:
                continue

            if finding.score <= 1.0:
                priority = "P0"
            elif finding.score <= 2.0:
                priority = "P1"
            elif finding.score <= 3.5:
                priority = "P2"
            else:
                priority = "P3"

            file_path = ""
            line_num = ""
            for ev in finding.evidence:
                if isinstance(ev, dict):
                    if "file" in ev:
                        file_path = ev["file"]
                    if "line" in ev:
                        line_num = ev["line"]

            items.append({
                "priority": priority,
                "finding": finding.claim,
                "dimension": dim,
                "severity": "critical" if finding.score <= 1.0 else "high" if finding.score <= 2.0 else "medium" if finding.score <= 3.5 else "low",
                "evidence": [str(e) for e in finding.evidence[:3]],
                "file": file_path,
                "line": line_num,
                "recommended_action": self._suggest_action(finding, dim),
                "expected_impact": f"Would improve {dim} score from {finding.score:.1f} to ~7+",
                "verification_status": vr.status if vr else "UNKNOWN",
            })

        return items[:15]

    def _suggest_action(self, finding: AgentFinding, dim: str) -> str:
        """Suggest a remediation action based on the finding."""
        claim = finding.claim.lower()
        if "test" in claim and "no" in claim:
            return "Add comprehensive test suite with meaningful assertions"
        if "test" in claim and ("fail" in claim or "broken" in claim):
            return "Fix failing tests and ensure CI enforces passing tests"
        if "secret" in claim or "hardcoded" in claim:
            return "Remove committed secrets and use environment variables"
        if "injection" in claim or "subprocess" in claim:
            return "Fix injection vulnerability: sanitize inputs, avoid shell=True"
        if "complexity" in claim:
            return "Refactor high-complexity functions to reduce cyclomatic complexity"
        if "documentation" in claim or "readme" in claim:
            return "Add comprehensive README with installation, usage, and API docs"
        if "stale" in claim or "abandoned" in claim or "maintenance" in claim:
            return "Resume active maintenance: update dependencies, respond to issues"
        if "dependenc" in claim:
            return "Pin dependencies, update vulnerable packages, add lockfile"
        if "ci" in claim:
            return "Set up CI/CD pipeline with automated testing and security scanning"
        return f"Address {dim} issues identified in the evaluation"

    def _score_explanation(self, dim: str, result: AgentResult,
                           verifications: list[VerificationResult]) -> dict[str, Any]:
        """Explain why a dimension got the score it did."""
        positives = []
        negatives = []
        verify_map = {v.finding_id: v for v in verifications}

        for finding in result.findings:
            fid = _finding_id(finding)
            vr = verify_map.get(fid)
            status = vr.status if vr else "UNKNOWN"

            if status == "CONTRADICTED":
                continue

            weight_mult = VERIFICATION_WEIGHTS.get(status, 0.5)
            effective_score = finding.score * weight_mult

            entry = f"{finding.claim} (score: {finding.score:.1f}, status: {status}, effective: {effective_score:.1f})"
            if finding.score >= 6.0:
                positives.append(entry)
            elif finding.score <= 4.0:
                negatives.append(entry)

        return {
            "dimension": dim,
            "raw_score": round(result.score, 2),
            "score_0_100": round(result.score * 10, 1),
            "positives": positives,
            "negatives": negatives,
            "evidence_coverage": round(result.evidence_coverage, 3),
            "unknowns": result.unknowns,
        }

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
        """Produce the final evaluation.

        Verification status directly affects score contributions:
        - VERIFIED findings contribute full score
        - PARTIALLY_VERIFIED contribute 75%
        - UNKNOWN contribute 50%
        - UNVERIFIED contribute 25%
        - CONTRADICTED findings are suppressed (0%)
        """
        verify_map = {v.finding_id: v for v in verifications}

        # Apply verification statuses to findings
        for result in agent_results:
            for finding in result.findings:
                fid = _finding_id(finding)
                vr = verify_map.get(fid)
                if vr:
                    finding.status = vr.status
                else:
                    finding.status = "UNKNOWN"

        dim_map = {
            "structure": "structure", "testing": "testing",
            "code_quality": "code_quality", "maintenance": "maintenance",
        }

        # Calculate verification-weighted score
        agent_scores = {}
        score_explanations = {}
        total_weight = 0
        weighted_sum = 0

        for result in agent_results:
            dim = result.dimension
            weight_key = dim_map.get(dim, dim)
            weight = self.weights.get(weight_key, 0)

            if result.findings:
                finding_scores = []
                finding_weights = []
                for finding in result.findings:
                    fid = _finding_id(finding)
                    vr = verify_map.get(fid)
                    status = vr.status if vr else "UNKNOWN"
                    mult = VERIFICATION_WEIGHTS.get(status, 0.5)
                    finding_scores.append(finding.score * mult)
                    finding_weights.append(finding.confidence if finding.confidence > 0 else 0.5)

                if sum(finding_weights) > 0:
                    adj_score = sum(s * w for s, w in zip(finding_scores, finding_weights)) / sum(finding_weights)
                else:
                    adj_score = sum(finding_scores) / len(finding_scores) if finding_scores else 0
            else:
                adj_score = result.score

            # If verification is disabled (empty verifications), use raw score
            if not verifications:
                adj_score = result.score

            agent_scores[dim] = adj_score * 10
            weighted_sum += agent_scores[dim] * weight
            total_weight += weight
            score_explanations[dim] = self._score_explanation(dim, result, verifications)

        final_score = weighted_sum / total_weight if total_weight > 0 else 0
        gated_score, gate_reasons = self._apply_hard_gates(final_score, agent_results, evidence)

        avg_confidence = sum(r.confidence for r in agent_results) / len(agent_results) if agent_results else 0
        avg_coverage = sum(r.evidence_coverage for r in agent_results) / len(agent_results) if agent_results else 0

        verifier = VerificationAgent(evidence)
        verify_metrics = verifier.compute_verification_rate(verifications)

        # Confidence = agent confidence * (0.5 + 0.5 * verification_rate)
        if verifications:
            adjusted_confidence = avg_confidence * (0.5 + 0.5 * verify_metrics["weighted_verification_rate"])
        else:
            adjusted_confidence = avg_confidence * 0.5

        recommendation = self._generate_recommendation(gated_score, adjusted_confidence, gate_reasons)
        evidence_graph = self._build_evidence_graph(agent_results, verifications)
        remediation_plan = self._build_remediation_plan(agent_results, verifications, evidence)
        known_unknowns = [u for r in agent_results for u in r.unknowns]

        report = {
            "schema_version": "1.0",
            "system": "advanced",
            "score": round(gated_score, 2),
            "grade": self._score_to_grade(gated_score),
            "confidence": round(adjusted_confidence, 3),
            "evidence_coverage": round(avg_coverage, 3),
            "verification_rate": verify_metrics["verification_rate"],
            "weighted_verification_rate": verify_metrics["weighted_verification_rate"],
            "verification_metrics": verify_metrics,
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
            "score_explanation": score_explanations,
            "weights": self.weights,
            "top_strengths": self._get_top_strengths(agent_results, verifications),
            "top_risks": self._get_top_risks(agent_results, verifications),
            "uncertainties": known_unknowns,
            "known_unknowns": known_unknowns,
            "verification_details": [
                {"finding_id": v.finding_id, "claim": v.claim,
                 "claim_type": v.claim_type, "status": v.status,
                 "supporting": v.supporting_evidence,
                 "contradicting": v.contradicting_evidence}
                for v in verifications
            ],
            "evidence_graph": evidence_graph,
            "remediation_plan": remediation_plan,
            "hard_gates_applied": self.gates,
            "metadata": {
                "agent_count": len(agent_results),
                "total_findings": len(verifications),
                "contradicted_findings": sum(1 for v in verifications if v.status == "CONTRADICTED"),
                "verified_findings": sum(1 for v in verifications if v.status == "VERIFIED"),
            },
        }

        return report


def evaluate_advanced(repo_path: str,
                      weights: dict[str, float] = None,
                      gates: dict = None,
                      profile: str = None) -> dict[str, Any]:
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

    orchestrator = Orchestrator(weights=weights, gates=gates, profile=profile)
    report = orchestrator.orchestrate(agent_results, verifications, evidence)

    report["metadata"]["evaluation_time_seconds"] = round(time.time() - start_time, 3)
    report["metadata"]["agents_run"] = [a.AGENT_NAME for a in agents]

    return report


def evaluate_advanced_no_verification(repo_path: str,
                                       weights: dict[str, float] = None,
                                       gates: dict = None,
                                       profile: str = None) -> dict[str, Any]:
    """Run advanced evaluation WITHOUT verification for ablation comparison.

    This runs the same agents but skips verification, so all findings
    get full weight. The score will differ from the verified version,
    proving verification matters.
    """
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
    verifications = []  # No verification

    orchestrator = Orchestrator(weights=weights, gates=gates, profile=profile)
    report = orchestrator.orchestrate(agent_results, verifications, evidence)

    report["metadata"]["evaluation_time_seconds"] = round(time.time() - start_time, 3)
    report["metadata"]["agents_run"] = [a.AGENT_NAME for a in agents]
    report["metadata"]["verification_enabled"] = False

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
