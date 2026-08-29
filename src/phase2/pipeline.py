"""
Phase 2 Pipeline Orchestrator — runs all analyzers in dependency order,
collects results, and produces the final report.

Flow:
    Repository -> Discovery -> Profile -> Analyzer Registry ->
    Parallel Analysis -> Evidence Normalization -> Finding Dedup ->
    Severity/Confidence -> Category Scores -> Hard Gates ->
    Grade -> Report
"""

from __future__ import annotations

import os
import sys
import json
import time
import concurrent.futures
from typing import Any

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.phase2.schema import (
    AnalyzerBase, AnalyzerRegistry, ToolResult, Finding,
    Status, Severity, register_analyzer,
)
from src.phase2.scoring import ScoringEngine
from src.phase2.reporting import ReportGenerator


class Pipeline:
    """
    Orchestrates the full Phase 2 analysis pipeline.
    """

    def __init__(self, repo_path: str, parallel: bool = True, verbose: bool = False):
        self.repo_path = os.path.abspath(repo_path)
        self.parallel = parallel
        self.verbose = verbose
        self.context: dict[str, Any] = {}
        self.tool_results: list[dict] = []
        self.all_findings: list[Finding] = []
        self.errors: list[dict] = []
        self.scoring_engine: ScoringEngine | None = None

        # Import all analyzers to trigger registration
        self._import_analyzers()

    def _import_analyzers(self):
        """Import all analyzer modules to register them."""
        try:
            from src.phase2.analyzers import all_analyzers  # noqa: F401 - triggers registration
        except ImportError as e:
            if self.verbose:
                print(f"Warning: some analyzers failed to import: {e}")

    def run(self) -> dict:
        """
        Run the full analysis pipeline.

        Returns the complete analysis result.
        """
        start_time = time.time()

        if not os.path.exists(self.repo_path):
            raise FileNotFoundError(f"Repository not found: {self.repo_path}")

        # Step 1: Run discovery first (other analyzers depend on it)
        if self.verbose:
            print("Phase 2: Running repository discovery...")

        discovery = AnalyzerRegistry.get_instance("repository_discovery")
        if discovery:
            result = discovery.analyze(self.repo_path, {})
            self.tool_results.append(result.to_dict())
            self.context["discovery"] = result.raw_data.get("discovery", {})
            self.all_findings.extend(result.findings)
            if self.verbose:
                profile = self.context["discovery"].get("project_profile", "UNKNOWN")
                print(f"  Profile: {profile}")
                print(f"  Files: {self.context['discovery'].get('file_stats', {}).get('total_files', 0)}")

        profile = self.context.get("discovery", {}).get("project_profile", "UNKNOWN")

        # Step 2: Run all other analyzers (in parallel or sequential)
        all_analyzers = AnalyzerRegistry.get_all()
        # Exclude discovery (already ran)
        analyzer_ids = [aid for aid in all_analyzers if aid != "repository_discovery"]

        if self.parallel:
            self._run_parallel(analyzer_ids, all_analyzers)
        else:
            self._run_sequential(analyzer_ids, all_analyzers)

        # Step 3: Score
        if self.verbose:
            print(f"Phase 2: Scoring ({len(self.all_findings)} findings)...")

        self.scoring_engine = ScoringEngine(profile=profile)
        scoring_result = self.scoring_engine.score(self.tool_results, self.all_findings)

        # Step 4: Generate reports
        repo_info = {
            "path": self.repo_path,
            "profile": profile,
            "primary_language": self.context.get("discovery", {}).get("primary_language", "unknown"),
        }

        report_gen = ReportGenerator(scoring_result, self.tool_results, repo_info)

        elapsed = time.time() - start_time

        result = {
            "repository": repo_info,
            "profile": profile,
            "scores": scoring_result,
            "tool_results": self.tool_results,
            "errors": self.errors,
            "analysis_metadata": {
                "analyzer_version": "2.0.0",
                "total_time_seconds": round(elapsed, 3),
                "analyzer_count": len(self.tool_results),
                "finding_count": len(self.all_findings),
            },
            "executive_report": report_gen.generate_executive(),
            "engineering_report": report_gen.generate_engineering(),
            "machine_report": report_gen.generate_machine(),
        }

        if self.verbose:
            print(f"\nPhase 2 Complete: {scoring_result['overall_score']}/100 ({scoring_result['grade']})")
            print(f"  Maturity: {scoring_result['maturity_label']}")
            print(f"  Findings: {len(self.all_findings)} total, "
                  f"{scoring_result['critical_count']} critical, "
                  f"{scoring_result['high_count']} high")
            if scoring_result["hard_gates_triggered"]:
                print(f"  Hard gates triggered: {len(scoring_result['hard_gates_triggered'])}")
            print(f"  Time: {elapsed:.2f}s")

        return result

    def _run_parallel(self, analyzer_ids: list, all_analyzers: dict):
        """Run analyzers in parallel using ThreadPoolExecutor."""
        if self.verbose:
            print(f"Phase 2: Running {len(analyzer_ids)} analyzers in parallel...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for aid in analyzer_ids:
                analyzer_cls = all_analyzers.get(aid)
                if not analyzer_cls:
                    continue
                # Check profile support
                if analyzer_cls.SUPPORTS_PROFILES:
                    profile = self.context.get("discovery", {}).get("project_profile", "UNKNOWN")
                    if profile not in analyzer_cls.SUPPORTS_PROFILES:
                        continue
                instance = analyzer_cls()
                future = executor.submit(self._run_analyzer, aid, instance)
                futures[future] = aid

            for future in concurrent.futures.as_completed(futures):
                aid = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.errors.append({"analyzer": aid, "error": str(e)})
                    if self.verbose:
                        print(f"  {aid} failed: {e}")

    def _run_sequential(self, analyzer_ids: list, all_analyzers: dict):
        """Run analyzers sequentially."""
        if self.verbose:
            print(f"Phase 2: Running {len(analyzer_ids)} analyzers sequentially...")

        for aid in analyzer_ids:
            analyzer_cls = all_analyzers.get(aid)
            if not analyzer_cls:
                continue
            if analyzer_cls.SUPPORTS_PROFILES:
                profile = self.context.get("discovery", {}).get("project_profile", "UNKNOWN")
                if profile not in analyzer_cls.SUPPORTS_PROFILES:
                    continue
            instance = analyzer_cls()
            self._run_analyzer(aid, instance)

    def _run_analyzer(self, analyzer_id: str, instance: AnalyzerBase):
        """Run a single analyzer and collect results."""
        if self.verbose:
            print(f"  -> {instance.ANALYZER_NAME}...")

        start = time.time()
        try:
            result = instance.analyze(self.repo_path, self.context)
            result_dict = result.to_dict()
            self.tool_results.append(result_dict)
            self.all_findings.extend(result.findings)

            if self.verbose:
                status_icon = "OK" if result.status == "PASS" else "WARN" if result.status == "WARN" else "FAIL"
                print(f"    [{status_icon}] {result.status} - {len(result.findings)} findings ({result.execution_time_seconds:.3f}s)")

        except Exception as e:
            self.errors.append({
                "analyzer": analyzer_id,
                "error": str(e),
                "recoverable": True,
            })
            # Record the failure as a tool result
            self.tool_results.append({
                "tool_name": instance.ANALYZER_NAME,
                "status": Status.ERROR.value,
                "findings": [],
                "metrics": {},
                "errors": [str(e)],
                "execution_time_seconds": round(time.time() - start, 3),
                "analyzer_version": instance.VERSION,
            })
            if self.verbose:
                print(f"    ERROR: {e}")


# --- CLI ---

def run_analysis(repo_path: str, output_dir: str = "phase2_output",
                 parallel: bool = True, verbose: bool = True) -> dict:
    """
    Run the Phase 2 analysis on a repository.

    Args:
        repo_path: Path to the repository to analyze.
        output_dir: Directory to save reports.
        parallel: Run analyzers in parallel.
        verbose: Print progress.

    Returns:
        Complete analysis result.
    """
    pipeline = Pipeline(repo_path, parallel=parallel, verbose=verbose)
    result = pipeline.run()

    # Save reports
    os.makedirs(output_dir, exist_ok=True)

    # Executive report
    with open(os.path.join(output_dir, "executive_report.md"), "w") as f:
        f.write(result["executive_report"])

    # Engineering report
    with open(os.path.join(output_dir, "engineering_report.md"), "w") as f:
        f.write(result["engineering_report"])

    # Machine report (JSON)
    with open(os.path.join(output_dir, "machine_report.json"), "w") as f:
        json.dump(result["machine_report"], f, indent=2, default=str)

    if verbose:
        print(f"\nReports saved to {output_dir}/")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.phase2.pipeline <repo_path> [--output DIR] [--sequential] [--quiet]")
        sys.exit(1)

    repo = sys.argv[1]
    output = "phase2_output"
    parallel = True
    verbose = True

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--output" and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]
        elif arg == "--sequential":
            parallel = False
        elif arg == "--quiet":
            verbose = False

    result = run_analysis(repo, output_dir=output, parallel=parallel, verbose=verbose)

    # Exit code based on score
    score = result["scores"]["overall_score"]
    if result["scores"]["hard_gates_triggered"]:
        sys.exit(1)  # Quality gate failed
    elif score < 50:
        sys.exit(1)
    else:
        sys.exit(0)
