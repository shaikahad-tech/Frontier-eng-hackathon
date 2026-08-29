"""Phase 5 — Ground Truth Manifests and Scoring Rubrics

Machine-readable ground truth for each synthetic repository.
Ground truth is created BEFORE evaluation — the evaluator never modifies it.

Includes:
- SCORING_RUBRICS: Written rubrics for each qualitative dimension (0-10 scale)
- GROUND_TRUTH: Per-repo ground truth with overall + per-dimension scores and known_conditions
- 15 repositories (12 standard + 3 adversarial)

Ground truth types:
- FACTUAL: e.g., "pytest has 37 tests" — deterministic
- QUALITY JUDGMENT: e.g., "Test quality = 7/10" — requires rubric
"""
from __future__ import annotations
from typing import Any


# ═══════════════════════════════════════════════════════════════
# SCORING RUBRICS — Written rubrics for each dimension (0-10 scale)
# ═══════════════════════════════════════════════════════════════

SCORING_RUBRICS = {
    "testing": {
        "0-1": "No meaningful automated testing.",
        "2-3": "Tests exist but weak or mostly unverified.",
        "4-5": "Basic automated testing.",
        "6-7": "Strong automated testing with meaningful coverage.",
        "8-9": "Comprehensive tests including multiple layers and CI enforcement.",
        "10": "Excellent coverage, meaningful assertions, reliable execution, appropriate test layering.",
    },
    "security": {
        "0-1": "Critical vulnerabilities, committed secrets, no security awareness.",
        "2-3": "Multiple high-severity issues, no security tooling.",
        "4-5": "Some security measures but gaps remain.",
        "6-7": "Good security practices, minor issues only.",
        "8-9": "Strong security posture with tooling and no critical issues.",
        "10": "Excellent security — verified, scanned, no secrets, defense in depth.",
    },
    "documentation": {
        "0-1": "No README or documentation.",
        "2-3": "Minimal README, no structure.",
        "4-5": "Basic README with installation and usage.",
        "6-7": "Comprehensive docs with examples and API docs.",
        "8-9": "Excellent documentation with tutorials, API reference, architecture docs.",
        "10": "World-class documentation — complete, accurate, well-organized, with examples.",
    },
    "maintenance": {
        "0-1": "Abandoned repository, no commits in years.",
        "2-3": "Stale, minimal activity, no releases.",
        "4-5": "Occasional updates, basic maintenance.",
        "6-7": "Active maintenance, regular updates, releases.",
        "8-9": "Excellent maintenance — frequent updates, multiple contributors, regular releases.",
        "10": "Exceptional maintenance — active community, regular releases, responsive maintainers.",
    },
    "code_quality": {
        "0-1": "Severe quality issues — high complexity, no linting, dead code, duplication.",
        "2-3": "Poor quality — high complexity, no tooling, significant tech debt.",
        "4-5": "Moderate quality — some issues but manageable.",
        "6-7": "Good quality — linting configured, reasonable complexity, low tech debt.",
        "8-9": "Excellent quality — strong tooling, low complexity, minimal debt.",
        "10": "Exceptional — comprehensive tooling, very low complexity, no debt.",
    },
    "structure": {
        "0-1": "No organization, files scattered, no packaging.",
        "2-3": "Poor structure, minimal organization.",
        "4-5": "Basic structure with src/tests separation.",
        "6-7": "Good structure with packaging and CI.",
        "8-9": "Excellent structure — clear separation, packaging, Docker, CI.",
        "10": "Exceptional — well-organized, packaged, containerized, CI/CD, reproducible.",
    },
}


# ═══════════════════════════════════════════════════════════════
# GROUND TRUTH — Per-repo scores and known conditions
# Created BEFORE evaluation — evaluator never modifies these
# ═══════════════════════════════════════════════════════════════

GROUND_TRUTH = {
    "repo_01": {
        "repository": "repo_01", "neutral_id": "repository_001",
        "description": "Excellent across every dimension",
        "ground_truth": {"overall": 9.0, "testing": 9.0, "security": 9.0, "documentation": 9.0,
                        "maintenance": 8.5, "code_quality": 9.0, "structure": 9.0},
        "known_conditions": ["comprehensive_tests", "no_security_issues", "excellent_docs",
                            "active_maintenance", "low_complexity", "proper_packaging"],
    },
    "repo_02": {
        "repository": "repo_02", "neutral_id": "repository_002",
        "description": "Excellent documentation but terrible code",
        "ground_truth": {"overall": 4.0, "testing": 1.0, "security": 2.0, "documentation": 9.5,
                        "maintenance": 3.0, "code_quality": 2.0, "structure": 5.0},
        "known_conditions": ["excellent_docs", "no_tests", "high_complexity", "security_issues"],
    },
    "repo_03": {
        "repository": "repo_03", "neutral_id": "repository_003",
        "description": "Excellent code but almost no documentation",
        "ground_truth": {"overall": 6.5, "testing": 8.0, "security": 8.0, "documentation": 1.5,
                        "maintenance": 7.0, "code_quality": 8.5, "structure": 6.0},
        "known_conditions": ["good_tests", "no_security_issues", "minimal_docs",
                            "active_maintenance", "low_complexity"],
    },
    "repo_04": {
        "repository": "repo_04", "neutral_id": "repository_004",
        "description": "Many tests but tests mostly meaningless",
        "ground_truth": {"overall": 3.5, "testing": 3.0, "security": 5.0, "documentation": 6.0,
                        "maintenance": 5.0, "code_quality": 4.0, "structure": 5.0},
        "known_conditions": ["many_trivial_tests", "low_coverage_real", "moderate_docs"],
    },
    "repo_05": {
        "repository": "repo_05", "neutral_id": "repository_005",
        "description": "Few tests but very strong tests",
        "ground_truth": {"overall": 7.0, "testing": 7.5, "security": 7.0, "documentation": 6.0,
                        "maintenance": 6.5, "code_quality": 7.0, "structure": 7.0},
        "known_conditions": ["few_meaningful_tests", "high_assertion_quality", "good_docs"],
    },
    "repo_06": {
        "repository": "repo_06", "neutral_id": "repository_006",
        "description": "High complexity but otherwise healthy",
        "ground_truth": {"overall": 6.0, "testing": 7.0, "security": 7.0, "documentation": 7.0,
                        "maintenance": 6.0, "code_quality": 4.0, "structure": 7.0},
        "known_conditions": ["high_complexity", "good_tests", "no_security_issues", "good_docs"],
    },
    "repo_07": {
        "repository": "repo_07", "neutral_id": "repository_007",
        "description": "Low complexity but severe security issues",
        "ground_truth": {"overall": 4.2, "testing": 7.0, "security": 1.5, "documentation": 8.0,
                        "maintenance": 5.0, "code_quality": 5.5, "structure": 6.0},
        "known_conditions": ["critical_command_injection", "good_test_suite", "good_documentation"],
    },
    "repo_08": {
        "repository": "repo_08", "neutral_id": "repository_008",
        "description": "Good repository with broken CI",
        "ground_truth": {"overall": 6.0, "testing": 6.5, "security": 7.0, "documentation": 7.0,
                        "maintenance": 4.0, "code_quality": 7.0, "structure": 6.5},
        "known_conditions": ["broken_ci", "passing_tests_locally", "good_docs"],
    },
    "repo_09": {
        "repository": "repo_09", "neutral_id": "repository_009",
        "description": "Good repository with dependency vulnerabilities",
        "ground_truth": {"overall": 5.5, "testing": 7.0, "security": 3.0, "documentation": 7.0,
                        "maintenance": 6.0, "code_quality": 7.0, "structure": 7.0},
        "known_conditions": ["vulnerable_dependencies", "good_tests", "good_docs"],
    },
    "repo_10": {
        "repository": "repo_10", "neutral_id": "repository_010",
        "description": "Healthy code but abandoned Git history",
        "ground_truth": {"overall": 5.0, "testing": 7.0, "security": 7.0, "documentation": 6.0,
                        "maintenance": 1.5, "code_quality": 7.0, "structure": 6.0},
        "known_conditions": ["abandoned_git", "good_code", "no_recent_commits"],
    },
    "repo_11": {
        "repository": "repo_11", "neutral_id": "repository_011",
        "description": "Active repository with poor architecture",
        "ground_truth": {"overall": 4.5, "testing": 5.0, "security": 5.0, "documentation": 5.0,
                        "maintenance": 7.0, "code_quality": 4.0, "structure": 3.0},
        "known_conditions": ["active_git", "poor_structure", "flat_directory", "mixed_concerns"],
    },
    "repo_12": {
        "repository": "repo_12", "neutral_id": "repository_012",
        "description": "Surface-perfect repository with hidden severe problems",
        "ground_truth": {"overall": 3.0, "testing": 2.0, "security": 1.0, "documentation": 9.0,
                        "maintenance": 8.0, "code_quality": 2.0, "structure": 8.0},
        "known_conditions": ["surface_camouflage", "hidden_secrets", "fake_ci",
                            "trivial_tests", "polished_readme"],
    },
    # ── Adversarial cases ──
    "repo_13": {
        "repository": "repo_13", "neutral_id": "repository_013",
        "description": "Adversarial: Fake quality (enormous README, meaningless tests, fake CI)",
        "ground_truth": {"overall": 2.5, "testing": 1.5, "security": 4.0, "documentation": 3.0,
                        "maintenance": 3.0, "code_quality": 2.0, "structure": 4.0},
        "known_conditions": ["enormous_readme", "meaningless_tests", "fake_ci", "excessive_comments"],
    },
    "repo_14": {
        "repository": "repo_14", "neutral_id": "repository_014",
        "description": "Adversarial: Security camouflage (vulnerable code behind helpers, encoded strings)",
        "ground_truth": {"overall": 3.5, "testing": 6.0, "security": 1.0, "documentation": 7.0,
                        "maintenance": 6.0, "code_quality": 4.0, "structure": 6.0},
        "known_conditions": ["security_camouflage", "encoded_dangerous_strings", "helper_hidden_vuln"],
    },
    "repo_15": {
        "repository": "repo_15", "neutral_id": "repository_015",
        "description": "Adversarial: Test camouflage (hundreds of trivial tests, asserts only truthy)",
        "ground_truth": {"overall": 3.0, "testing": 2.0, "security": 5.0, "documentation": 6.0,
                        "maintenance": 5.0, "code_quality": 4.0, "structure": 5.0},
        "known_conditions": ["test_camouflage", "hundreds_trivial_tests", "asserts_truthy_only"],
    },
}
