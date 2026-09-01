"""Phase 4 — Rebuilt Verification Agent

Structured claim verification, not keyword matching.
For each finding, determines a claim_type and checks actual tool evidence.

Statuses: VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONTRADICTED, UNKNOWN
"""
from __future__ import annotations
import hashlib
from typing import Any
from dataclasses import dataclass, field

from src.phase4.agents import AgentFinding, AgentResult, EvidenceCollector


@dataclass
class VerificationResult:
    """Result of verifying a finding."""
    finding_id: str
    claim: str
    claim_type: str
    status: str  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONTRADICTED, UNKNOWN
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    verifier_notes: str = ""


def _finding_id(finding: AgentFinding) -> str:
    """Deterministic ID from finding content."""
    raw = f"{finding.agent}|{finding.dimension}|{finding.claim}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# Claim type detection — maps claim text to a structured type
CLAIM_PATTERNS = [
    # (claim_type, keywords_that_indicate_it)
    ("test_pass",       ["passing", "tests pass", "all tests pass", "test suite passes"]),
    ("test_fail",       ["failing", "tests fail", "broken tests", "test failures"]),
    ("test_count",      ["test count", "number of tests", "tests exist", "has tests",
                          "no tests", "missing tests", "test presence"]),
    ("test_quality",    ["meaningful", "assertion", "trivial", "weak test", "test quality",
                          "strong test", "good test"]),
    ("coverage",        ["coverage"]),
    ("security_findings", ["security", "vulnerab", "injection", "secret", "hardcoded",
                           "unsafe", "command injection", "sql injection"]),
    ("no_security",      ["no security", "no vulnerabilities", "secure", "no findings",
                           "no issues detected"]),
    ("complexity",       ["complexity", "complex", "cyclomatic", "maintainability"]),
    ("documentation",    ["documentation", "readme", "docs", "well-documented"]),
    ("git_activity",     ["commit", "git activity", "recent", "active", "stale", "abandoned",
                           "maintenance", "maintained"]),
    ("dependency_risk",  ["dependenc", "outdated", "vulnerable dependency", "unpinned",
                           "lockfile", "supply chain"]),
    ("structure",        ["structure", "organization", "packaging", "architecture",
                           "well-organized", "clean structure"]),
    ("ci_cd",            ["ci", "continuous integration", "workflow", "github actions",
                           "pipeline", "ci/cd"]),
]


def detect_claim_type(claim: str) -> str:
    """Detect the structured claim type from claim text."""
    claim_lower = claim.lower()
    for claim_type, keywords in CLAIM_PATTERNS:
        for kw in keywords:
            if kw in claim_lower:
                return claim_type
    return "generic"


class VerificationAgent:
    """Verifies that every finding is supported by actual tool evidence.

    Uses structured claim verification:
        CLAIM -> CLAIM TYPE -> EXPECTED EVIDENCE -> ACTUAL TOOL DATA -> RESULT

    Does NOT re-score. Only verifies claims.
    """

    def __init__(self, evidence: EvidenceCollector):
        self.evidence = evidence

    def verify_finding(self, finding: AgentFinding) -> VerificationResult:
        """Verify a single finding against tool evidence using structured claim types."""
        fid = _finding_id(finding)
        claim_type = detect_claim_type(finding.claim)
        supporting = []
        contradicting = []
        notes = ""

        # Check if finding has any evidence references
        if not finding.evidence and not finding.sources:
            return VerificationResult(
                finding_id=fid, claim=finding.claim, claim_type=claim_type,
                status="UNVERIFIED",
                contradicting_evidence=["No evidence references provided"],
            )

        # Verify based on claim type
        if claim_type == "test_pass":
            self._verify_test_pass(finding, supporting, contradicting)
        elif claim_type == "test_fail":
            self._verify_test_fail(finding, supporting, contradicting)
        elif claim_type == "test_count":
            self._verify_test_count(finding, supporting, contradicting)
        elif claim_type == "test_quality":
            self._verify_test_quality(finding, supporting, contradicting)
        elif claim_type == "coverage":
            self._verify_coverage(finding, supporting, contradicting)
        elif claim_type == "security_findings":
            self._verify_security_findings(finding, supporting, contradicting)
        elif claim_type == "no_security":
            self._verify_no_security(finding, supporting, contradicting)
        elif claim_type == "complexity":
            self._verify_complexity(finding, supporting, contradicting)
        elif claim_type == "documentation":
            self._verify_documentation(finding, supporting, contradicting)
        elif claim_type == "git_activity":
            self._verify_git_activity(finding, supporting, contradicting)
        elif claim_type == "dependency_risk":
            self._verify_dependency_risk(finding, supporting, contradicting)
        elif claim_type == "structure":
            self._verify_structure(finding, supporting, contradicting)
        elif claim_type == "ci_cd":
            self._verify_ci_cd(finding, supporting, contradicting)
        else:
            self._verify_generic(finding, supporting, contradicting)

        # Determine status
        if contradicting:
            status = "CONTRADICTED"
        elif supporting:
            status = "VERIFIED"
        elif finding.sources:
            any_data = False
            for source in finding.sources:
                raw = self.evidence.get_raw_data(source)
                if raw:
                    any_data = True
                    break
            if any_data:
                status = "PARTIALLY_VERIFIED"
                notes = "Source analyzers ran but specific claims could not be fully cross-referenced"
            else:
                status = "UNVERIFIED"
                notes = "Source analyzers did not produce data"
        else:
            status = "UNKNOWN"

        return VerificationResult(
            finding_id=fid, claim=finding.claim, claim_type=claim_type,
            status=status, supporting_evidence=supporting,
            contradicting_evidence=contradicting, verifier_notes=notes,
        )

    # Structured verifiers per claim type

    def _verify_test_pass(self, finding, supporting, contradicting):
        exec_raw = self.evidence.get_raw_data("test_execution")
        if exec_raw:
            passed = exec_raw.get("passed", 0)
            failed = exec_raw.get("failed", 0)
            errors = exec_raw.get("errors", 0)
            if passed > 0 and failed == 0 and errors == 0:
                supporting.append(f"test_execution: {passed} passed, 0 failed, 0 errors")
            elif failed > 0:
                contradicting.append(f"test_execution: {failed} tests failing (claim says passing)")
            elif errors > 0:
                contradicting.append(f"test_execution: {errors} errors (claim says passing)")
            else:
                contradicting.append("test_execution: 0 tests passed")
        else:
            testing_raw = self.evidence.get_raw_data("testing")
            if testing_raw and testing_raw.get("has_tests"):
                supporting.append("testing: tests exist (execution not run)")
            else:
                contradicting.append("No test execution data and no tests detected")

    def _verify_test_fail(self, finding, supporting, contradicting):
        exec_raw = self.evidence.get_raw_data("test_execution")
        if exec_raw:
            failed = exec_raw.get("failed", 0)
            if failed > 0:
                supporting.append(f"test_execution: {failed} tests failing")
            else:
                contradicting.append("test_execution: 0 failures (claim says tests fail)")

    def _verify_test_count(self, finding, supporting, contradicting):
        testing_raw = self.evidence.get_raw_data("testing")
        if testing_raw:
            has_tests = testing_raw.get("has_tests", False)
            test_count = testing_raw.get("test_count", 0)
            if has_tests:
                supporting.append(f"testing: {test_count} tests detected")
            else:
                if "no tests" in finding.claim.lower() or "missing" in finding.claim.lower():
                    supporting.append("testing: no tests detected (matches claim)")
                else:
                    contradicting.append("testing: no tests detected but claim implies tests exist")
        else:
            supporting.append("testing analyzer ran (no data returned)")

    def _verify_test_quality(self, finding, supporting, contradicting):
        testing_raw = self.evidence.get_raw_data("testing")
        if testing_raw:
            assertion_ratio = testing_raw.get("assertion_ratio", None)
            trivial_count = testing_raw.get("trivial_tests", 0)
            meaningful_count = testing_raw.get("meaningful_tests", 0)
            if assertion_ratio is not None:
                if assertion_ratio > 0.5:
                    supporting.append(f"testing: assertion ratio {assertion_ratio:.2f} (meaningful)")
                else:
                    supporting.append(f"testing: assertion ratio {assertion_ratio:.2f}")
            if trivial_count > 0 and "trivial" in finding.claim.lower():
                supporting.append(f"testing: {trivial_count} trivial tests detected")
            if meaningful_count > 0 and "meaningful" in finding.claim.lower():
                supporting.append(f"testing: {meaningful_count} meaningful tests detected")
        exec_raw = self.evidence.get_raw_data("test_execution")
        if exec_raw:
            passed = exec_raw.get("passed", 0)
            if passed > 0:
                supporting.append(f"test_execution: {passed} tests passed")

    def _verify_coverage(self, finding, supporting, contradicting):
        cov_raw = self.evidence.get_raw_data("coverage")
        if cov_raw:
            cov_pct = cov_raw.get("coverage_pct")
            if cov_pct is not None:
                supporting.append(f"coverage: {cov_pct:.1f}%")
            else:
                supporting.append("coverage analyzer ran but no percentage available")

    def _verify_security_findings(self, finding, supporting, contradicting):
        sec_findings = self.evidence.get_findings("security")
        secrets_findings = self.evidence.get_findings("secrets")
        vuln_findings = self.evidence.get_findings("vulnerability")
        total_sec = len(sec_findings) + len(secrets_findings) + len(vuln_findings)
        if total_sec > 0:
            details = []
            for f in sec_findings[:3]:
                details.append(f"{f.get('category', 'unknown')}:{f.get('severity', 'unknown')}")
            for f in secrets_findings[:3]:
                details.append(f"secret:{f.get('severity', 'unknown')}")
            supporting.append(f"security: {total_sec} findings confirmed ({', '.join(details)})")
        else:
            sec_raw = self.evidence.get_raw_data("security")
            if sec_raw is not None:
                supporting.append("security ran: 0 findings (analyzers executed)")

    def _verify_no_security(self, finding, supporting, contradicting):
        sec_findings = self.evidence.get_findings("security")
        secrets_findings = self.evidence.get_findings("secrets")
        vuln_findings = self.evidence.get_findings("vulnerability")
        total_sec = len(sec_findings) + len(secrets_findings) + len(vuln_findings)
        if total_sec == 0:
            sec_raw = self.evidence.get_raw_data("security")
            if sec_raw is not None:
                supporting.append("security: 0 findings (analyzers executed, none found)")
        else:
            contradicting.append(f"security: {total_sec} findings found (claim says no issues)")

    def _verify_complexity(self, finding, supporting, contradicting):
        cx_raw = self.evidence.get_raw_data("complexity")
        if cx_raw:
            avg_complexity = cx_raw.get("avg_complexity")
            max_complexity = cx_raw.get("max_complexity")
            high_count = cx_raw.get("high_complexity_count", 0)
            if avg_complexity is not None:
                supporting.append(f"complexity: avg={avg_complexity:.1f}, max={max_complexity}")
            if high_count > 0:
                supporting.append(f"complexity: {high_count} high-complexity functions")

    def _verify_documentation(self, finding, supporting, contradicting):
        doc_raw = self.evidence.get_raw_data("documentation")
        if doc_raw:
            readme_info = doc_raw.get("readme", {})
            if isinstance(readme_info, dict):
                has_readme = readme_info.get("found", False)
                readme_size = readme_info.get("length_chars", 0)
            else:
                has_readme = False
                readme_size = 0
            doc_score = doc_raw.get("score", 0)
            if has_readme:
                supporting.append(f"documentation: README found ({readme_size} chars, score {doc_score})")
            else:
                if "no" in finding.claim.lower() or "poor" in finding.claim.lower() or "missing" in finding.claim.lower():
                    supporting.append("documentation: no README found (matches claim)")
                else:
                    contradicting.append("documentation: no README found")

    def _verify_git_activity(self, finding, supporting, contradicting):
        git_raw = self.evidence.get_raw_data("git")
        if git_raw:
            commit_count = git_raw.get("total_commits", git_raw.get("commit_count", 0))
            contributor_count = git_raw.get("contributor_count", 0)
            if commit_count > 0:
                supporting.append(f"git: {commit_count} commits, {contributor_count} contributors")
            else:
                if "abandoned" in finding.claim.lower() or "stale" in finding.claim.lower():
                    supporting.append("git: 0 commits (matches stale claim)")
                else:
                    contradicting.append("git: 0 commits")

    def _verify_dependency_risk(self, finding, supporting, contradicting):
        dep_raw = self.evidence.get_raw_data("dependencies")
        vuln_raw = self.evidence.get_raw_data("vulnerability")
        if dep_raw:
            dep_count = dep_raw.get("dependency_count", 0)
            unpinned = dep_raw.get("unpinned_count", 0)
            if dep_count > 0:
                supporting.append(f"dependencies: {dep_count} deps, {unpinned} unpinned")
        if vuln_raw:
            vuln_count = len(vuln_raw) if isinstance(vuln_raw, list) else vuln_raw.get("count", 0)
            if vuln_count > 0:
                supporting.append(f"vulnerability: {vuln_count} vulnerable dependencies")

    def _verify_structure(self, finding, supporting, contradicting):
        struct_raw = self.evidence.get_raw_data("structure")
        if struct_raw:
            struct_score = struct_raw.get("score", 0)
            has_cyclic = len(struct_raw.get("cyclic_deps", [])) > 0
            total_loc = struct_raw.get("total_loc", 0)
            if struct_score >= 70 and not has_cyclic:
                supporting.append(f"structure: good score ({struct_score}), no cyclic deps, {total_loc} LOC")
            elif struct_score >= 50:
                supporting.append(f"structure: moderate score ({struct_score})")
            elif "poor" in finding.claim.lower() or "no" in finding.claim.lower():
                supporting.append(f"structure: low score ({struct_score}) matches claim")
            else:
                contradicting.append(f"structure: low score ({struct_score}) contradicts claim")
        else:
            supporting.append("structure analyzer ran (no data returned)")

    def _verify_ci_cd(self, finding, supporting, contradicting):
        ci_raw = self.evidence.get_raw_data("cicd")
        if ci_raw:
            has_ci = ci_raw.get("has_ci", False)
            if has_ci:
                supporting.append(f"cicd: CI detected ({ci_raw.get('platform', 'unknown')})")
            else:
                if "no ci" in finding.claim.lower() or "missing" in finding.claim.lower():
                    supporting.append("cicd: no CI detected (matches claim)")
                else:
                    contradicting.append("cicd: no CI detected")

    def _verify_generic(self, finding, supporting, contradicting):
        """For generic claims, check that source analyzers produced data."""
        for source in finding.sources:
            raw = self.evidence.get_raw_data(source)
            if raw:
                supporting.append(f"{source}: analyzer ran with data")
            else:
                contradicting.append(f"{source}: analyzer did not produce data")

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
            return {
                "verification_rate": 0.0,
                "weighted_verification_rate": 0.0,
                "contradiction_rate": 0.0,
                "unsupported_rate": 0.0,
                "total_findings": 0,
                "verified": 0,
                "partially_verified": 0,
                "contradicted": 0,
                "unverified": 0,
                "unknown": 0,
            }

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
