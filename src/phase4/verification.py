"""Phase 4 — Verification Agent

Verifies that every finding is supported by evidence.
Does NOT re-score. Only verifies claims.
"""
from __future__ import annotations
from typing import Any
from src.phase4.agents import AgentFinding, AgentResult, EvidenceCollector
from dataclasses import dataclass, field


@dataclass
class VerificationResult:
    """Result of verifying a finding."""
    finding_id: str
    claim: str
    status: str  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONTRADICTED, UNKNOWN
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    verifier_notes: str = ""


class VerificationAgent:
    """Verifies that every finding is supported by evidence.

    Does NOT re-score. Only verifies claims.
    """

    def __init__(self, evidence: EvidenceCollector):
        self.evidence = evidence

    def verify_finding(self, finding: AgentFinding) -> VerificationResult:
        """Verify a single finding against tool evidence."""
        claim = finding.claim.lower()
        supporting = []
        contradicting = []
        notes = ""

        if not finding.evidence and not finding.sources:
            return VerificationResult(
                finding_id=f"{finding.agent}_{finding.dimension}",
                claim=finding.claim,
                status="UNVERIFIED",
                contradicting_evidence=["No evidence references provided"],
            )

        for source in finding.sources:
            raw = self.evidence.get_raw_data(source)
            if not raw:
                continue

            if "passing" in claim or "tests pass" in claim:
                exec_raw = self.evidence.get_raw_data("test_execution")
                passed = exec_raw.get("passed", 0)
                failed = exec_raw.get("failed", 0)
                if passed > 0 and failed == 0:
                    supporting.append(f"test_execution: {passed} passed, 0 failed")
                elif failed > 0:
                    contradicting.append(f"test_execution: {failed} tests failing")
                    return VerificationResult(
                        finding_id=f"{finding.agent}_{finding.dimension}",
                        claim=finding.claim, status="CONTRADICTED",
                        supporting_evidence=supporting,
                        contradicting_evidence=contradicting,
                        verifier_notes="Tool data contradicts claim")

            if "coverage" in claim:
                cov_raw = self.evidence.get_raw_data("coverage")
                cov_pct = cov_raw.get("coverage_pct")
                if cov_pct is not None:
                    supporting.append(f"coverage: {cov_pct:.1f}%")

            if "security" in claim or "vulnerab" in claim or "secret" in claim:
                sec_findings = self.evidence.get_findings("security_sast")
                secrets_findings = self.evidence.get_findings("secrets")
                vuln_findings = self.evidence.get_findings("vulnerability")
                total_sec = len(sec_findings) + len(secrets_findings) + len(vuln_findings)
                if "no security" in claim or "no issues" in claim:
                    if total_sec == 0:
                        supporting.append("No security findings in tool output")
                    else:
                        contradicting.append(f"{total_sec} security findings found")
                elif total_sec > 0:
                    supporting.append(f"{total_sec} security findings confirmed")

            if "complexity" in claim:
                cx_raw = self.evidence.get_raw_data("complexity")
                if cx_raw:
                    supporting.append(f"complexity data available: {cx_raw}")

            if "documentation" in claim or "readme" in claim:
                doc_raw = self.evidence.get_raw_data("documentation")
                if doc_raw:
                    supporting.append("documentation analyzer ran")

            if "maintain" in claim or "git" in claim or "commit" in claim:
                git_raw = self.evidence.get_raw_data("git_maturity")
                if git_raw:
                    supporting.append("git_maturity data available")

        if contradicting:
            status = "CONTRADICTED"
        elif supporting:
            status = "VERIFIED" if len(supporting) >= 1 else "PARTIALLY_VERIFIED"
        elif finding.sources:
            status = "PARTIALLY_VERIFIED"
            notes = "Source analyzers ran but specific claims could not be cross-referenced"
        else:
            status = "UNKNOWN"

        return VerificationResult(
            finding_id=f"{finding.agent}_{finding.dimension}",
            claim=finding.claim, status=status,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            verifier_notes=notes,
        )

    def verify_all(self, agent_results: list[AgentResult]) -> list[VerificationResult]:
        """Verify all findings from all agents."""
        results = []
        for agent_result in agent_results:
            for finding in agent_result.findings:
                vr = self.verify_finding(finding)
                results.append(vr)
        return results

    def compute_verification_rate(self, verifications: list[VerificationResult]) -> dict[str, float]:
        """Compute verification metrics."""
        total = len(verifications)
        if total == 0:
            return {"verification_rate": 0.0, "weighted_verification_rate": 0.0,
                    "contradiction_rate": 0.0, "unsupported_rate": 0.0}

        verified = sum(1 for v in verifications if v.status == "VERIFIED")
        partial = sum(1 for v in verifications if v.status == "PARTIALLY_VERIFIED")
        contradicted = sum(1 for v in verifications if v.status == "CONTRADICTED")
        unverified = sum(1 for v in verifications if v.status == "UNVERIFIED")
        unknown = sum(1 for v in verifications if v.status == "UNKNOWN")

        return {
            "verification_rate": round(verified / total, 3),
            "weighted_verification_rate": round((verified + 0.5 * partial) / total, 3),
            "contradiction_rate": round(contradicted / total, 3),
            "unsupported_rate": round((unverified + unknown) / total, 3),
            "total_findings": total,
            "verified": verified,
            "partially_verified": partial,
            "contradicted": contradicted,
            "unverified": unverified,
            "unknown": unknown,
        }
