"""
Baseline solution: A single-prompt approach to repository quality assessment.

The baseline represents the "reasonable basic way to handle the task" before
using the advanced agent solution. It reads the README and file listing,
sends a single prompt to an LLM (or uses a rule-based fallback), and gets
back a quality score.

This is what a person might do with ChatGPT: paste the README and ask
"Is this repo good quality?"

The baseline uses only two tools (read_readme, analyze_structure) and makes
a single assessment call. No multi-agent orchestration, no verification,
no code analysis, no test execution.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.trajectory_logger import TrajectoryLogger
from src.tools.repo_tools import read_readme, analyze_structure


BASELINE_PROMPT = """You are a code repository quality assessor. You have been given the README
and basic file listing of a repository. Based on this information alone, provide
a quality assessment.

Repository information:
{repo_info}

Provide your assessment as JSON with the following structure:
{{
    "overall_score": <1-10 integer>,
    "quality_tier": "<bronze|silver|gold|platinum>",
    "summary": "<one paragraph summary>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
    "recommendation": "<adopt|investigate|avoid>",
    "confidence": "<low|medium|high>"
}}

Score guide:
- 1-3: Poor quality, significant risks, avoid
- 4-5: Below average, investigate carefully before use
- 6-7: Average quality, usable with some caution
- 8-9: Good quality, safe to adopt
- 10: Excellent quality, exemplary

Base your assessment ONLY on the information provided above. Do not make
assumptions about code you cannot see."""


def run_baseline(repo_path: str, llm_call_fn=None) -> dict:
    """
    Run the baseline assessment on a repository.

    Args:
        repo_path: Path to the repository to assess.
        llm_call_fn: A function that takes a prompt string and returns the LLM response.
                     If None, uses a rule-based fallback (for offline evaluation).

    Returns:
        Assessment dict with score, strengths, weaknesses, etc.
    """
    logger = TrajectoryLogger("baseline")

    # Step 1: Read the README (the only "tool" the baseline uses)
    logger.log_instruction(
        f"Assess the quality of the repository at {repo_path} using only the README "
        "and basic file listing. Provide a score from 1-10."
    )

    readme_data = read_readme(repo_path)
    logger.log_tool_call("read_readme", {"repo_path": repo_path}, readme_data)

    structure_data = analyze_structure(repo_path)
    logger.log_tool_call("analyze_structure", {"repo_path": repo_path}, {
        "project_type": structure_data["project_type"],
        "total_files": structure_data["file_stats"]["total_files"],
        "python_file_count": structure_data["python_file_count"],
    })

    # Prepare the info given to the LLM
    repo_info = f"README:\n{readme_data.get('preview', 'No README found')[:2000]}\n\n"
    repo_info += f"Project type: {structure_data['project_type']}\n"
    repo_info += f"Total files: {structure_data['file_stats']['total_files']}\n"
    repo_info += f"Top-level entries: {[e['name'] for e in structure_data['top_level_entries'][:15]]}\n"

    # Step 2: Single LLM call or rule-based fallback
    prompt = BASELINE_PROMPT.format(repo_info=repo_info)
    logger.log_thought("Sending single prompt to LLM with README and file listing only.")

    if llm_call_fn:
        response_text = llm_call_fn(prompt)
        logger.log_tool_call("llm_call", {"prompt_length": len(prompt)}, {"response_length": len(response_text)})

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                assessment = json.loads(response_text[json_start:json_end])
            else:
                assessment = _fallback_assessment(readme_data, structure_data)
        except json.JSONDecodeError:
            assessment = _fallback_assessment(readme_data, structure_data)
            logger.log_feedback("LLM response was not valid JSON, used fallback scoring.", "self")
    else:
        # Rule-based fallback for offline evaluation
        assessment = _fallback_assessment(readme_data, structure_data)
        logger.log_tool_call("rule_based_fallback", {"reason": "no llm_call_fn provided"}, assessment)

    assessment = _ensure_fields(assessment)
    assessment["method"] = "baseline_single_prompt"

    logger.log_result(assessment)
    traj_path = logger.save()
    assessment["_trajectory"] = traj_path

    return assessment


def _ensure_fields(assessment: dict) -> dict:
    """Ensure all expected fields exist in the assessment."""
    defaults = {
        "overall_score": 5,
        "quality_tier": "silver",
        "summary": "No summary provided.",
        "strengths": [],
        "weaknesses": [],
        "recommendation": "investigate",
        "confidence": "low",
    }
    for key, default in defaults.items():
        if key not in assessment:
            assessment[key] = default
    # Clamp score to 1-10
    assessment["overall_score"] = max(1, min(10, int(assessment["overall_score"])))
    return assessment


def _fallback_assessment(readme_data: dict, structure_data: dict) -> dict:
    """
    Rule-based fallback assessment when no LLM is available.
    This is deliberately simple — it can only see surface metadata.
    """
    score = 5
    strengths = []
    weaknesses = []

    # README quality
    if readme_data.get("found"):
        strengths.append("Has a README file")
        readme_len = readme_data.get("length_chars", 0)
        if readme_len > 2000:
            score += 1
            strengths.append("README is detailed")
        elif readme_len < 200:
            weaknesses.append("README is very short")
        if readme_data.get("has_installation"):
            strengths.append("README has installation instructions")
        if readme_data.get("has_usage"):
            strengths.append("README has usage examples")
    else:
        weaknesses.append("No README file found")
        score -= 2

    # Project type detection
    if structure_data.get("project_type") != "unknown":
        strengths.append(f"Recognized project type: {structure_data['project_type']}")
    else:
        weaknesses.append("Could not determine project type")

    # File count
    total_files = structure_data.get("file_stats", {}).get("total_files", 0)
    if total_files > 50:
        strengths.append(f"Substantial codebase ({total_files} files)")
    elif total_files < 5:
        weaknesses.append("Very small codebase")

    # Dockerfile
    if structure_data.get("has_dockerfile"):
        strengths.append("Has Dockerfile for containerization")
        score += 1

    # Clamp
    score = max(1, min(10, score))

    if score >= 8:
        tier, rec = "platinum", "adopt"
    elif score >= 6:
        tier, rec = "gold", "adopt"
    elif score >= 4:
        tier, rec = "silver", "investigate"
    else:
        tier, rec = "bronze", "avoid"

    return {
        "overall_score": score,
        "quality_tier": tier,
        "summary": f"Rule-based assessment based on README presence and file structure. Score: {score}/10. "
                   f"The baseline cannot see test coverage, code complexity, or git history.",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": rec,
        "confidence": "low",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.baseline <repo_path>")
        sys.exit(1)
    result = run_baseline(sys.argv[1])
    print(json.dumps(result, indent=2))
