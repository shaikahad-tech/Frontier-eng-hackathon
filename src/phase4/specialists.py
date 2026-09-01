"""Phase 4 — Specialist Agents (Structure, Test, CodeQuality, Maintenance)

Bonus-based scoring: each positive signal adds points from a base of 0.
This produces scores that span the full 0-10 range and correlate better
with ground truth quality assessments.
"""
from src.phase4.agents import (
    SpecialistAgent, AgentFinding, AgentResult, EvidenceCollector,
)


class StructureAgent(SpecialistAgent):
    AGENT_NAME = "structure_agent"
    DIMENSION = "structure"
    ALLOWED_ANALYZERS = ["repository_discovery", "documentation", "structure",
                         "config", "build", "api_analysis"]

    def evaluate(self) -> AgentResult:
        profile = self._profile()
        acc = 0.0
        mx = 0.0

        # Documentation (weight: 3)
        mx += 3.0
        doc_raw = self._get_raw_data("documentation")
        doc_score = self._get_metric("documentation", "documentation_score", 0)
        readme_info = doc_raw.get("readme", {})
        has_readme = readme_info.get("found", False) if isinstance(readme_info, dict) else False
        # Count README sections as primary quality signal (more reliable than raw doc_score)
        sections = sum(1 for k in ["has_install","has_usage","has_test","has_contribut","has_license","has_example"] if readme_info.get(k)) if isinstance(readme_info, dict) else 0
        has_license = doc_raw.get("license", {}).get("found", False) if isinstance(doc_raw.get("license"), dict) else False
        if has_readme and sections >= 5 and has_license:
            self._add_finding("Strong documentation with comprehensive README, license, and contributing guide",
                score=9.0, confidence=0.9, evidence=[{"type": "doc_sections", "value": sections}], sources=["documentation"])
            acc += 2.7
        elif has_readme and sections >= 3:
            val = min(7.5, 4.0 + sections * 0.6)
            self._add_finding(f"Good documentation ({sections} README sections)", score=val, confidence=0.85, sources=["documentation"])
            acc += val / 10.0 * 3.0
        elif has_readme and sections >= 1:
            val = min(5.0, 2.0 + sections * 0.5)
            self._add_finding(f"Basic documentation ({sections} README sections)", score=val, confidence=0.8, sources=["documentation"])
            acc += val / 10.0 * 3.0
        elif has_readme:
            # Has README but no standard sections — could be bloated/fake
            readme_len = readme_info.get("length_chars", 0) if isinstance(readme_info, dict) else 0
            if readme_len > 10000:
                self._add_finding(f"Large README ({readme_len} chars) but no standard sections — possible bloat", score=1.0, confidence=0.8, sources=["documentation"])
                acc += 0.3
            else:
                self._add_finding("Minimal README present", score=2.5, confidence=0.7, sources=["documentation"])
                acc += 0.75
        else:
            self._add_finding("No documentation found", score=0.5, confidence=0.9, sources=["documentation"])

        # Organization (weight: 2)
        mx += 2.0
        struct_raw = self._get_raw_data("structure")
        struct_score = self._get_metric("structure", "architecture_score", 0) or self._get_metric("structure", "structure_score", 0)
        if struct_score and struct_score >= 70:
            self._add_finding("Well-organized project structure", score=8.0, confidence=0.85, sources=["structure"])
            acc += 1.6
        elif struct_score and struct_score >= 50:
            self._add_finding("Adequate project organization", score=6.0, confidence=0.75, sources=["structure"])
            acc += 1.2
        elif struct_score and struct_score >= 30:
            self._add_finding("Basic project organization", score=4.0, confidence=0.7, sources=["structure"])
            acc += 0.8
        else:
            self._add_finding("Poor project organization", score=2.0, confidence=0.7, sources=["structure"])
            acc += 0.4

        # Packaging (weight: 2)
        mx += 2.0
        build_raw = self._get_raw_data("build")
        build_files = build_raw.get("build_files", [])
        if build_files:
            val = min(8.0, 5.0 + len(build_files) * 1.5)
            self._add_finding(f"Proper packaging with {', '.join(build_files[:3])}", score=val, confidence=0.85, sources=["build"])
            acc += val / 10.0 * 2.0
        else:
            self._add_finding("No build configuration detected", score=2.0, confidence=0.7, sources=["build"])
            acc += 0.4

        # Container (weight: 1.5)
        mx += 1.5
        container_raw = self._get_raw_data("container")
        has_dockerfile = container_raw.get("has_dockerfile", False)
        container_issues = container_raw.get("issues", 0)
        if has_dockerfile and container_issues == 0:
            self._add_finding("Docker configuration follows best practices", score=8.5, confidence=0.85, sources=["container"])
            acc += 1.275
        elif has_dockerfile:
            self._add_finding(f"Dockerfile present with {container_issues} issues", score=5.0, confidence=0.8, sources=["container"])
            acc += 0.75
        else:
            self._add_unknown("No container configuration to evaluate")

        # CI/CD (weight: 1.5)
        mx += 1.5
        cicd_raw = self._get_raw_data("cicd")
        has_ci = cicd_raw.get("has_ci", False)
        if has_ci:
            self._add_finding("CI/CD pipeline configured", score=7.5, confidence=0.85, sources=["cicd"])
            acc += 1.125
        else:
            self._add_finding("No CI/CD configuration", score=2.0, confidence=0.8, sources=["cicd"])
            acc += 0.3

        dim_score = min(10.0, (acc / mx * 10.0) if mx > 0 else 3.0)
        dim_conf = sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.3
        return AgentResult(agent_name=self.AGENT_NAME, dimension=self.DIMENSION, score=round(dim_score, 2),
            confidence=round(dim_conf, 3), findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3), unknowns=self.unknowns, metadata={"profile": profile})


class TestAgent(SpecialistAgent):
    AGENT_NAME = "test_agent"
    DIMENSION = "testing"
    ALLOWED_ANALYZERS = ["testing", "test_execution", "coverage"]

    def evaluate(self) -> AgentResult:
        acc = 0.0
        mx = 0.0

        # Test presence (weight: 3)
        mx += 3.0
        testing_raw = self._get_raw_data("testing")
        test_file_count = testing_raw.get("test_file_count", 0)
        test_function_count = testing_raw.get("test_function_count", 0)
        has_tests = test_file_count > 0 or test_function_count > 0
        test_count = test_function_count
        ratio = testing_raw.get("test_to_source_ratio", 0)
        if not has_tests or test_count == 0:
            self._add_finding("No meaningful tests found", score=0.0, confidence=0.95, evidence=[{"type": "test_count", "value": 0}], sources=["testing"])
        else:
            # Detect suspiciously high test-to-source ratio (meaningless tests)
            tests_without_assert = testing_raw.get("tests_without_assertions", 0)
            if ratio > 10.0 and tests_without_assert == 0 and test_count > 20:
                # Likely meaningless tests (e.g., all `assert True`)
                val = min(5.0, 2.0 + test_count * 0.05)
                self._add_finding(f"{test_count} tests but ratio {ratio:.1f} suggests low quality tests", score=val, confidence=0.7,
                    evidence=[{"type": "test_count", "value": test_count, "ratio": ratio}], sources=["testing"])
                acc += val / 10.0 * 3.0
            else:
                val = min(9.0, 4.0 + test_count * 0.4 + (1.0 if ratio > 0.5 else 0.5 if ratio > 0.2 else 0))
                self._add_finding(f"{test_count} tests detected (ratio: {ratio:.1f})", score=val, confidence=0.85,
                    evidence=[{"type": "test_count", "value": test_count, "ratio": ratio}], sources=["testing"])
                acc += val / 10.0 * 3.0

        # Test execution (weight: 4)
        mx += 4.0
        exec_raw = self._get_raw_data("test_execution")
        exec_score = self._get_metric("test_execution", "test_execution_score", None)
        passed = exec_raw.get("passed", 0)
        failed = exec_raw.get("failed", 0)
        errors = exec_raw.get("errors", 0)
        if exec_score is not None:
            if passed > 0 and failed == 0 and errors == 0:
                self._add_finding(f"All {passed} tests passing", score=9.5, confidence=1.0,
                    evidence=[{"passed": passed, "failed": failed}], sources=["test_execution"])
                acc += 3.8
            elif failed > 0:
                self._add_finding(f"{failed} tests failing out of {passed + failed}", score=1.5, confidence=1.0,
                    evidence=[{"passed": passed, "failed": failed}], sources=["test_execution"])
                acc += 0.6
            elif passed > 0 and failed == 0:
                self._add_finding(f"Tests pass ({passed} passed)", score=7.0, confidence=0.9, sources=["test_execution"])
                acc += 2.8
            else:
                # exec_score exists but no tests ran (score=30)
                # Don't penalize for inability to run in sandbox — give neutral score
                if has_tests:
                    self._add_finding("Tests present but not executed in environment", score=5.5, confidence=0.5, sources=["test_execution"])
                    acc += 2.2
        else:
            if has_tests:
                self._add_finding("Tests present but execution results not available", score=5.5, confidence=0.5, sources=["test_execution"])
                acc += 2.2
            else:
                self._add_unknown("Test execution results not available")

        # Coverage (weight: 2)
        mx += 2.0
        cov_raw = self._get_raw_data("coverage")
        cov_pct = cov_raw.get("coverage_pct")
        cov_score = self._get_metric("coverage", "coverage_score", None)
        if cov_pct is not None and cov_pct > 0:
            if cov_pct >= 80:
                self._add_finding(f"Excellent coverage: {cov_pct:.1f}%", score=9.5, confidence=1.0, sources=["coverage"])
                acc += 1.9
            elif cov_pct >= 50:
                self._add_finding(f"Adequate coverage: {cov_pct:.1f}%", score=6.5, confidence=0.9, sources=["coverage"])
                acc += 1.3
            else:
                self._add_finding(f"Low coverage: {cov_pct:.1f}%", score=3.0, confidence=0.9, sources=["coverage"])
                acc += 0.6
        elif cov_score is not None:
            self._add_finding(f"Coverage config present (score: {cov_score})", score=5.0, confidence=0.6, sources=["coverage"])
            acc += 1.0
        else:
            self._add_unknown("Coverage data not available")

        # CI (weight: 1)
        mx += 1.0
        cicd_raw = self._get_raw_data("cicd")
        has_ci = cicd_raw.get("has_ci", False)
        if has_ci:
            self._add_finding("CI pipeline present", score=6.0, confidence=0.7, sources=["cicd"])
            acc += 0.6
        else:
            self._add_unknown("CI enforcement unknown")

        dim_score = min(10.0, (acc / mx * 10.0) if mx > 0 else 1.0)
        dim_conf = sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2
        return AgentResult(agent_name=self.AGENT_NAME, dimension=self.DIMENSION, score=round(dim_score, 2),
            confidence=round(dim_conf, 3), findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3), unknowns=self.unknowns,
            metadata={"test_count": test_count, "passed": passed, "failed": failed})


class CodeQualityAgent(SpecialistAgent):
    AGENT_NAME = "code_quality_agent"
    DIMENSION = "code_quality"
    ALLOWED_ANALYZERS = ["complexity", "static_quality", "security", "secrets",
                         "dead_code", "duplication", "tech_debt", "performance",
                         "vulnerability", "error_handling"]

    def evaluate(self) -> AgentResult:
        acc = 0.0
        mx = 0.0

        # Complexity (weight: 2)
        mx += 2.0
        cx_raw = self._get_raw_data("complexity")
        cx_score = self._get_metric("complexity", "complexity_score", None) or self._get_metric("complexity", "maintainability_score", None)
        avg_complexity = cx_raw.get("avg", 0)
        if cx_score is not None:
            if cx_score >= 80 and avg_complexity > 1.0:
                self._add_finding("Low code complexity", score=8.5, confidence=0.85, sources=["complexity"])
                acc += 1.7
            elif cx_score >= 80 and avg_complexity <= 1.0:
                # Trivially simple code (just pass/return) — not real quality
                self._add_finding("Suspiciously low complexity — code may be trivial or empty", score=2.0, confidence=0.7, sources=["complexity"])
                acc += 0.4
            elif cx_score >= 60:
                self._add_finding("Moderate code complexity", score=6.0, confidence=0.8, sources=["complexity"])
                acc += 1.2
            else:
                self._add_finding("High code complexity", score=3.0, confidence=0.85, sources=["complexity"])
                acc += 0.6
        else:
            self._add_unknown("Complexity data not available")

        # Static analysis (weight: 1.5)
        mx += 1.5
        static_score = self._get_metric("static_quality", "static_quality_score", None)
        linters = self._get_raw_data("static_quality").get("linters", [])
        ruff_errors = self._get_raw_data("static_quality").get("ruff_errors", 0)
        if static_score is not None:
            if linters and ruff_errors == 0:
                self._add_finding(f"Linters configured ({', '.join(linters)}), no errors", score=8.5, confidence=0.9, sources=["static_quality"])
                acc += 1.275
            elif linters and ruff_errors > 0:
                self._add_finding(f"Linters configured but {ruff_errors} issues", score=5.0, confidence=0.85, sources=["static_quality"])
                acc += 0.75
            else:
                self._add_finding("No static analysis configured", score=3.5, confidence=0.7, sources=["static_quality"])
                acc += 0.525

        # Security (weight: 2.5)
        mx += 2.5
        sec_findings = self._get_findings("security")
        secrets_findings = self._get_findings("secrets")
        vuln_findings = self._get_findings("vulnerability")
        critical = [f for f in sec_findings + secrets_findings + vuln_findings if f.get("severity") in ("critical", "high", "CRITICAL", "HIGH")]
        if critical:
            self._add_finding(f"{len(critical)} critical/high security findings", score=0.5, confidence=0.95,
                evidence=[{"type": "security_findings", "count": len(critical)}], sources=["security", "secrets", "vulnerability"])
            acc += 0.125
        elif sec_findings or vuln_findings:
            self._add_finding("Minor security findings detected", score=5.5, confidence=0.8, sources=["security", "vulnerability"])
            acc += 1.375
        else:
            self._add_finding("No security issues detected", score=8.5, confidence=0.75, sources=["security"])
            acc += 2.125

        # Duplication (weight: 1)
        mx += 1.0
        dup_score = self._get_metric("duplication", "duplication_score", None)
        if dup_score is not None:
            if dup_score >= 80:
                self._add_finding("Low code duplication", score=8.0, confidence=0.8, sources=["duplication"])
                acc += 0.8
            elif dup_score < 50:
                self._add_finding("High code duplication", score=3.0, confidence=0.8, sources=["duplication"])
                acc += 0.3
            else:
                acc += 0.5

        # Dead code (weight: 1)
        mx += 1.0
        dead_score = self._get_metric("dead_code", "dead_code_score", None)
        if dead_score is not None:
            if dead_score >= 80:
                self._add_finding("Minimal dead code", score=8.0, confidence=0.8, sources=["dead_code"])
                acc += 0.8
            elif dead_score < 50:
                self._add_finding("Significant dead code detected", score=4.0, confidence=0.8, sources=["dead_code"])
                acc += 0.4
            else:
                acc += 0.5

        # Tech debt (weight: 1)
        mx += 1.0
        debt_score = self._get_metric("tech_debt", "tech_debt_score", None)
        if debt_score is not None:
            if debt_score >= 70:
                self._add_finding("Low technical debt", score=8.0, confidence=0.8, sources=["tech_debt"])
                acc += 0.8
            elif debt_score < 40:
                self._add_finding("High technical debt", score=3.0, confidence=0.85, sources=["tech_debt"])
                acc += 0.3
            else:
                acc += 0.5

        dim_score = min(10.0, (acc / mx * 10.0) if mx > 0 else 3.0)
        # If code is trivially simple (avg complexity <= 1.0), cap the overall quality score
        # because dead_code/tech_debt/duplication scores are meaningless on empty code
        if avg_complexity <= 1.0 and cx_score is not None and cx_score >= 80:
            dim_score = min(dim_score, 4.0)
        dim_conf = sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2
        return AgentResult(agent_name=self.AGENT_NAME, dimension=self.DIMENSION, score=round(dim_score, 2),
            confidence=round(dim_conf, 3), findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3), unknowns=self.unknowns)


class MaintenanceAgent(SpecialistAgent):
    AGENT_NAME = "maintenance_agent"
    DIMENSION = "maintenance"
    ALLOWED_ANALYZERS = ["git", "release", "reproducibility"]

    def evaluate(self) -> AgentResult:
        acc = 0.0
        mx = 0.0

        # Git history (weight: 3)
        mx += 3.0
        git_raw = self._get_raw_data("git")
        git_score = self._get_metric("git", "git_score", None) or self._get_metric("git", "git_maturity_score", None)
        commit_count = git_raw.get("total_commits", git_raw.get("commit_count", 0))
        contributor_count = git_raw.get("contributor_count", 0)
        if git_score is not None:
            if git_score >= 70:
                self._add_finding("Healthy Git maintenance history", score=8.0, confidence=0.85, sources=["git"])
                acc += 2.4
            elif git_score >= 50:
                self._add_finding("Moderate Git maintenance", score=7.0, confidence=0.8, sources=["git"])
                acc += 2.1
            elif git_score >= 30:
                self._add_finding("Repository has Git history", score=5.5, confidence=0.7, sources=["git"])
                acc += 1.65
            else:
                self._add_finding("Limited Git history", score=3.5, confidence=0.7, sources=["git"])
                acc += 1.05
        else:
            self._add_unknown("Git history not available")

        # Contributors (weight: 1)
        mx += 1.0
        if commit_count > 0:
            if contributor_count >= 3:
                self._add_finding(f"Active development with {contributor_count} contributors", score=8.0, confidence=0.8, sources=["git"])
                acc += 0.8
            elif contributor_count == 1:
                self._add_finding("Single maintainer — evaluate continuity", score=5.5, confidence=0.6,
                    evidence=[{"commit_count": commit_count, "contributors": 1}], sources=["git"])
                acc += 0.55
            else:
                acc += 0.6

        # Release (weight: 2)
        mx += 2.0
        rel_raw = self._get_raw_data("release")
        rel_score = self._get_metric("release", "release_score", None)
        tag_count = rel_raw.get("tag_count", 0)
        has_changelog = rel_raw.get("has_changelog", False)
        pkg_version = rel_raw.get("package_version", "")
        if rel_score is not None:
            if tag_count > 0 and has_changelog:
                self._add_finding(f"Proper release management ({tag_count} tags, changelog)", score=8.5, confidence=0.85, sources=["release"])
                acc += 1.7
            elif tag_count > 0:
                self._add_finding(f"Has {tag_count} release tags", score=6.5, confidence=0.8, sources=["release"])
                acc += 1.3
            elif pkg_version:
                self._add_finding(f"Versioned package ({pkg_version})", score=5.0, confidence=0.7, sources=["release"])
                acc += 1.0
            else:
                self._add_finding("No release tags", score=2.5, confidence=0.7, sources=["release"])
                acc += 0.5
        else:
            if pkg_version:
                self._add_finding(f"Versioned package ({pkg_version})", score=4.5, confidence=0.6, sources=["release"])
                acc += 0.9

        # Reproducibility (weight: 2)
        mx += 2.0
        repro_raw = self._get_raw_data("reproducibility")
        repro_score = self._get_metric("reproducibility", "reproducibility_score", None)
        has_lockfile = repro_raw.get("has_lockfile", False)
        if repro_score is not None:
            if repro_score >= 70:
                self._add_finding("Good reproducibility setup", score=8.0, confidence=0.8, sources=["reproducibility"])
                acc += 1.6
            elif repro_score >= 40:
                self._add_finding("Moderate reproducibility", score=5.0, confidence=0.7, sources=["reproducibility"])
                acc += 1.0
            else:
                build_raw = self._get_raw_data("build")
                build_files = build_raw.get("build_files", [])
                if build_files:
                    self._add_finding("Build configuration present but no lockfile", score=3.5, confidence=0.7, sources=["reproducibility"])
                    acc += 0.7
                else:
                    self._add_finding("Poor reproducibility", score=2.0, confidence=0.8, sources=["reproducibility"])
                    acc += 0.4
        else:
            self._add_unknown("Reproducibility data not available")

        dim_score = min(10.0, (acc / mx * 10.0) if mx > 0 else 3.0)
        dim_conf = sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2
        return AgentResult(agent_name=self.AGENT_NAME, dimension=self.DIMENSION, score=round(dim_score, 2),
            confidence=round(dim_conf, 3), findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3), unknowns=self.unknowns,
            metadata={"commit_count": commit_count, "contributors": contributor_count})
