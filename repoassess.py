#!/usr/bin/env python3
"""RepoAssess CLI — Evidence-backed Engineering Due Diligence

Usage:
    repoassess analyze <repo_path> [--profile LIBRARY|API|CLI|BACKEND_SERVICE|ML]
                                [--format executive|engineering|json]
                                [--output <file>]
    repoassess benchmark [--adversarial] [--mutations]
    repoassess gate <report.json> --min-score 70

Commands:
    analyze     Evaluate a repository and produce a report
    benchmark   Run the full benchmark suite (Phase 5)
    gate        Check if a report meets a minimum score threshold

Options:
    --profile   Project profile (affects weights)
    --format    Output format: executive, engineering, or json
    --output    Write report to file instead of stdout
    --min-score Minimum score for gate to pass
    --quiet     Suppress progress output
    --verbose   Show detailed progress
    --timeout   Test execution timeout in seconds (default: 30)
"""
import sys
import os
import json
import argparse
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_analyze(args):
    """Analyze a repository."""
    from src.phase4.orchestrator import evaluate_advanced
    from src.phase3.baseline import evaluate_baseline

    repo_path = args.repo_path
    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory", file=sys.stderr)
        return 1

    # Run baseline
    if not args.quiet:
        print("Running baseline evaluation...", file=sys.stderr)
    baseline_result = evaluate_baseline(repo_path)

    # Run advanced
    if not args.quiet:
        print("Running advanced multi-agent evaluation...", file=sys.stderr)
    advanced_result = evaluate_advanced(repo_path, profile=args.profile)

    report = {
        "schema_version": "1.0",
        "repository": os.path.abspath(repo_path),
        "profile": args.profile or "UNKNOWN",
        "baseline": baseline_result,
        "advanced": advanced_result,
    }

    if args.output:
        with open(args.output, "w") as f:
            if args.format == "json":
                json.dump(report, f, indent=2, default=str)
            elif args.format == "engineering":
                f.write(format_engineering_report(report))
            else:
                f.write(format_executive_report(report))
        if not args.quiet:
            print(f"Report written to {args.output}", file=sys.stderr)
    else:
        if args.format == "json":
            print(json.dumps(report, indent=2, default=str))
        elif args.format == "engineering":
            print(format_engineering_report(report))
        else:
            print(format_executive_report(report))

    return 0


def cmd_benchmark(args):
    """Run benchmark suite."""
    from src.phase5.benchmark import run_full_benchmark

    results = run_full_benchmark(verbose=not args.quiet)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        if not args.quiet:
            print(f"\nResults written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2, default=str))

    return 0


def cmd_gate(args):
    """Check if a report meets minimum score."""
    with open(args.report_file) as f:
        report = json.load(f)

    # Try to find score in report
    score = report.get("advanced", {}).get("score", report.get("score", 0))

    if score >= args.min_score:
        print(f"PASS: Score {score} >= {args.min_score}")
        return 0
    else:
        print(f"FAIL: Score {score} < {args.min_score}")
        return 1


def format_executive_report(report: dict) -> str:
    """Format an executive report."""
    adv = report.get("advanced", {})
    baseline = report.get("baseline", {})

    lines = []
    lines.append("=" * 70)
    lines.append("REPOASSESS — Engineering Due Diligence Report")
    lines.append("=" * 70)
    lines.append("")

    # Header
    score = adv.get("score", 0)
    grade = adv.get("grade", "F")
    rec = adv.get("recommendation", "UNKNOWN")
    conf = adv.get("confidence", 0)
    cov = adv.get("evidence_coverage", 0)
    vrate = adv.get("verification_rate", 0)

    lines.append(f"Repository: {report.get('repository', 'N/A')}")
    lines.append(f"Profile: {report.get('profile', 'UNKNOWN')}")
    lines.append("")
    lines.append(f"  ENGINEERING SCORE:  {score}/100  (Grade: {grade})")
    lines.append(f"  RECOMMENDATION:     {rec}")
    lines.append(f"  CONFIDENCE:         {conf:.0%}")
    lines.append(f"  EVIDENCE COVERAGE:  {cov:.0%}")
    lines.append(f"  VERIFICATION RATE:  {vrate:.0%}")
    lines.append("")

    # Baseline comparison
    bscore = baseline.get("score", 0)
    lines.append(f"  Baseline Score:     {bscore:.1f}/10")
    lines.append(f"  Advanced Score:     {score}/100")
    lines.append("")

    # Top Risks
    risks = adv.get("top_risks", [])
    if risks:
        lines.append("TOP RISKS:")
        for r in risks[:5]:
            lines.append(f"  - {r}")
        lines.append("")

    # Top Strengths
    strengths = adv.get("top_strengths", [])
    if strengths:
        lines.append("TOP STRENGTHS:")
        for s in strengths[:5]:
            lines.append(f"  + {s}")
        lines.append("")

    # Dimension Scores
    breakdown = adv.get("agent_breakdown", {})
    if breakdown:
        lines.append("ENGINEERING DIMENSIONS:")
        lines.append(f"  {'Dimension':<20} {'Score':>8} {'Confidence':>12} {'Coverage':>10}")
        lines.append(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10}")
        for dim, data in breakdown.items():
            lines.append(f"  {dim:<20} {data.get('score', 0):>8.1f} {data.get('confidence', 0):>12.0%} {data.get('evidence_coverage', 0):>10.0%}")
        lines.append("")

    # Gate reasons
    gates = adv.get("gate_reasons", [])
    if gates:
        lines.append("HARD GATES TRIGGERED:")
        for g in gates:
            lines.append(f"  [!] {g}")
        lines.append("")

    # Remediation
    remediation = adv.get("remediation_plan", [])
    if remediation:
        lines.append("REMEDIATION PLAN:")
        for item in remediation[:5]:
            lines.append(f"  [{item['priority']}] {item['finding']}")
            if item.get("file"):
                lines.append(f"       File: {item['file']}")
            lines.append(f"       Action: {item['recommended_action']}")
        lines.append("")

    # Known Unknowns
    unknowns = adv.get("known_unknowns", [])
    if unknowns:
        lines.append("KNOWN UNKNOWNS:")
        for u in unknowns[:5]:
            lines.append(f"  ? {u}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("Assessment generated by RepoAssess. Scores are based on static analysis")
    lines.append("and do not guarantee production readiness. Runtime behavior was not evaluated.")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_engineering_report(report: dict) -> str:
    """Format a detailed engineering report."""
    adv = report.get("advanced", {})

    lines = [format_executive_report(report)]

    lines.append("")
    lines.append("ENGINEERING DETAILS")
    lines.append("-" * 70)

    # Score explanations
    explanations = adv.get("score_explanation", {})
    for dim, exp in explanations.items():
        lines.append(f"\n{exp['dimension'].upper()} (Score: {exp['score_0_100']}/100)")
        if exp.get("positives"):
            lines.append("  Positives:")
            for p in exp["positives"]:
                lines.append(f"    + {p}")
        if exp.get("negatives"):
            lines.append("  Negatives:")
            for n in exp["negatives"]:
                lines.append(f"    - {n}")
        if exp.get("unknowns"):
            lines.append("  Unknowns:")
            for u in exp["unknowns"]:
                lines.append(f"    ? {u}")

    # Verification details
    vdetails = adv.get("verification_details", [])
    if vdetails:
        lines.append(f"\nVERIFICATION DETAILS ({len(vdetails)} findings)")
        for v in vdetails:
            lines.append(f"  [{v['status']}] {v['claim']}")
            lines.append(f"    Type: {v.get('claim_type', 'generic')}")
            if v.get("supporting"):
                lines.append(f"    Supporting: {v['supporting'][0]}")
            if v.get("contradicting"):
                lines.append(f"    Contradicting: {v['contradicting'][0]}")

    # Full remediation
    remediation = adv.get("remediation_plan", [])
    if remediation:
        lines.append(f"\nFULL REMEDIATION PLAN ({len(remediation)} items)")
        for item in remediation:
            lines.append(f"\n  [{item['priority']}] {item['finding']}")
            lines.append(f"    Dimension: {item['dimension']}")
            lines.append(f"    Severity: {item['severity']}")
            if item.get("file"):
                lines.append(f"    File: {item['file']}" + (f":{item['line']}" if item.get("line") else ""))
            lines.append(f"    Action: {item['recommended_action']}")
            lines.append(f"    Impact: {item['expected_impact']}")
            lines.append(f"    Verification: {item.get('verification_status', 'UNKNOWN')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="repoassess",
        description="Evidence-backed Engineering Due Diligence for Software Repositories",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Evaluate a repository")
    p_analyze.add_argument("repo_path", help="Path to repository")
    p_analyze.add_argument("--profile", choices=["LIBRARY", "API", "CLI", "BACKEND_SERVICE", "ML"],
                          help="Project profile")
    p_analyze.add_argument("--format", choices=["executive", "engineering", "json"],
                          default="executive", help="Output format")
    p_analyze.add_argument("--output", help="Write report to file")
    p_analyze.add_argument("--quiet", action="store_true", help="Suppress progress")
    p_analyze.add_argument("--verbose", action="store_true", help="Detailed progress")
    p_analyze.add_argument("--timeout", type=int, default=30, help="Test execution timeout")

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run benchmark suite")
    p_bench.add_argument("--adversarial", action="store_true", help="Include adversarial cases")
    p_bench.add_argument("--mutations", action="store_true", help="Run mutation tests")
    p_bench.add_argument("--output", help="Write results to file")
    p_bench.add_argument("--quiet", action="store_true")

    # gate
    p_gate = subparsers.add_parser("gate", help="Check if report meets minimum score")
    p_gate.add_argument("report_file", help="Path to JSON report")
    p_gate.add_argument("--min-score", type=float, default=70, help="Minimum score threshold")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "benchmark":
        return cmd_benchmark(args)
    elif args.command == "gate":
        return cmd_gate(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
