"""
Phase 2 Suppression & Baseline Support — false positive control
and baseline marking for gradual adoption.
"""
from __future__ import annotations
import json
import os
from typing import Any

from src.phase2.schema import Finding, Status


class SuppressionManager:
    """
    Manages finding suppressions at repository, file, and rule level.
    Supports allowlists and justification tracking.
    """

    def __init__(self, suppression_file: str = None):
        self.suppressions = []
        if suppression_file and os.path.exists(suppression_file):
            with open(suppression_file) as f:
                self.suppressions = json.load(f)

    def add_suppression(self, rule_id: str = None, file_path: str = None,
                        justification: str = "", scope: str = "file"):
        """Add a suppression entry."""
        self.suppressions.append({
            "rule_id": rule_id,
            "file": file_path,
            "scope": scope,
            "justification": justification,
        })

    def is_suppressed(self, finding: Finding) -> bool:
        """Check if a finding should be suppressed."""
        for sup in self.suppressions:
            if sup.get("rule_id") and finding.id == sup["rule_id"]:
                return True
            if sup.get("file"):
                for f in finding.files:
                    if sup["file"] in f.get("path", ""):
                        return True
        return False

    def apply_suppressions(self, findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
        """
        Apply suppressions to a list of findings.

        Returns:
            (active_findings, suppressed_findings)
        """
        active = []
        suppressed = []
        for f in findings:
            if self.is_suppressed(f):
                f.suppressed = True
                f.suppression_reason = "Matched suppression rule"
                suppressed.append(f)
            else:
                active.append(f)
        return active, suppressed

    def detect_over_suppression(self, findings: list[Finding]) -> list[Finding]:
        """
        Detect when too many findings of the same rule are suppressed.
        This itself becomes a finding.
        """
        suppression_counts = {}
        for f in findings:
            if f.suppressed:
                suppression_counts[f.id] = suppression_counts.get(f.id, 0) + 1

        over_suppression_findings = []
        for rule_id, count in suppression_counts.items():
            if count > 10:
                over_suppression_findings.append(Finding(
                    id="QUALITY-SEC-OVER-SUPPRESSION",
                    category="maintainability",
                    severity="medium",
                    status="WARN",
                    title=f"Excessive suppression: rule {rule_id} suppressed {count} times",
                    confidence=1.0,
                    evidence=f"{count} instances of {rule_id} suppressed",
                    recommendation="Review suppression rules. Too many suppressions may hide real issues.",
                ))
        return over_suppression_findings

    def save(self, path: str):
        """Save suppressions to file."""
        with open(path, "w") as f:
            json.dump(self.suppressions, f, indent=2)


class BaselineManager:
    """
    Allows existing findings to be marked as 'baseline' so only
    newly introduced findings fail quality gates.
    """

    def __init__(self, baseline_file: str = None):
        self.baseline_findings = set()
        if baseline_file and os.path.exists(baseline_file):
            with open(baseline_file) as f:
                data = json.load(f)
                self.baseline_findings = {tuple(item) for item in data}

    def create_baseline(self, findings: list[Finding]) -> int:
        """Create a baseline from current findings."""
        self.baseline_findings = {self._finding_key(f) for f in findings}
        return len(self.baseline_findings)

    def is_baseline(self, finding: Finding) -> bool:
        """Check if a finding exists in the baseline."""
        return self._finding_key(finding) in self.baseline_findings

    def filter_new_findings(self, findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
        """
        Split findings into new and baseline.

        Returns:
            (new_findings, baseline_findings)
        """
        new = []
        baseline = []
        for f in findings:
            if self.is_baseline(f):
                baseline.append(f)
            else:
                new.append(f)
        return new, baseline

    def _finding_key(self, f: Finding) -> tuple:
        files = tuple(sorted(tuple(ff.get("path", "")) for ff in f.files)) if f.files else ()
        return (f.category, f.title, files)

    def save(self, path: str):
        """Save baseline to file."""
        with open(path, "w") as f:
            json.dump([list(item) for item in self.baseline_findings], f, indent=2)
