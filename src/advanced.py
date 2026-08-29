"""
Advanced multi-agent solution for repository quality assessment.

Architecture:
─────────────
1. Orchestrator Agent — coordinates the workflow, calls specialist agents,
   synthesizes their findings into a final report.

2. Specialist Agents (run in parallel):
   a. Structure Agent   — analyzes project structure, config, organization
   b. Test Agent         — counts tests, runs them, checks CI config
   c. Code Quality Agent — complexity, tech debt markers, documentation, security
   d. Maintenance Agent  — git history, contributors, recent activity, releases

3. Verification Agent — cross-checks claims made by specialist agents against
   the raw tool data. Catches hallucinations and unsupported assertions.

4. Orchestrator produces the final consolidated report with evidence.

Key improvements over baseline:
- Uses 10 real tools (not just README) to gather evidence
- Multiple specialized agents each focus on one dimension
- Verification agent catches unsupported claims
- Every finding is backed by tool data (evidence chain)
- Structured scoring with transparent reasoning
- Security analysis (bare except, eval, exec, hardcoded secrets)
"""

import json
import os
import sys
import time
import concurrent.futures
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.trajectory_logger import TrajectoryLogger
from src.tools.repo_tools import (
    read_readme,
    analyze_structure,
    analyze_dependencies,
    analyze_tests,
    run_tests,
    analyze_complexity,
    analyze_code_quality,
    analyze_documentation,
    analyze_git_history,
    analyze_security,
)


# ─── Specialist Agent: Structure ───

def structure_agent(repo_path: str, logger: TrajectoryLogger) -> dict:
    """Analyze project structure, configuration, and organization."""
    logger.log_instruction(f"Analyze the project structure and configuration of {repo_path}")

    readme = read_readme(repo_path)
    logger.log_tool_call("read_readme", {"repo_path": repo_path}, readme)

    structure = analyze_structure(repo_path)
    logger.log_tool_call("analyze_structure", {"repo_path": repo_path}, structure)

    deps = analyze_dependencies(repo_path)
    logger.log_tool_call("analyze_dependencies", {"repo_path": repo_path}, deps)

    # Calibrated: base=3, only above-average gets bonus
    score = 3
    findings = []
    evidence = []

    if readme.get("found"):
        score += 1
        findings.append(("strength", "README file present"))
        evidence.append({"claim": "README exists", "source": "read_readme", "data": {"filename": readme.get("filename")}})
        if readme.get("length_chars", 0) > 2000:
            score += 1
            findings.append(("strength", "README is detailed (2000+ chars)"))
            evidence.append({"claim": "README is detailed", "source": "read_readme", "data": {"length_chars": readme.get("length_chars")}})
        if readme.get("has_usage"):
            score += 0.5
            findings.append(("strength", "README includes usage examples"))
    else:
        score -= 1
        findings.append(("weakness", "No README file"))
        evidence.append({"claim": "No README", "source": "read_readme", "data": {"found": False}})

    if structure.get("has_dockerfile"):
        score += 1
        findings.append(("strength", "Has Dockerfile"))
        evidence.append({"claim": "Dockerfile exists", "source": "analyze_structure", "data": {"has_dockerfile": True}})

    if structure.get("has_makefile"):
        score += 0.5
        findings.append(("strength", "Has Makefile for build automation"))

    if structure.get("has_pyproject") or structure.get("has_setup_py"):
        score += 1
        findings.append(("strength", "Has proper Python packaging config"))
        evidence.append({"claim": "Packaging config present", "source": "analyze_structure", "data": {"has_pyproject": structure.get("has_pyproject"), "has_setup_py": structure.get("has_setup_py")}})

    if deps.get("total", 0) > 0:
        if deps["total"] <= 20:
            score += 1
            findings.append(("strength", f"Manageable dependency count ({deps['total']})"))
        elif deps["total"] > 50:
            score -= 2
            findings.append(("weakness", f"Excessive dependency count ({deps['total']})"))
        elif deps["total"] > 30:
            score -= 1
            findings.append(("weakness", f"High dependency count ({deps['total']})"))
        evidence.append({"claim": f"Has {deps['total']} dependencies", "source": "analyze_dependencies", "data": {"total": deps["total"], "source_file": deps.get("source")}})

    score = max(1, min(10, score))
    logger.log_thought(f"Structure analysis complete. Score: {score}/10. Findings: {len(findings)}")

    return {
        "agent": "structure",
        "dimension": "Structure & Configuration",
        "score": score,
        "findings": findings,
        "evidence": evidence,
        "raw_data": {"readme": readme, "structure": structure, "dependencies": deps},
    }


# ─── Specialist Agent: Test ───

def test_agent(repo_path: str, logger: TrajectoryLogger) -> dict:
    """Analyze test coverage, test quality, and CI configuration."""
    logger.log_instruction(f"Analyze test suite quality and coverage of {repo_path}")

    test_data = analyze_tests(repo_path)
    logger.log_tool_call("analyze_tests", {"repo_path": repo_path}, test_data)

    test_run = run_tests(repo_path, timeout=30)
    logger.log_tool_call("run_tests", {"repo_path": repo_path, "timeout": 30}, test_run)

    # Calibrated: base=3, tests are critical, absence is heavily penalized
    score = 3
    findings = []
    evidence = []

    if test_data["test_file_count"] > 0:
        score += 2
        findings.append(("strength", f"Has {test_data['test_file_count']} test file(s)"))
        evidence.append({"claim": f"Test files: {test_data['test_file_count']}", "source": "analyze_tests", "data": {"test_file_count": test_data["test_file_count"]}})

        ratio = test_data["test_to_source_ratio"]
        if ratio > 0.5:
            score += 2
            findings.append(("strength", f"Good test-to-source ratio: {ratio:.2f}"))
            evidence.append({"claim": f"Test ratio {ratio:.2f}", "source": "analyze_tests", "data": {"ratio": ratio}})
        elif ratio > 0.2:
            score += 1
            findings.append(("strength", f"Moderate test-to-source ratio: {ratio:.2f}"))
        else:
            score -= 1
            findings.append(("weakness", f"Low test-to-source ratio: {ratio:.2f}"))
            evidence.append({"claim": f"Low test ratio {ratio:.2f}", "source": "analyze_tests", "data": {"ratio": ratio}})
    else:
        score -= 2
        findings.append(("weakness", "No test files found"))
        evidence.append({"claim": "Zero test files", "source": "analyze_tests", "data": {"test_file_count": 0}})

    if test_data.get("has_pytest_config") or test_data.get("has_tox_config"):
        score += 1
        findings.append(("strength", "Has test configuration (pytest/tox)"))

    if test_data.get("has_ci"):
        score += 1
        findings.append(("strength", "Has CI/CD pipeline configured"))
        evidence.append({"claim": "CI configured", "source": "analyze_tests", "data": {"has_ci": True}})
    else:
        score -= 1
        findings.append(("weakness", "No CI/CD pipeline detected"))

    if test_run.get("ran"):
        passed = test_run.get("passed", 0)
        failed = test_run.get("failed", 0)
        errors = test_run.get("errors", 0)
        total = passed + failed + errors
        if total > 0:
            pass_rate = passed / total
            if pass_rate == 1.0:
                score += 2
                findings.append(("strength", f"All tests pass ({passed} tests)"))
                evidence.append({"claim": f"All {passed} tests pass", "source": "run_tests", "data": {"passed": passed, "failed": failed}})
            elif pass_rate >= 0.8:
                score += 1
                findings.append(("strength", f"Most tests pass ({passed}/{total})"))
            else:
                score -= 2
                findings.append(("weakness", f"Many tests failing ({failed + errors}/{total})"))
                evidence.append({"claim": f"{failed + errors} failing tests", "source": "run_tests", "data": {"passed": passed, "failed": failed, "errors": errors}})
    elif test_run.get("error") == "timeout":
        findings.append(("weakness", "Test suite timed out (possible performance issue)"))

    score = max(1, min(10, score))
    logger.log_thought(f"Test analysis complete. Score: {score}/10. Findings: {len(findings)}")

    return {
        "agent": "test",
        "dimension": "Testing & CI",
        "score": score,
        "findings": findings,
        "evidence": evidence,
        "raw_data": {"test_analysis": test_data, "test_run": test_run},
    }


# ─── Specialist Agent: Code Quality ───

def code_quality_agent(repo_path: str, logger: TrajectoryLogger) -> dict:
    """Analyze code complexity, documentation, tech debt, and security."""
    logger.log_instruction(f"Analyze code quality, complexity, documentation, and security of {repo_path}")

    complexity = analyze_complexity(repo_path)
    logger.log_tool_call("analyze_complexity", {"repo_path": repo_path}, complexity)

    quality = analyze_code_quality(repo_path)
    logger.log_tool_call("analyze_code_quality", {"repo_path": repo_path}, quality)

    docs = analyze_documentation(repo_path)
    logger.log_tool_call("analyze_documentation", {"repo_path": repo_path}, docs)

    security = analyze_security(repo_path)
    logger.log_tool_call("analyze_security", {"repo_path": repo_path}, security)

    # Calibrated: base=4, above-average docs/complexity get bonus, debt penalized heavily
    score = 4
    findings = []
    evidence = []

    # Complexity
    avg_complexity = complexity.get("average_complexity", 0)
    high_count = complexity.get("high_complexity_count", 0)
    if avg_complexity < 3:
        score += 2
        findings.append(("strength", f"Low average complexity: {avg_complexity}"))
        evidence.append({"claim": f"Low avg complexity {avg_complexity}", "source": "analyze_complexity", "data": {"average_complexity": avg_complexity}})
    elif avg_complexity < 6:
        score += 1
        findings.append(("strength", f"Moderate average complexity: {avg_complexity}"))
    elif avg_complexity > 10:
        score -= 3
        findings.append(("weakness", f"High average complexity: {avg_complexity}"))
        evidence.append({"claim": f"High avg complexity {avg_complexity}", "source": "analyze_complexity", "data": {"average_complexity": avg_complexity}})

    if high_count > 10:
        score -= 2
        findings.append(("weakness", f"{high_count} functions with high complexity (>=10)"))
        evidence.append({"claim": f"{high_count} high-complexity functions", "source": "analyze_complexity", "data": {"high_complexity_count": high_count}})
    elif high_count == 0 and complexity.get("total_functions", 0) > 0:
        score += 1
        findings.append(("strength", "No high-complexity functions"))

    # Tech debt markers
    debt_markers = quality.get("tech_debt_markers", 0)
    if debt_markers == 0:
        score += 1
        findings.append(("strength", "No TODO/FIXME/HACK markers in code"))
    elif debt_markers > 5:
        score -= 2
        findings.append(("weakness", f"High tech debt markers: {debt_markers} (TODO/FIXME/HACK)"))
        evidence.append({"claim": f"{debt_markers} debt markers", "source": "analyze_code_quality", "data": {"tech_debt_markers": debt_markers}})
    elif debt_markers > 0:
        score -= 1
        findings.append(("weakness", f"Tech debt markers present: {debt_markers} (TODO/FIXME/HACK)"))

    # Comment ratio
    comment_ratio = quality.get("comment_ratio", 0)
    if comment_ratio > 0.15:
        score += 1
        findings.append(("strength", f"Good comment ratio: {comment_ratio:.0%}"))
    elif comment_ratio < 0.05:
        score -= 1
        findings.append(("weakness", f"Low comment ratio: {comment_ratio:.0%}"))

    # Documentation
    docstring_ratio = docs.get("docstring_ratio", 0)
    if docstring_ratio > 0.7:
        score += 2
        findings.append(("strength", f"Excellent docstring coverage: {docstring_ratio:.0%}"))
        evidence.append({"claim": f"Docstring ratio {docstring_ratio:.0%}", "source": "analyze_documentation", "data": {"docstring_ratio": docstring_ratio}})
    elif docstring_ratio > 0.4:
        score += 1
        findings.append(("strength", f"Good docstring coverage: {docstring_ratio:.0%}"))
    elif docstring_ratio < 0.1 and complexity.get("total_functions", 0) > 0:
        score -= 1
        findings.append(("weakness", f"Poor docstring coverage: {docstring_ratio:.0%}"))
        evidence.append({"claim": f"Low docstring ratio {docstring_ratio:.0%}", "source": "analyze_documentation", "data": {"docstring_ratio": docstring_ratio}})

    if docs.get("has_license"):
        score += 0.5
        findings.append(("strength", "Has LICENSE file"))
    else:
        score -= 1
        findings.append(("weakness", "No LICENSE file found"))

    if docs.get("has_contributing"):
        score += 0.5
        findings.append(("strength", "Has CONTRIBUTING.md"))

    if docs.get("has_changelog"):
        score += 0.5
        findings.append(("strength", "Has CHANGELOG"))

    # Security
    sec_issues = security.get("issue_count", 0)
    if sec_issues == 0:
        score += 1
        findings.append(("strength", "No security issues detected"))
    else:
        score -= min(3, sec_issues)
        findings.append(("weakness", f"{sec_issues} security issue(s) found (bare except, eval, exec, etc.)"))
        evidence.append({"claim": f"{sec_issues} security issues", "source": "analyze_security", "data": {"issue_count": sec_issues, "types": [i["type"] for i in security.get("issues_found", [])[:5]]}})

    score = max(1, min(10, score))
    logger.log_thought(f"Code quality analysis complete. Score: {score}/10. Findings: {len(findings)}")

    return {
        "agent": "code_quality",
        "dimension": "Code Quality & Security",
        "score": score,
        "findings": findings,
        "evidence": evidence,
        "raw_data": {"complexity": complexity, "quality": quality, "documentation": docs, "security": security},
    }


# ─── Specialist Agent: Maintenance ───

def maintenance_agent(repo_path: str, logger: TrajectoryLogger) -> dict:
    """Analyze git history, contributor health, and maintenance indicators."""
    logger.log_instruction(f"Analyze maintenance health and project activity of {repo_path}")

    git_data = analyze_git_history(repo_path)
    logger.log_tool_call("analyze_git_history", {"repo_path": repo_path}, git_data)

    # Calibrated: base=3, active projects get rewarded, inactive penalized
    score = 3
    findings = []
    evidence = []

    total_commits = git_data.get("total_commits", 0)
    if total_commits > 500:
        score += 2
        findings.append(("strength", f"Active commit history ({total_commits} commits)"))
        evidence.append({"claim": f"{total_commits} total commits", "source": "analyze_git_history", "data": {"total_commits": total_commits}})
    elif total_commits > 50:
        score += 1
        findings.append(("strength", f"Good commit history ({total_commits} commits)"))
    elif total_commits < 5:
        score -= 1
        findings.append(("weakness", f"Very few commits ({total_commits})"))

    contributors = git_data.get("contributor_count", 0)
    if contributors > 10:
        score += 2
        findings.append(("strength", f"Healthy contributor base ({contributors} contributors)"))
        evidence.append({"claim": f"{contributors} contributors", "source": "analyze_git_history", "data": {"contributor_count": contributors}})
    elif contributors > 3:
        score += 1
        findings.append(("strength", f"Multiple contributors ({contributors})"))
    elif contributors <= 1:
        score -= 1
        findings.append(("weakness", "Single contributor — bus factor risk"))
        evidence.append({"claim": "Single contributor", "source": "analyze_git_history", "data": {"contributor_count": contributors}})

    recent_commits = git_data.get("recent_commit_count_30d", 0)
    if recent_commits > 10:
        score += 2
        findings.append(("strength", f"Very active recently ({recent_commits} commits in last 30 days)"))
        evidence.append({"claim": f"{recent_commits} recent commits", "source": "analyze_git_history", "data": {"recent_commit_count_30d": recent_commits}})
    elif recent_commits > 0:
        score += 1
        findings.append(("strength", f"Active in last 30 days ({recent_commits} commits)"))
    else:
        score -= 2
        findings.append(("weakness", "No commits in last 30 days — may be abandoned"))
        evidence.append({"claim": "No recent commits", "source": "analyze_git_history", "data": {"recent_commit_count_30d": 0}})

    tags = git_data.get("tag_count", 0)
    if tags > 5:
        score += 1
        findings.append(("strength", f"Has {tags} tagged releases"))
    elif tags == 0:
        score -= 0.5
        findings.append(("weakness", "No version tags found"))

    score = max(1, min(10, score))
    logger.log_thought(f"Maintenance analysis complete. Score: {score}/10. Findings: {len(findings)}")

    return {
        "agent": "maintenance",
        "dimension": "Maintenance & Activity",
        "score": score,
        "findings": findings,
        "evidence": evidence,
        "raw_data": {"git_history": git_data},
    }


# ─── Verification Agent ───

def verification_agent(specialist_results: list[dict], logger: TrajectoryLogger) -> dict:
    """
    Cross-checks claims made by specialist agents against raw tool data.
    Catches unsupported assertions and hallucinated findings.

    For each finding, checks:
    1. Is there a matching evidence entry?
    2. If not, can the finding be verified against the raw tool data?
    3. If neither, the finding is flagged as unverified.
    """
    logger.log_instruction("Verify all specialist agent findings against raw tool data.")

    verified_findings = []
    flagged_findings = []

    for result in specialist_results:
        agent_name = result.get("agent", "unknown")
        raw_data = result.get("raw_data", {})
        evidence_list = result.get("evidence", [])

        for finding_type, finding_text in result.get("findings", []):
            # Check if this finding has a matching evidence entry
            has_evidence = False
            for ev in evidence_list:
                claim = ev.get("claim", "").lower()
                # Check if key words from the finding appear in the claim
                finding_words = [w for w in finding_text.lower().split() if len(w) > 3]
                if any(w in claim for w in finding_words[:3]):
                    has_evidence = True
                    break

            if has_evidence:
                verified_findings.append({
                    "agent": agent_name,
                    "type": finding_type,
                    "finding": finding_text,
                    "verified": True,
                    "note": "Finding supported by tool evidence"
                })
            else:
                # Check raw data directly — look for numbers/values from the finding
                found_in_raw = False
                finding_lower = finding_text.lower()
                for raw_key, raw_val in raw_data.items():
                    if isinstance(raw_val, dict):
                        for k, v in raw_val.items():
                            if isinstance(v, (int, float)) and v != 0 and str(v) in finding_text:
                                found_in_raw = True
                                break
                            if isinstance(v, bool) and v:
                                # Check if the finding mentions this key
                                if k.replace("_", " ") in finding_lower or k in finding_lower:
                                    found_in_raw = True
                                    break
                    if found_in_raw:
                        break

                if found_in_raw:
                    verified_findings.append({
                        "agent": agent_name,
                        "type": finding_type,
                        "finding": finding_text,
                        "verified": True,
                        "note": "Finding verified against raw data"
                    })
                else:
                    flagged_findings.append({
                        "agent": agent_name,
                        "type": finding_type,
                        "finding": finding_text,
                        "verified": False,
                        "note": "Finding could not be verified against raw data"
                    })

    total = len(verified_findings) + len(flagged_findings)
    logger.log_thought(
        f"Verification complete: {len(verified_findings)} verified, "
        f"{len(flagged_findings)} flagged as unverified out of {total} total"
    )

    if flagged_findings:
        logger.log_feedback(
            f"Found {len(flagged_findings)} unverified findings. These will be "
            f"marked as lower confidence in the final report.",
            "verification_agent"
        )

    return {
        "verified_findings": verified_findings,
        "flagged_findings": flagged_findings,
        "total_checked": total,
        "verification_rate": len(verified_findings) / total if total > 0 else 1.0,
    }


# ─── Orchestrator Agent ───

def run_advanced(repo_path: str, llm_call_fn=None) -> dict:
    """
    Run the advanced multi-agent assessment on a repository.

    The orchestrator coordinates:
    1. Four specialist agents run in parallel (structure, test, code quality, maintenance)
    2. Verification agent cross-checks findings
    3. Orchestrator synthesizes the final report
    """
    logger = TrajectoryLogger("advanced_orchestrator")

    logger.log_instruction(
        f"Assess the quality of repository at {repo_path} using a multi-agent "
        f"approach with specialized agents, real tools, and verification."
    )

    start_time = time.time()

    # Phase 1: Run specialist agents in parallel
    logger.log_thought("Launching 4 specialist agents in parallel: structure, test, code_quality, maintenance")

    specialist_results = []

    sub_loggers = {
        "structure": TrajectoryLogger("advanced_structure"),
        "test": TrajectoryLogger("advanced_test"),
        "code_quality": TrajectoryLogger("advanced_code_quality"),
        "maintenance": TrajectoryLogger("advanced_maintenance"),
    }

    agent_map = {
        "structure": structure_agent,
        "test": test_agent,
        "code_quality": code_quality_agent,
        "maintenance": maintenance_agent,
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for name, agent_fn in agent_map.items():
            future = executor.submit(agent_fn, repo_path, sub_loggers[name])
            futures[future] = name

        for future in concurrent.futures.as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                specialist_results.append(result)
                logger.log_tool_call(
                    f"{agent_name}_agent",
                    {"repo_path": repo_path},
                    {"score": result["score"], "findings_count": len(result["findings"])}
                )
            except Exception as e:
                logger.log_retry(f"{agent_name}_agent failed: {e}", 1)
                # Failed agents get a low score, not a neutral 5
                specialist_results.append({
                    "agent": agent_name,
                    "dimension": agent_name.replace("_", " ").title(),
                    "score": 2,
                    "findings": [("weakness", f"Agent failed with error: {e}")],
                    "evidence": [],
                    "raw_data": {},
                    "error": str(e),
                })

    # Save sub-trajectories
    for name, sub_logger in sub_loggers.items():
        sub_logger.save()

    # Phase 2: Verification
    logger.log_thought("Running verification agent to cross-check specialist findings")
    verification = verification_agent(specialist_results, logger)
    logger.log_tool_call("verification_agent", {"specialist_count": len(specialist_results)}, verification)

    # Phase 3: Synthesize final report
    logger.log_thought("Synthesizing final quality report from specialist findings")

    # Calculate weighted overall score
    weights = {
        "structure": 0.20,
        "test": 0.30,
        "code_quality": 0.30,
        "maintenance": 0.20,
    }

    weighted_score = 0
    for result in specialist_results:
        agent = result["agent"]
        w = weights.get(agent, 0.25)
        weighted_score += result["score"] * w

    overall_score = round(weighted_score)

    # Collect all findings
    all_strengths = []
    all_weaknesses = []
    all_evidence = []

    for result in specialist_results:
        for finding_type, finding_text in result.get("findings", []):
            if finding_type == "strength":
                all_strengths.append(f"[{result['dimension']}] {finding_text}")
            else:
                all_weaknesses.append(f"[{result['dimension']}] {finding_text}")
        all_evidence.extend(result.get("evidence", []))

    # Determine quality tier and recommendation
    if overall_score >= 8:
        tier, rec = "platinum", "adopt"
    elif overall_score >= 6:
        tier, rec = "gold", "adopt"
    elif overall_score >= 4:
        tier, rec = "silver", "investigate"
    else:
        tier, rec = "bronze", "avoid"

    # Build dimension scores
    dimension_scores = {}
    for result in specialist_results:
        dimension_scores[result["dimension"]] = result["score"]

    # Build summary
    summary = (
        f"Repository assessed across {len(specialist_results)} dimensions "
        f"using specialized agents with real code analysis tools. "
        f"Overall score: {overall_score}/10 ({tier}). "
        f"{len(all_strengths)} strengths and {len(all_weaknesses)} weaknesses identified. "
        f"Verification rate: {verification['verification_rate']:.0%}."
    )

    # Identify main failure mode
    main_failure = None
    if verification["flagged_findings"]:
        main_failure = f"{len(verification['flagged_findings'])} findings could not be verified against raw data"
    else:
        min_dim = min(dimension_scores, key=dimension_scores.get) if dimension_scores else "unknown"
        min_score = dimension_scores.get(min_dim, 10)
        if min_score < 5:
            main_failure = f"Weakest dimension: {min_dim} (score {min_score}/10)"

    elapsed = time.time() - start_time

    assessment = {
        "overall_score": overall_score,
        "quality_tier": tier,
        "summary": summary,
        "strengths": all_strengths,
        "weaknesses": all_weaknesses,
        "recommendation": rec,
        "confidence": "high" if verification["verification_rate"] > 0.8 else "medium",
        "method": "multi_agent_with_tools_and_verification",
        "dimension_scores": dimension_scores,
        "evidence_count": len(all_evidence),
        "evidence": all_evidence,
        "verification": {
            "verified_count": len(verification["verified_findings"]),
            "flagged_count": len(verification["flagged_findings"]),
            "verification_rate": round(verification["verification_rate"], 3),
            "flagged_details": verification["flagged_findings"][:5],
        },
        "main_failure_mode": main_failure,
        "elapsed_seconds": round(elapsed, 2),
        "agents_used": [r["agent"] for r in specialist_results] + ["verification", "orchestrator"],
    }

    logger.log_result(assessment)
    traj_path = logger.save()
    assessment["_trajectory"] = traj_path

    return assessment


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.advanced <repo_path>")
        sys.exit(1)
    result = run_advanced(sys.argv[1])
    print(json.dumps(result, indent=2, default=str))
