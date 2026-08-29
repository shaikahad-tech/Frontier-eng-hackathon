"""
Phase 2 Report Generator — produces three report levels:
1. Executive Report (for non-technical reviewers)
2. Engineering Report (for developers, with findings and evidence)
3. Machine Report (strict JSON for downstream processing)
"""

from __future__ import annotations
import json
from typing import Any


class ReportGenerator:
    """Generates reports from scoring results and tool outputs."""

    def __init__(self, scoring_result: dict, tool_results: list, repo_info: dict):
        self.scoring = scoring_result
        self.tool_results = tool_results
        self.repo_info = repo_info

    def generate_executive(self) -> str:
        """Generate an executive report (markdown)."""
        s = self.scoring
        lines = [
            "# Executive Report",
            "",
            f"**Repository:** {self.repo_info.get('path', 'Unknown')}",
            f"**Overall Score:** {s['overall_score']}/100 ({s['grade']})",
            f"**Maturity Level:** {s['maturity_label']}",
            "",
        ]

        # Hard gates
        if s["hard_gates_triggered"]:
            lines.append("## Hard Gates Triggered")
            lines.append("")
            for gate in s["hard_gates_triggered"]:
                lines.append(f"- **{gate['name']}**: {gate['message']}")
            lines.append("")

        # Top risks
        lines.append("## Top Risks")
        lines.append("")
        all_findings = self._collect_findings()
        risks = [f for f in all_findings if f.get("status") in ("FAIL", "WARN")]
        risks.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("severity", "low"), 4))
        for risk in risks[:5]:
            lines.append(f"- **[{risk.get('severity', 'unknown').upper()}]** {risk.get('title', 'Unknown')}")
            if risk.get("impact"):
                lines.append(f"  - Impact: {risk['impact']}")
        lines.append("")

        # Top strengths
        lines.append("## Top Strengths")
        lines.append("")
        strengths = [f for f in all_findings if f.get("status") == "PASS"]
        for strength in strengths[:5]:
            lines.append(f"- **{strength.get('title', 'Unknown')}**")
        if not strengths:
            lines.append("- No notable strengths detected.")
        lines.append("")

        # Category scores
        lines.append("## Category Scores")
        lines.append("")
        lines.append("| Category | Score |")
        lines.append("|---|---|")
        for cat, score in sorted(s["category_scores"].items()):
            lines.append(f"| {cat.title()} | {score}/100 |")
        lines.append("")

        # Summary status
        lines.append("## Status Summary")
        lines.append("")
        lines.append(f"| Dimension | Status |")
        lines.append(f"|---|---|")
        lines.append(f"| Security | {'FAIL' if s['critical_count'] > 0 else 'PASS'} ({s['category_scores'].get('security', 0)}/100) |")
        lines.append(f"| Testing | {'WARN' if s['category_scores'].get('testing', 0) < 50 else 'PASS'} ({s['category_scores'].get('testing', 0)}/100) |")
        lines.append(f"| Maintainability | {'WARN' if s['category_scores'].get('maintainability', 0) < 50 else 'PASS'} ({s['category_scores'].get('maintainability', 0)}/100) |")
        lines.append(f"| CI/CD | {'WARN' if s['category_scores'].get('cicd', 0) < 50 else 'PASS'} ({s['category_scores'].get('cicd', 0)}/100) |")
        lines.append("")

        return "\n".join(lines)

    def generate_engineering(self) -> str:
        """Generate an engineering report (markdown, detailed)."""
        s = self.scoring
        lines = [
            "# Engineering Report",
            "",
            f"**Repository:** {self.repo_info.get('path', 'Unknown')}",
            f"**Overall Score:** {s['overall_score']}/100 ({s['grade']})",
            f"**Maturity:** {s['maturity_label']}",
            "",
        ]

        # Hard gates
        if s["hard_gates_triggered"]:
            lines.append("## Hard Gates")
            lines.append("")
            for gate in s["hard_gates_triggered"]:
                lines.append(f"- **{gate['name']}** (cap: {gate['max_score']}): {gate['message']}")
            lines.append("")

        # All findings grouped by severity
        all_findings = self._collect_findings()
        for severity in ["critical", "high", "medium", "low", "info"]:
            sev_findings = [f for f in all_findings if f.get("severity") == severity]
            if not sev_findings:
                continue
            lines.append(f"## {severity.upper()} Findings ({len(sev_findings)})")
            lines.append("")
            for f in sev_findings:
                lines.append(f"### {f.get('title', 'Unknown')}")
                lines.append(f"- **ID:** {f.get('id', 'N/A')}")
                lines.append(f"- **Category:** {f.get('category', 'N/A')}")
                lines.append(f"- **Status:** {f.get('status', 'N/A')}")
                lines.append(f"- **Confidence:** {f.get('confidence', 0)}")
                if f.get("files"):
                    for file_info in f["files"]:
                        lines.append(f"- **File:** {file_info.get('path', '?')} (line {file_info.get('line_start', '?')})")
                if f.get("evidence"):
                    lines.append(f"- **Evidence:** {f['evidence']}")
                if f.get("impact"):
                    lines.append(f"- **Impact:** {f['impact']}")
                if f.get("recommendation"):
                    lines.append(f"- **Recommendation:** {f['recommendation']}")
                if f.get("cwe_id"):
                    lines.append(f"- **CWE:** {f['cwe_id']}")
                if f.get("owasp_category"):
                    lines.append(f"- **OWASP:** {f['owasp_category']}")
                lines.append("")

        # Metrics
        lines.append("## Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for result in self.tool_results:
            if isinstance(result, dict):
                for key, value in result.get("metrics", {}).items():
                    lines.append(f"| {key} | {value} |")
        lines.append("")

        # Tool results summary
        lines.append("## Tool Results Summary")
        lines.append("")
        lines.append("| Tool | Status | Findings | Time (s) |")
        lines.append("|---|---|---|---|")
        for result in self.tool_results:
            if isinstance(result, dict):
                lines.append(f"| {result.get('tool_name', '?')} | {result.get('status', '?')} | {len(result.get('findings', []))} | {result.get('execution_time_seconds', 0):.3f} |")
        lines.append("")

        return "\n".join(lines)

    def generate_machine(self) -> dict:
        """Generate a machine-readable JSON report."""
        all_findings = self._collect_findings()
        return {
            "repository": {
                "path": self.repo_info.get("path", ""),
                "profile": self.repo_info.get("profile", "UNKNOWN"),
                "primary_language": self.repo_info.get("primary_language", "unknown"),
            },
            "scores": {
                "overall": self.scoring["overall_score"],
                "grade": self.scoring["grade"],
                "maturity_level": self.scoring["maturity_level"],
                "maturity_label": self.scoring["maturity_label"],
                "categories": self.scoring["category_scores"],
            },
            "hard_gates": self.scoring["hard_gates_triggered"],
            "findings": {
                "total": self.scoring["total_findings"],
                "critical": self.scoring["critical_count"],
                "high": self.scoring["high_count"],
                "medium": self.scoring["medium_count"],
                "low": self.scoring["low_count"],
            },
            "critical_findings": [f for f in all_findings if f.get("severity") == "critical"],
            "high_findings": [f for f in all_findings if f.get("severity") == "high"],
            "medium_findings": [f for f in all_findings if f.get("severity") == "medium"],
            "low_findings": [f for f in all_findings if f.get("severity") == "low"],
            "strengths": [f for f in all_findings if f.get("status") == "PASS"],
            "tool_results": self.tool_results,
            "errors": [r for r in self.tool_results if isinstance(r, dict) and r.get("status") == "ERROR"],
            "analysis_metadata": {
                "analyzer_version": "2.0.0",
                "weights": self.scoring["weights"],
            },
        }

    def _collect_findings(self) -> list[dict]:
        """Collect all findings from tool results."""
        findings = []
        for result in self.tool_results:
            if isinstance(result, dict):
                findings.extend(result.get("findings", []))
        return findings
