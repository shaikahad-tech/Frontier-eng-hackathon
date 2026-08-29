"""Phase 4 — Specialist Agents (Structure, Test, CodeQuality, Maintenance)

Each agent is scope-limited to specific analyzers and operates from actual
Phase 2 tool output, not invented facts.

Agents:
  - StructureAgent: README, organization, packaging, Docker, architecture (weight: 20%)
  - TestAgent: test presence, execution, coverage, CI enforcement (weight: 25%)
  - CodeQualityAgent: complexity, static analysis, security, duplication, dead code, tech debt (weight: 25%)
  - MaintenanceAgent: git history, activity, releases, reproducibility (weight: 15%)
"""
from src.phase4.agents import (
    SpecialistAgent, AgentFinding, AgentResult, EvidenceCollector,
)


class StructureAgent(SpecialistAgent):
    """Evaluates documentation quality, organization, packaging, deployment."""

    AGENT_NAME = "structure_agent"
    DIMENSION = "structure"
    ALLOWED_ANALYZERS = ["repository_discovery", "documentation", "structure",
                         "config", "build_packaging", "api_analysis"]

    def evaluate(self) -> AgentResult:
        profile = self._profile()
        discovery = self._get_context().get("discovery", {})

        # ── Documentation quality ──
        doc_raw = self._get_raw_data("documentation")
        doc_score = self._get_metric("documentation", "documentation_score", 50)

        if doc_score and doc_score >= 70:
            self._add_finding("Strong documentation with comprehensive README",
                score=8.0, confidence=0.9,
                evidence=[{"type": "documentation_analyzer", "score": doc_score}],
                sources=["documentation"])
        elif doc_score and doc_score >= 50:
            self._add_finding("Adequate documentation",
                score=6.0, confidence=0.8,
                evidence=[{"type": "documentation_score", "value": doc_score}],
                sources=["documentation"])
        elif doc_score and doc_score < 30:
            self._add_finding("Poor or missing documentation",
                score=2.0, confidence=0.9,
                evidence=[{"type": "documentation_score", "value": doc_score}],
                sources=["documentation"])
        else:
            self._add_unknown("Documentation quality could not be determined")

        # ── Project organization ──
        struct_raw = self._get_raw_data("structure")
        struct_score = self._get_metric("structure", "structure_score", 50)
        has_src = struct_raw.get("has_src_dir", False)
        has_tests = struct_raw.get("has_tests_dir", False)

        if struct_score and struct_score >= 70:
            org_claim = "Well-organized project structure"
            if has_src and has_tests:
                org_claim += " with clear src/tests separation"
            self._add_finding(org_claim, score=8.0, confidence=0.85,
                            evidence=[{"type": "structure_score", "value": struct_score}],
                            sources=["structure"])
        elif struct_score and struct_score >= 50:
            self._add_finding("Basic project organization", score=5.0, confidence=0.7,
                            evidence=[{"type": "structure_score", "value": struct_score}],
                            sources=["structure"])
        else:
            self._add_finding("Poor project organization", score=3.0, confidence=0.7,
                            sources=["structure"])

        # ── Packaging quality ──
        build_raw = self._get_raw_data("build_packaging")
        build_files = build_raw.get("build_files", [])

        if build_files:
            self._add_finding(f"Proper packaging with {', '.join(build_files[:3])}",
                score=7.0, confidence=0.85,
                evidence=[{"type": "build_files", "value": build_files}],
                sources=["build_packaging"])
        else:
            self._add_finding("No build configuration detected", score=3.0, confidence=0.7,
                            sources=["build_packaging"])

        # ── Deployment readiness ──
        container_raw = self._get_raw_data("container")
        has_dockerfile = container_raw.get("has_dockerfile", False)
        container_issues = container_raw.get("issues", 0)

        if has_dockerfile and container_issues == 0:
            self._add_finding("Docker configuration follows best practices", score=8.0,
                            confidence=0.85, sources=["container"])
        elif has_dockerfile and container_issues <= 3:
            self._add_finding(f"Dockerfile present with {container_issues} minor issues",
                            score=6.0, confidence=0.8, sources=["container"])
        elif has_dockerfile:
            self._add_finding(f"Dockerfile present but has {container_issues} issues",
                            score=4.0, confidence=0.85, sources=["container"])
        else:
            self._add_unknown("No container configuration to evaluate")

        # ── Architecture signals ──
        api_raw = self._get_raw_data("api_analysis")
        route_count = api_raw.get("routes", 0)

        if profile in ("API", "WEB_APP", "BACKEND_SERVICE") and route_count > 0:
            has_openapi = api_raw.get("has_openapi", False)
            if has_openapi:
                self._add_finding("API has OpenAPI/Swagger documentation", score=8.0,
                                confidence=0.9, sources=["api_analysis"])
            else:
                self._add_finding(f"API has {route_count} routes but no OpenAPI spec",
                                score=4.0, confidence=0.85, sources=["api_analysis"])

        scores = [f.score for f in self.findings]
        dim_score = sum(scores) / len(scores) if scores else 5.0
        dim_confidence = sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.3

        return AgentResult(
            agent_name=self.AGENT_NAME, dimension=self.DIMENSION,
            score=round(min(10.0, dim_score), 2),
            confidence=round(dim_confidence, 3),
            findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3),
            unknowns=self.unknowns, metadata={"profile": profile})


class TestAgent(SpecialistAgent):
    """Evaluates test presence, execution, coverage, and quality."""

    AGENT_NAME = "test_agent"
    DIMENSION = "testing"
    ALLOWED_ANALYZERS = ["testing", "test_execution", "coverage"]

    def evaluate(self) -> AgentResult:
        testing_raw = self._get_raw_data("testing")
        has_tests = testing_raw.get("has_tests", False)
        test_count = testing_raw.get("test_count", 0)
        test_frameworks = testing_raw.get("frameworks", [])

        if not has_tests or test_count == 0:
            self._add_finding("No meaningful tests found", score=0.0, confidence=0.95,
                            evidence=[{"type": "test_count", "value": 0}],
                            sources=["testing"])
        elif test_count > 0:
            self._add_finding(
                f"{test_count} tests detected using {', '.join(test_frameworks) or 'unknown framework'}",
                score=min(6.0, 2.0 + test_count * 0.3), confidence=0.8,
                evidence=[{"type": "test_count", "value": test_count}],
                sources=["testing"])

        exec_raw = self._get_raw_data("test_execution")
        exec_score = self._get_metric("test_execution", "test_execution_score", None)
        passed = exec_raw.get("passed", 0)
        failed = exec_raw.get("failed", 0)
        errors = exec_raw.get("errors", 0)

        if exec_score is not None:
            if passed > 0 and failed == 0 and errors == 0:
                self._add_finding(f"All {passed} tests passing", score=9.0, confidence=1.0,
                    evidence=[{"passed": passed, "failed": failed, "errors": errors}],
                    sources=["test_execution"])
            elif failed > 0:
                self._add_finding(f"{failed} tests failing out of {passed + failed}", score=2.0,
                    confidence=1.0, evidence=[{"passed": passed, "failed": failed}],
                    sources=["test_execution"])
            elif passed > 0 and failed == 0:
                self._add_finding(f"Tests pass ({passed} passed)", score=7.0, confidence=0.9,
                    sources=["test_execution"])
        else:
            self._add_unknown("Test execution results not available")

        cov_raw = self._get_raw_data("coverage")
        cov_pct = cov_raw.get("coverage_pct")
        cov_score = self._get_metric("coverage", "coverage_score", None)

        if cov_pct is not None:
            if cov_pct >= 80:
                self._add_finding(f"Excellent coverage: {cov_pct:.1f}%", score=9.0, confidence=1.0, sources=["coverage"])
            elif cov_pct >= 50:
                self._add_finding(f"Adequate coverage: {cov_pct:.1f}%", score=6.0, confidence=0.9, sources=["coverage"])
            else:
                self._add_finding(f"Low coverage: {cov_pct:.1f}%", score=3.0, confidence=0.9, sources=["coverage"])
        elif cov_score is not None:
            self._add_finding(f"Coverage config present (score: {cov_score})", score=5.0, confidence=0.6, sources=["coverage"])
        else:
            self._add_unknown("Coverage data not available")

        cicd_raw = self._get_raw_data("cicd")
        has_ci = cicd_raw.get("has_ci", False)
        ci_runs_tests = cicd_raw.get("runs_tests", False)

        if has_ci and ci_runs_tests:
            self._add_finding("CI pipeline enforces tests", score=8.0, confidence=0.85, sources=["cicd"])
        elif has_ci:
            self._add_finding("CI present but test enforcement unclear", score=5.0, confidence=0.5, sources=["cicd"])
        else:
            self._add_unknown("CI enforcement unknown")

        if self.findings:
            weighted_sum = 0; total_weight = 0
            for f in self.findings:
                w = 2.0 if "test_execution" in str(f.sources) else 1.0
                weighted_sum += f.score * w; total_weight += w
            dim_score = weighted_sum / total_weight if total_weight else 5.0
        else:
            dim_score = 2.0
            self._add_finding("No test evidence available", score=2.0, confidence=0.3)

        dim_confidence = (sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2)

        return AgentResult(
            agent_name=self.AGENT_NAME, dimension=self.DIMENSION,
            score=round(min(10.0, dim_score), 2),
            confidence=round(dim_confidence, 3),
            findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3),
            unknowns=self.unknowns,
            metadata={"test_count": test_count, "passed": passed, "failed": failed})


class CodeQualityAgent(SpecialistAgent):
    """Evaluates complexity, maintainability, static analysis, security, tech debt."""

    AGENT_NAME = "code_quality_agent"
    DIMENSION = "code_quality"
    ALLOWED_ANALYZERS = ["complexity", "static_quality", "security_sast", "secrets",
                         "dead_code", "duplication", "tech_debt", "performance",
                         "vulnerability", "error_handling"]

    def evaluate(self) -> AgentResult:
        complexity_score = self._get_metric("complexity", "complexity_score", None)

        if complexity_score is not None:
            if complexity_score >= 80:
                self._add_finding("Low code complexity", score=8.0, confidence=0.85, sources=["complexity"])
            elif complexity_score >= 60:
                self._add_finding("Moderate code complexity", score=6.0, confidence=0.8, sources=["complexity"])
            else:
                self._add_finding("High code complexity — maintenance risk", score=3.0, confidence=0.85, sources=["complexity"])
        else:
            self._add_unknown("Complexity data not available")

        static_score = self._get_metric("static_quality", "static_quality_score", None)
        linters = self._get_raw_data("static_quality").get("linters", [])
        ruff_errors = self._get_raw_data("static_quality").get("ruff_errors", 0)

        if static_score is not None:
            if linters and ruff_errors == 0:
                self._add_finding(f"Linters configured ({', '.join(linters)}), no errors", score=8.0, confidence=0.9, sources=["static_quality"])
            elif linters and ruff_errors > 0:
                self._add_finding(f"Linters configured but {ruff_errors} issues found", score=5.0, confidence=0.85, sources=["static_quality"])
            else:
                self._add_finding("No static analysis configured", score=3.0, confidence=0.8, sources=["static_quality"])

        security_findings = self._get_findings("security_sast")
        secrets_findings = self._get_findings("secrets")
        vuln_findings = self._get_findings("vulnerability")

        critical_security = [f for f in security_findings + secrets_findings + vuln_findings
                            if f.get("severity") in ("critical", "high")]
        if critical_security:
            self._add_finding(f"{len(critical_security)} critical/high security findings",
                score=1.0, confidence=0.95,
                evidence=[{"type": "security_findings", "count": len(critical_security)}],
                sources=["security_sast", "secrets", "vulnerability"])
        elif security_findings or vuln_findings:
            self._add_finding("Minor security findings detected", score=6.0, confidence=0.8,
                            sources=["security_sast", "vulnerability"])
        else:
            self._add_finding("No security issues detected", score=8.0, confidence=0.7,
                            sources=["security_sast"])

        dup_score = self._get_metric("duplication", "duplication_score", None)
        if dup_score is not None:
            if dup_score >= 80:
                self._add_finding("Low code duplication", score=8.0, confidence=0.8, sources=["duplication"])
            elif dup_score < 50:
                self._add_finding("High code duplication", score=3.0, confidence=0.8, sources=["duplication"])

        dead_score = self._get_metric("dead_code", "dead_code_score", None)
        if dead_score is not None:
            if dead_score >= 80:
                self._add_finding("Minimal dead code", score=8.0, confidence=0.8, sources=["dead_code"])
            elif dead_score < 50:
                self._add_finding("Significant dead code detected", score=4.0, confidence=0.8, sources=["dead_code"])

        debt_score = self._get_metric("tech_debt", "tech_debt_score", None)
        if debt_score is not None:
            if debt_score >= 70:
                self._add_finding("Low technical debt", score=8.0, confidence=0.8, sources=["tech_debt"])
            elif debt_score < 40:
                self._add_finding("High technical debt", score=3.0, confidence=0.85, sources=["tech_debt"])

        if self.findings:
            dim_score = sum(f.score for f in self.findings) / len(self.findings)
        else:
            dim_score = 4.0
            self._add_unknown("No code quality evidence available")

        dim_confidence = (sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2)

        return AgentResult(
            agent_name=self.AGENT_NAME, dimension=self.DIMENSION,
            score=round(min(10.0, dim_score), 2),
            confidence=round(dim_confidence, 3),
            findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3),
            unknowns=self.unknowns)


class MaintenanceAgent(SpecialistAgent):
    """Evaluates Git history, activity, contributors, releases, maintenance signals.

    Does NOT automatically punish single-contributor repositories.
    """

    AGENT_NAME = "maintenance_agent"
    DIMENSION = "maintenance"
    ALLOWED_ANALYZERS = ["git_maturity", "release_versioning", "reproducibility"]

    def evaluate(self) -> AgentResult:
        git_raw = self._get_raw_data("git_maturity")
        git_score = self._get_metric("git_maturity", "git_maturity_score", None)
        commit_count = git_raw.get("commit_count", 0)
        contributor_count = git_raw.get("contributor_count", 0)
        last_commit_days = git_raw.get("days_since_last_commit", None)

        if git_score is not None:
            if git_score >= 70:
                self._add_finding("Healthy Git maintenance history", score=8.0, confidence=0.85, sources=["git_maturity"])
            elif git_score >= 50:
                self._add_finding("Moderate Git maintenance", score=5.0, confidence=0.8, sources=["git_maturity"])
            else:
                self._add_finding("Poor Git maintenance signals", score=3.0, confidence=0.8, sources=["git_maturity"])

        if commit_count > 0:
            if contributor_count == 1:
                self._add_finding("Single maintainer — evaluate continuity, not just contributor count",
                    score=6.0, confidence=0.6,
                    evidence=[{"commit_count": commit_count, "contributors": 1}],
                    sources=["git_maturity"])
            elif contributor_count >= 3:
                self._add_finding(f"Active development with {contributor_count} contributors",
                    score=8.0, confidence=0.8, sources=["git_maturity"])
        else:
            self._add_unknown("Git history not available")

        if last_commit_days is not None:
            if last_commit_days <= 30:
                self._add_finding("Recently active repository", score=8.0, confidence=0.9, sources=["git_maturity"])
            elif last_commit_days <= 180:
                self._add_finding("Moderately recent activity", score=6.0, confidence=0.8, sources=["git_maturity"])
            elif last_commit_days > 365:
                self._add_finding("Repository appears abandoned (no commits in >1 year)",
                                score=2.0, confidence=0.85, sources=["git_maturity"])

        rel_raw = self._get_raw_data("release_versioning")
        rel_score = self._get_metric("release_versioning", "release_score", None)
        tag_count = rel_raw.get("tag_count", 0)
        has_changelog = rel_raw.get("has_changelog", False)

        if rel_score is not None:
            if tag_count > 0 and has_changelog:
                self._add_finding(f"Proper release management ({tag_count} tags, changelog)",
                                score=8.0, confidence=0.85, sources=["release_versioning"])
            elif tag_count > 0:
                self._add_finding(f"Has {tag_count} release tags", score=6.0, confidence=0.8, sources=["release_versioning"])
            else:
                self._add_finding("No release tags", score=3.0, confidence=0.7, sources=["release_versioning"])

        repro_raw = self._get_raw_data("reproducibility")
        repro_score = self._get_metric("reproducibility", "reproducibility_score", None)

        if repro_score is not None:
            if repro_score >= 70:
                self._add_finding("Good reproducibility setup", score=8.0, confidence=0.8, sources=["reproducibility"])
            elif repro_score < 40:
                self._add_finding("Poor reproducibility — hard to reproduce builds",
                                score=3.0, confidence=0.8, sources=["reproducibility"])

        if self.findings:
            dim_score = sum(f.score for f in self.findings) / len(self.findings)
        else:
            dim_score = 4.0
            self._add_unknown("No maintenance evidence available")

        dim_confidence = (sum(f.confidence for f in self.findings) / len(self.findings) if self.findings else 0.2)

        return AgentResult(
            agent_name=self.AGENT_NAME, dimension=self.DIMENSION,
            score=round(min(10.0, dim_score), 2),
            confidence=round(dim_confidence, 3),
            findings=self.findings,
            evidence_coverage=round(self._evidence_coverage(), 3),
            unknowns=self.unknowns,
            metadata={"commit_count": commit_count, "contributors": contributor_count})
