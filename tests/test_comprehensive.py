"""Comprehensive test suite for RepoAssess.

Tests Phase 2 pipeline, Phase 3 baseline, Phase 4 advanced evaluation,
Phase 5 benchmark, CLI, and validation tests.
"""
import os
import sys
import json
import tempfile
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_repo():
    """Create a sample repository for testing."""
    with tempfile.TemporaryDirectory() as repo_path:
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write("# Test Project\n\nA test project.\n\n## Usage\n\n```python\nimport test\n```\n")
        os.makedirs(os.path.join(repo_path, "src"))
        with open(os.path.join(repo_path, "src/app.py"), "w") as f:
            f.write('"""App module."""\n\ndef app():\n    """Return True."""\n    return True\n')
        os.makedirs(os.path.join(repo_path, "tests"))
        with open(os.path.join(repo_path, "tests/test_app.py"), "w") as f:
            f.write('from src.app import app\n\ndef test_app():\n    assert app() == True\n')
        with open(os.path.join(repo_path, "tests/__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(repo_path, "pyproject.toml"), "w") as f:
            f.write('[project]\nname = "test"\nversion = "0.1.0"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
        import subprocess
        try:
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, timeout=5)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, capture_output=True, timeout=5)
        except:
            pass
        yield repo_path


@pytest.fixture
def empty_repo():
    with tempfile.TemporaryDirectory() as repo_path:
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write("# Empty\n")
        yield repo_path


class TestPhase2:
    def test_pipeline_imports(self):
        from src.phase2.pipeline import Pipeline
        assert Pipeline is not None

    def test_pipeline_runs(self, sample_repo):
        from src.phase2.pipeline import Pipeline
        pipeline = Pipeline(sample_repo)
        report = pipeline.run()
        assert report is not None
        assert "tool_results" in report
        assert len(report["tool_results"]) > 0

    def test_pipeline_produces_context(self, sample_repo):
        from src.phase2.pipeline import Pipeline
        pipeline = Pipeline(sample_repo)
        report = pipeline.run()
        assert "context" in report or "repository" in report or "analysis_metadata" in report

    def test_pipeline_detects_readme(self, sample_repo):
        from src.phase2.pipeline import Pipeline
        pipeline = Pipeline(sample_repo)
        report = pipeline.run()
        tool_names = [tr.get("tool_name", "") for tr in report["tool_results"]]
        assert any("doc" in name.lower() or "readme" in name.lower() for name in tool_names)

    def test_pipeline_detects_tests(self, sample_repo):
        from src.phase2.pipeline import Pipeline
        pipeline = Pipeline(sample_repo)
        report = pipeline.run()
        tool_names = [tr.get("tool_name", "") for tr in report["tool_results"]]
        assert any("test" in name.lower() for name in tool_names)


class TestPhase3:
    def test_baseline_imports(self):
        from src.phase3.baseline import evaluate_baseline
        assert evaluate_baseline is not None

    def test_baseline_runs(self, sample_repo):
        from src.phase3.baseline import evaluate_baseline
        result = evaluate_baseline(sample_repo)
        assert "score" in result
        assert 0 <= result["score"] <= 10

    def test_baseline_has_uncertainty(self, sample_repo):
        from src.phase3.baseline import evaluate_baseline
        result = evaluate_baseline(sample_repo)
        assert "uncertainty" in result or "known_unknowns" in result

    def test_baseline_empty_repo(self, empty_repo):
        from src.phase3.baseline import evaluate_baseline
        result = evaluate_baseline(empty_repo)
        assert result["score"] < 5


class TestPhase4:
    def test_advanced_imports(self):
        from src.phase4.advanced import evaluate_advanced
        assert evaluate_advanced is not None

    def test_advanced_runs(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_advanced_has_verification(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert "verification_rate" in result
        assert "verification_metrics" in result

    def test_advanced_has_remediation(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert "remediation_plan" in result
        assert isinstance(result["remediation_plan"], list)

    def test_advanced_has_evidence_graph(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert "evidence_graph" in result
        assert "dimensions" in result["evidence_graph"]

    def test_advanced_has_score_explanation(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert "score_explanation" in result

    def test_advanced_has_recommendation(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert result["recommendation"] in ("ADOPT", "INVESTIGATE", "AVOID")

    def test_advanced_has_grade(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert result["grade"] in ("A", "A-", "B+", "B", "B-", "C+", "C", "F")

    def test_no_verification_differs(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced, evaluate_advanced_no_verification
        with_v = evaluate_advanced(sample_repo)
        without_v = evaluate_advanced_no_verification(sample_repo)
        assert with_v["score"] != without_v["score"] or with_v["confidence"] != without_v["confidence"]

    def test_profile_weights(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo, profile="LIBRARY")
        assert "weights" in result

    def test_verification_details(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        details = result.get("verification_details", [])
        assert len(details) > 0
        for v in details:
            assert "status" in v
            assert "claim" in v
            assert v["status"] in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED", "UNKNOWN")


class TestPhase5:
    def test_ground_truth_imports(self):
        from src.phase5.ground_truth import GROUND_TRUTH, SCORING_RUBRICS
        assert len(GROUND_TRUTH) == 25
        assert len(SCORING_RUBRICS) >= 6

    def test_repo_generators(self):
        from src.phase5.repos import REPO_GENERATORS
        assert len(REPO_GENERATORS) == 25

    def test_generate_repos(self):
        from src.phase5.repos import generate_all_repos
        import tempfile
        with tempfile.TemporaryDirectory() as base:
            repos = generate_all_repos(base)
            assert len(repos) == 25
            for name, path in repos.items():
                assert os.path.isdir(path)
                assert os.path.exists(os.path.join(path, ".ground_truth.json"))

    def test_benchmark_metrics(self):
        from src.phase5.benchmark import mean_absolute_error, pearson_correlation, spearman_correlation
        assert mean_absolute_error([1, 2, 3], [1, 2, 3]) == 0.0
        assert abs(pearson_correlation([1, 2, 3], [1, 2, 3]) - 1.0) < 0.01
        assert abs(spearman_correlation([1, 2, 3], [1, 2, 3]) - 1.0) < 0.01

    def test_pairwise_ranking(self):
        from src.phase5.benchmark import pairwise_ranking_accuracy
        assert pairwise_ranking_accuracy([1, 2, 3], [1, 2, 3]) == 1.0
        assert pairwise_ranking_accuracy([3, 2, 1], [1, 2, 3]) == 0.0


class TestValidation:
    def test_verification_affects_score(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced, evaluate_advanced_no_verification
        with_v = evaluate_advanced(sample_repo)
        without_v = evaluate_advanced_no_verification(sample_repo)
        score_diff = abs(with_v["score"] - without_v["score"])
        conf_diff = abs(with_v["confidence"] - without_v["confidence"])
        assert score_diff > 0.1 or conf_diff > 0.01, "Verification must affect the outcome"

    def test_caused_by_secret(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        orig = evaluate_advanced(sample_repo)["score"]
        secret_path = os.path.join(sample_repo, "secret.txt")
        with open(secret_path, "w") as f:
            f.write("API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890\n")
        with_secret = evaluate_advanced(sample_repo)["score"]
        os.remove(secret_path)
        assert with_secret <= orig, "Adding a secret should not increase the score"

    def test_score_in_valid_range(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert 0 <= result["score"] <= 100

    def test_confidence_in_valid_range(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert 0 <= result["confidence"] <= 1.0

    def test_evidence_coverage_in_valid_range(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        assert 0 <= result["evidence_coverage"] <= 1.0

    def test_remediation_plan_has_priorities(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        for item in result["remediation_plan"]:
            assert item["priority"] in ("P0", "P1", "P2", "P3")

    def test_json_serializable(self, sample_repo):
        from src.phase4.orchestrator import evaluate_advanced
        result = evaluate_advanced(sample_repo)
        json.dumps(result, default=str)
