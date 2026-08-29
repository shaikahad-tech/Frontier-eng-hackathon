"""
Phase 2 Quality Gates — CI-friendly exit-code-based gate checks.

Exit codes:
  0 = pass
  1 = quality gate failed
  2 = analyzer failure
  3 = invalid configuration
"""

from __future__ import annotations
import sys
import json
import argparse
from typing import Any


class QualityGate:
    """
    Evaluates analysis results against configurable quality gates.
    """

    def __init__(self, max_severity: str = "high", min_score: int = 0,
                 no_critical: bool = False, changed_only: bool = False):
        self.max_severity = max_severity
        self.min_score = min_score
        self.no_critical = no_critical
        self.changed_only = changed_only

        self.severity_order = ["info", "low", "medium", "high", "critical"]

    def check(self, result: dict) -> tuple[int, list[str]]:
        """
        Check the analysis result against the quality gate.

        Returns:
            (exit_code, list_of_failure_reasons)
        """
        failures = []

        # Check for analyzer errors
        if result.get("errors"):
            failures.append(f"Analyzer errors detected: {len(result['errors'])} analyzer(s) failed")
            return (2, failures)

        scores = result.get("scores", {})
        machine = result.get("machine_report", {})

        # Check minimum score
        overall = scores.get("overall_score", 0)
        if overall < self.min_score:
            failures.append(f"Overall score {overall} is below minimum {self.min_score}")

        # Check for critical findings
        if self.no_critical:
            critical_count = scores.get("critical_count", 0)
            if critical_count > 0:
                failures.append(f"Found {critical_count} critical finding(s) — --no-critical gate failed")

        # Check severity threshold
        max_idx = self.severity_order.index(self.max_severity) if self.max_severity in self.severity_order else 4
        for severity in self.severity_order[max_idx + 1:]:
            count_key = f"{severity}_count"
            count = scores.get(count_key, 0)
            if count > 0:
                failures.append(f"Found {count} {severity} finding(s) — --max-severity {self.max_severity} gate failed")

        # Check hard gates
        triggered = scores.get("hard_gates_triggered", [])
        if triggered:
            failures.append(f"Hard gates triggered: {', '.join(g['name'] for g in triggered)}")

        if failures:
            return (1, failures)
        return (0, [])


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Quality Gate Checker")
    parser.add_argument("report", help="Path to machine_report.json")
    parser.add_argument("--max-severity", default="high",
                       help="Maximum allowed severity (info, low, medium, high, critical)")
    parser.add_argument("--min-score", type=int, default=0,
                       help="Minimum overall score required")
    parser.add_argument("--no-critical", action="store_true",
                       help="Fail if any critical findings exist")
    parser.add_argument("--changed-only", action="store_true",
                       help="Only check findings from changed files")

    args = parser.parse_args()

    try:
        with open(args.report) as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"Error: Report not found: {args.report}")
        sys.exit(3)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in report: {args.report}")
        sys.exit(3)

    # Wrap in the expected format
    result = {
        "scores": report.get("scores", {}),
        "errors": report.get("errors", []),
        "machine_report": report,
    }

    gate = QualityGate(
        max_severity=args.max_severity,
        min_score=args.min_score,
        no_critical=args.no_critical,
        changed_only=args.changed_only,
    )

    exit_code, failures = gate.check(result)

    if exit_code == 0:
        print("Quality gate PASSED")
    else:
        print(f"Quality gate FAILED:")
        for failure in failures:
            print(f"  - {failure}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
