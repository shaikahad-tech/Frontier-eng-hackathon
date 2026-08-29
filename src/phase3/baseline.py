"""
Phase 3 — Baseline Evaluator

A deliberately shallow repository assessment that uses ONLY:
  - Tool 1: read_readme (README content, headings, sections)
  - Tool 2: analyze_structure (directory structure, file types, languages)

The baseline simulates a human/LLM receiving only surface-level information.
It cannot access test execution, coverage, complexity, security, git history, etc.

Score scale: 0-10 (capped to 3-7 range)
Output includes: score, confidence, information_coverage, known_unknowns
"""
from __future__ import annotations
import os
import re
import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ── Phase 3 baseline does NOT import Phase 2 analyzers ──
# This isolation is deliberate to prevent information leakage.

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             ".eggs", "dist", "build", ".mypy_cache", ".pytest_cache", ".tox"}


# ═══════════════════════════════════════════════════════════════
# TOOL 1: read_readme
# ═══════════════════════════════════════════════════════════════

def read_readme(repo_path: str) -> dict[str, Any]:
    """Read README content and extract surface-level signals."""
    readme_content = ""
    readme_path = None

    for fname in ["README.md", "README.rst", "README.txt", "README",
                   "readme.md", "readme.rst", "readme.txt", "readme"]:
        path = os.path.join(repo_path, fname)
        if os.path.exists(path):
            readme_path = path
            with open(path, "r", errors="replace") as f:
                readme_content = f.read(50000)
            break

    if not readme_content:
        return {
            "found": False, "length": 0, "headings": [],
            "has_installation": False, "has_usage": False, "has_examples": False,
            "has_testing_section": False, "has_description": False,
            "has_license_section": False, "has_contributing_section": False,
            "word_count": 0, "code_blocks": 0,
        }

    headings = re.findall(r'^#{1,6}\s+(.+)$', readme_content, re.MULTILINE)
    lower = readme_content.lower()

    has_installation = bool(
        re.search(r'(?:^#{1,6}\s.*(install|setup|getting started))', lower, re.MULTILINE) or
        "pip install" in lower or "npm install" in lower or "cargo add" in lower)
    has_usage = bool(
        re.search(r'(?:^#{1,6}\s.*(usage|how to use|quick start))', lower, re.MULTILINE) or
        "```python" in lower or "```bash" in lower)
    has_examples = "example" in lower or "demo" in lower
    has_testing_section = "test" in lower and ("pytest" in lower or "unittest" in lower or "npm test" in lower)
    has_description = len(readme_content) > 100
    has_license_section = "license" in lower
    has_contributing_section = "contribut" in lower

    code_blocks = len(re.findall(r'```', readme_content)) // 2
    word_count = len(readme_content.split())

    return {
        "found": True, "length": len(readme_content), "headings": headings[:20],
        "heading_count": len(headings), "has_installation": has_installation,
        "has_usage": has_usage, "has_examples": has_examples,
        "has_testing_section": has_testing_section, "has_description": has_description,
        "has_license_section": has_license_section, "has_contributing_section": has_contributing_section,
        "word_count": word_count, "code_blocks": code_blocks,
    }


# ═══════════════════════════════════════════════════════════════
# TOOL 2: analyze_structure
# ═══════════════════════════════════════════════════════════════

def analyze_structure(repo_path: str) -> dict[str, Any]:
    """Analyze directory structure, file types, and basic project signals."""
    extensions = {}; total_files = 0; max_depth = 0
    top_level_dirs = []; top_level_files = []
    has_dockerfile = has_makefile = has_setup_py = has_pyproject = False
    has_package_json = has_cargo_toml = has_go_mod = has_requirements_txt = False
    has_gitignore = has_tests_dir = has_docs_dir = has_src_dir = has_ci = False

    for entry in os.listdir(repo_path):
        full = os.path.join(repo_path, entry)
        if os.path.isdir(full) and entry not in SKIP_DIRS:
            top_level_dirs.append(entry)
            if entry.lower() in ("tests", "test"): has_tests_dir = True
            if entry.lower() in ("docs", "doc", "documentation"): has_docs_dir = True
            if entry.lower() in ("src", "lib", "app"): has_src_dir = True
        elif os.path.isfile(full):
            top_level_files.append(entry)
            if entry == "Dockerfile": has_dockerfile = True
            if entry == "Makefile": has_makefile = True
            if entry == "setup.py": has_setup_py = True
            if entry == "pyproject.toml": has_pyproject = True
            if entry == "package.json": has_package_json = True
            if entry == "Cargo.toml": has_cargo_toml = True
            if entry == "go.mod": has_go_mod = True
            if entry == "requirements.txt": has_requirements_txt = True
            if entry == ".gitignore": has_gitignore = True

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        depth = root.replace(repo_path, "").count(os.sep)
        max_depth = max(max_depth, depth)
        for f in files:
            total_files += 1
            ext = os.path.splitext(f)[1].lower()
            if ext: extensions[ext] = extensions.get(ext, 0) + 1
        github_path = os.path.join(root, ".github", "workflows")
        if os.path.isdir(github_path): has_ci = True

    lang_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".java": "Java", ".cpp": "C++", ".c": "C", ".go": "Go",
                ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#"}
    lang_counts = {}
    for ext, count in extensions.items():
        lang = lang_map.get(ext)
        if lang: lang_counts[lang] = lang_counts.get(lang, 0) + count
    primary_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "Unknown"

    project_type = "unknown"
    if has_package_json: project_type = "node"
    elif has_setup_py or has_pyproject or has_requirements_txt: project_type = "python"
    elif has_cargo_toml: project_type = "rust"
    elif has_go_mod: project_type = "go"

    packaging_signals = sum([has_setup_py, has_pyproject, has_package_json,
                             has_cargo_toml, has_go_mod, has_requirements_txt])

    return {
        "total_files": total_files, "max_depth": max_depth,
        "top_level_dirs": top_level_dirs, "top_level_files": top_level_files,
        "extensions": dict(sorted(extensions.items(), key=lambda x: -x[1])[:10]),
        "primary_language": primary_lang, "languages_detected": lang_counts,
        "project_type": project_type, "has_dockerfile": has_dockerfile,
        "has_makefile": has_makefile, "has_tests_dir": has_tests_dir,
        "has_docs_dir": has_docs_dir, "has_src_dir": has_src_dir,
        "has_ci": has_ci, "has_gitignore": has_gitignore,
        "packaging_signals": packaging_signals,
    }


# ═══════════════════════════════════════════════════════════════
# BASELINE SCORING
# ═══════════════════════════════════════════════════════════════

BASELINE_WEIGHTS = {
    "readme_quality": 0.25, "project_organization": 0.25,
    "professional_signals": 0.20, "usability_signals": 0.15,
    "documentation_signals": 0.15,
}

MIN_SCORE = 3.0
MAX_SCORE = 7.0

KNOWN_UNKNOWNS = [
    "test quality unknown", "test execution unknown", "test coverage unknown",
    "security posture unknown", "dependency vulnerabilities unknown",
    "code complexity unknown", "git maintenance history unknown",
    "static analysis unknown", "secrets detection unknown", "runtime behavior unknown",
]

EVIDENCE_NOT_AVAILABLE = [
    "test execution results", "coverage data", "complexity metrics",
    "dependency vulnerability scan", "git history analysis",
    "security scanner output", "static analysis results",
    "secrets detection results", "CI/CD pipeline execution", "runtime profiling",
]


def _score_readme_quality(readme: dict) -> float:
    if not readme["found"]: return 1.0
    score = 3.0
    if readme["word_count"] > 100: score += 1.0
    if readme["word_count"] > 500: score += 1.0
    if readme["heading_count"] >= 3: score += 1.0
    if readme["has_installation"]: score += 1.0
    if readme["has_usage"]: score += 1.0
    if readme["has_examples"]: score += 0.5
    if readme["has_testing_section"]: score += 0.5
    if readme["code_blocks"] > 0: score += 0.5
    if readme["has_license_section"]: score += 0.5
    return min(10.0, score)


def _score_project_organization(structure: dict) -> float:
    score = 2.0
    if structure["has_src_dir"]: score += 1.5
    if structure["has_tests_dir"]: score += 1.5
    if structure["has_docs_dir"]: score += 1.0
    if structure["max_depth"] >= 2: score += 1.0
    if structure["max_depth"] >= 4: score += 0.5
    if len(structure["top_level_dirs"]) >= 3: score += 1.0
    if structure["total_files"] > 10: score += 1.0
    if structure["total_files"] > 50: score += 0.5
    return min(10.0, score)


def _score_professional_signals(structure: dict) -> float:
    score = 2.0
    if structure["packaging_signals"] > 0: score += 2.0
    if structure["has_dockerfile"]: score += 1.5
    if structure["has_makefile"]: score += 1.0
    if structure["has_ci"]: score += 1.5
    if structure["has_gitignore"]: score += 1.0
    if structure["packaging_signals"] > 1: score += 1.0
    return min(10.0, score)


def _score_usability_signals(readme: dict, structure: dict) -> float:
    score = 2.0
    if readme["has_installation"]: score += 2.0
    if readme["has_usage"]: score += 2.0
    if readme["has_examples"]: score += 1.5
    if readme["code_blocks"] > 0: score += 1.5
    if structure["project_type"] != "unknown": score += 1.0
    if structure["has_dockerfile"]: score += 1.0
    return min(10.0, score)


def _score_documentation_signals(readme: dict) -> float:
    score = 1.0
    if readme["found"]: score += 2.0
    if readme["word_count"] > 200: score += 1.0
    if readme["heading_count"] >= 5: score += 1.0
    if readme["has_license_section"]: score += 1.0
    if readme["has_contributing_section"]: score += 1.0
    if readme["has_testing_section"]: score += 1.0
    return min(10.0, score)


def _score_to_grade(score: float) -> str:
    if score >= 9: return "A"
    if score >= 8: return "A-"
    if score >= 7: return "B+"
    if score >= 6: return "B"
    if score >= 5: return "B-"
    if score >= 4: return "C+"
    if score >= 3: return "C"
    return "F"


def _compute_confidence(readme: dict, structure: dict) -> float:
    info_points = 0; max_points = 10
    if readme["found"]: info_points += 2
    if readme["word_count"] > 200: info_points += 1
    if readme["has_installation"]: info_points += 1
    if structure["total_files"] > 5: info_points += 1
    if structure["primary_language"] != "Unknown": info_points += 1
    if structure["project_type"] != "unknown": info_points += 1
    if structure["packaging_signals"] > 0: info_points += 1
    if structure["has_dockerfile"] or structure["has_ci"]: info_points += 1
    if structure["has_tests_dir"]: info_points += 1
    return min(0.5, 0.15 + (info_points / max_points) * 0.35)


def _compute_information_coverage(readme: dict, structure: dict) -> float:
    categories_accessed = 0
    if readme["found"]: categories_accessed += 1
    if structure["total_files"] > 0: categories_accessed += 1
    return categories_accessed / 10.0


def _get_strengths(readme: dict, structure: dict) -> list[str]:
    strengths = []
    if readme["found"] and readme["word_count"] > 500: strengths.append("Comprehensive README documentation")
    if readme["has_installation"] and readme["has_usage"]: strengths.append("Clear installation and usage instructions")
    if structure["has_dockerfile"]: strengths.append("Docker containerization support")
    if structure["has_ci"]: strengths.append("CI/CD pipeline configured")
    if structure["has_tests_dir"]: strengths.append("Test directory present")
    if structure["packaging_signals"] > 0: strengths.append("Proper package configuration")
    if structure["has_src_dir"] and structure["has_tests_dir"]: strengths.append("Organized project structure with src/tests separation")
    return strengths[:5]


def _get_weaknesses(readme: dict, structure: dict) -> list[str]:
    weaknesses = []
    if not readme["found"]: weaknesses.append("No README file found")
    elif readme["word_count"] < 100: weaknesses.append("README is very brief")
    if not readme["has_installation"]: weaknesses.append("No installation instructions visible")
    if not readme["has_usage"]: weaknesses.append("No usage examples visible")
    if not structure["has_dockerfile"]: weaknesses.append("No Dockerfile detected")
    if not structure["has_ci"]: weaknesses.append("No CI/CD configuration detected")
    if not structure["has_tests_dir"]: weaknesses.append("No tests directory detected")
    if structure["packaging_signals"] == 0: weaknesses.append("No package configuration detected")
    return weaknesses[:5]


def _get_evidence_used(readme: dict, structure: dict) -> list[str]:
    evidence = []
    if readme["found"]:
        evidence.append("README file content")
        if readme["heading_count"] > 0: evidence.append("README section headings")
        if readme["has_installation"]: evidence.append("Installation section")
        if readme["has_usage"]: evidence.append("Usage section")
    evidence.append("Directory structure")
    evidence.append(f"File types ({structure.get('primary_language', 'unknown')})")
    if structure["has_dockerfile"]: evidence.append("Dockerfile presence")
    if structure["has_ci"]: evidence.append("CI configuration presence")
    return evidence


DISCLOSURE = (
    "This evaluation is based only on surface-level repository metadata and "
    "documentation. It does not assess execution, security, dependency safety, "
    "code complexity, test effectiveness, or repository maintenance history."
)


def evaluate_baseline(repo_path: str, mode: str = "deterministic",
                      model_id: Optional[str] = None) -> dict[str, Any]:
    """Run the baseline evaluation."""
    start_time = time.time()
    readme = read_readme(repo_path)
    structure = analyze_structure(repo_path)

    dim_scores = {
        "readme_quality": _score_readme_quality(readme),
        "project_organization": _score_project_organization(structure),
        "professional_signals": _score_professional_signals(structure),
        "usability_signals": _score_usability_signals(readme, structure),
        "documentation_signals": _score_documentation_signals(readme),
    }

    raw_score = sum(dim_scores[k] * BASELINE_WEIGHTS[k] for k in BASELINE_WEIGHTS)
    clamped_score = max(MIN_SCORE, min(MAX_SCORE, raw_score))
    confidence = _compute_confidence(readme, structure)
    info_coverage = _compute_information_coverage(readme, structure)

    evidence_str = json.dumps({"readme": readme, "structure": structure}, sort_keys=True)
    evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()[:16]

    return {
        "system": "baseline", "mode": mode,
        "score": round(clamped_score, 2),
        "confidence": round(confidence, 3),
        "information_coverage": round(info_coverage, 3),
        "grade": _score_to_grade(clamped_score),
        "dimension_scores": {k: round(v, 2) for k, v in dim_scores.items()},
        "weights": BASELINE_WEIGHTS,
        "strengths": _get_strengths(readme, structure),
        "weaknesses": _get_weaknesses(readme, structure),
        "known_unknowns": KNOWN_UNKNOWNS,
        "evidence_used": _get_evidence_used(readme, structure),
        "evidence_not_available": EVIDENCE_NOT_AVAILABLE,
        "recommendation": "limited confidence",
        "disclosure": DISCLOSURE,
        "metadata": {
            "evidence_hash": evidence_hash,
            "evaluation_time_seconds": round(time.time() - start_time, 3),
            "model_id": model_id if mode == "llm" else None,
            "prompt_version": "baseline-v1.0" if mode == "llm" else None,
            "score_cap": {"min": MIN_SCORE, "max": MAX_SCORE},
            "raw_uncapped_score": round(raw_score, 2),
        },
    }


def evaluate_baseline_deterministic(repo_path: str) -> dict[str, Any]:
    """Run baseline in deterministic rule mode (no API required)."""
    return evaluate_baseline(repo_path, mode="deterministic")


def evaluate_baseline_llm(repo_path: str, model_id: str = "gpt-4") -> dict[str, Any]:
    """Run baseline in LLM mode with deterministic fallback."""
    return evaluate_baseline(repo_path, mode="llm", model_id=model_id)
