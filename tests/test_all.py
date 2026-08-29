"""
Test suite for RepoAssess — verifies the main components work correctly.
Tests cover tools, baseline, advanced solution, evaluation framework, and edge cases.
"""

import os
import sys
import json
import tempfile
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.tools.repo_tools import (
    read_readme,
    analyze_structure,
    analyze_dependencies,
    analyze_tests,
    analyze_complexity,
    analyze_code_quality,
    analyze_documentation,
    analyze_git_history,
    analyze_security,
)
from src.baseline import run_baseline
from src.advanced import run_advanced
from src.trajectory_logger import TrajectoryLogger


# ─── Fixtures ───

@pytest.fixture
def sample_repo(tmp_path):
    """Create a small sample repo for testing."""
    repo = tmp_path / "sample"
    repo.mkdir()

    (repo / "README.md").write_text("# Sample Project\n\nA test project with enough text to pass the 200 char threshold. " * 5)
    (repo / "setup.py").write_text("from setuptools import setup\nsetup(name='sample')\n")
    (repo / "LICENSE").write_text("MIT License\n")

    (repo / "src").mkdir()
    (repo / "src" / "__init__.py").write_text("")
    (repo / "src" / "main.py").write_text(
        '"""Main module."""\n\n'
        'def add(a, b):\n'
        '    """Add two numbers."""\n'
        '    return a + b\n'
    )

    (repo / "tests").mkdir()
    (repo / "tests" / "test_main.py").write_text(
        'from src.main import add\n\n'
        'def test_add():\n'
        '    assert add(1, 2) == 3\n'
    )

    # Initialize git
    env = {
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com",
        "HOME": "/tmp",
    }
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(repo), capture_output=True, env=env)

    return str(repo)


@pytest.fixture
def empty_dir(tmp_path):
    """Create an empty directory (edge case: not a repo at all)."""
    return str(tmp_path / "empty")


@pytest.fixture
def syntax_error_repo(tmp_path):
    """Create a repo with a Python syntax error."""
    repo = tmp_path / "syntax_err"
    repo.mkdir()
    (repo / "README.md").write_text("# Broken Repo\n")
    (repo / "broken.py").write_text("def broken(:\n    pass\n")
    return str(repo)


# ─── Tool tests ───

class TestReadReadme:
    def test_finds_readme(self, sample_repo):
        result = read_readme(sample_repo)
        assert result["found"] is True
        assert "Sample Project" in result["preview"]

    def test_no_readme(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = read_readme(empty_dir)
        assert result["found"] is False

    def test_readme_metadata(self, sample_repo):
        result = read_readme(sample_repo)
        assert result["length_chars"] > 0
        assert result["length_lines"] > 0


class TestAnalyzeStructure:
    def test_detects_python(self, sample_repo):
        result = analyze_structure(sample_repo)
        assert result["project_type"] == "python"
        assert result["has_setup_py"] is True

    def test_counts_files(self, sample_repo):
        result = analyze_structure(sample_repo)
        assert result["file_stats"]["total_files"] > 0

    def test_empty_dir(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = analyze_structure(empty_dir)
        assert result["file_stats"]["total_files"] == 0
        assert result["project_type"] == "unknown"

    def test_detects_dockerfile(self, sample_repo):
        (repo := sample_repo) and open(os.path.join(repo, "Dockerfile"), "w").write("FROM python:3.12\n")
        result = analyze_structure(sample_repo)
        assert result["has_dockerfile"] is True


class TestAnalyzeTests:
    def test_finds_tests(self, sample_repo):
        result = analyze_tests(sample_repo)
        assert result["test_file_count"] >= 1
        assert "tests/test_main.py" in result["test_files"]

    def test_ratio(self, sample_repo):
        result = analyze_tests(sample_repo)
        assert result["test_to_source_ratio"] > 0

    def test_no_tests(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = analyze_tests(empty_dir)
        assert result["test_file_count"] == 0

    def test_syntax_error_skipped(self, syntax_error_repo):
        """Files with syntax errors should be skipped, not crash."""
        result = analyze_tests(syntax_error_repo)
        assert result["source_file_count"] == 0  # broken.py can't be parsed


class TestAnalyzeComplexity:
    def test_finds_functions(self, sample_repo):
        result = analyze_complexity(sample_repo)
        assert result["total_functions"] > 0

    def test_add_function(self, sample_repo):
        result = analyze_complexity(sample_repo)
        function_names = [f["function"] for f in result["most_complex"]]
        assert "add" in function_names

    def test_empty_repo(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = analyze_complexity(empty_dir)
        assert result["total_functions"] == 0
        assert result["average_complexity"] == 0


class TestAnalyzeCodeQuality:
    def test_counts_lines(self, sample_repo):
        result = analyze_code_quality(sample_repo)
        assert result["total_lines"] > 0
        assert result["code_lines"] > 0

    def test_no_tech_debt(self, sample_repo):
        result = analyze_code_quality(sample_repo)
        assert result["tech_debt_markers"] == 0

    def test_detects_todo(self, tmp_path):
        repo = tmp_path / "todo_repo"
        repo.mkdir()
        (repo / "code.py").write_text("# TODO: fix this\nx = 1\n")
        result = analyze_code_quality(str(repo))
        assert result["todo_count"] == 1
        assert result["tech_debt_markers"] == 1


class TestAnalyzeDocumentation:
    def test_has_license(self, sample_repo):
        result = analyze_documentation(sample_repo)
        assert result["has_license"] is True

    def test_docstrings(self, sample_repo):
        result = analyze_documentation(sample_repo)
        assert result["docstrings_found"] > 0
        assert result["docstring_ratio"] > 0


class TestAnalyzeGitHistory:
    def test_has_commits(self, sample_repo):
        result = analyze_git_history(sample_repo)
        assert result["total_commits"] >= 1

    def test_contributor(self, sample_repo):
        result = analyze_git_history(sample_repo)
        assert result["contributor_count"] >= 1

    def test_no_git(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = analyze_git_history(empty_dir)
        assert result["total_commits"] == 0
        assert result["contributor_count"] == 0


class TestAnalyzeSecurity:
    def test_clean_repo(self, sample_repo):
        result = analyze_security(sample_repo)
        assert result["issue_count"] == 0

    def test_bare_except(self, tmp_path):
        repo = tmp_path / "sec_repo"
        repo.mkdir()
        (repo / "code.py").write_text("try:\n    pass\nexcept:\n    pass\n")
        result = analyze_security(str(repo))
        assert result["issue_count"] >= 1
        assert any(i["type"] == "bare_except" for i in result["issues_found"])

    def test_eval_detected(self, tmp_path):
        repo = tmp_path / "eval_repo"
        repo.mkdir()
        (repo / "code.py").write_text("result = eval('1+1')\n")
        result = analyze_security(str(repo))
        assert any(i["type"] == "eval" for i in result["issues_found"])


# ─── Baseline tests ───

class TestBaseline:
    def test_returns_assessment(self, sample_repo):
        result = run_baseline(sample_repo)
        assert "overall_score" in result
        assert 1 <= result["overall_score"] <= 10
        assert "quality_tier" in result
        assert "recommendation" in result
        assert "confidence" in result

    def test_writes_trajectory(self, sample_repo):
        result = run_baseline(sample_repo)
        assert "_trajectory" in result

    def test_empty_dir(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = run_baseline(empty_dir)
        assert 1 <= result["overall_score"] <= 10

    def test_score_in_range(self, sample_repo):
        result = run_baseline(sample_repo)
        assert 1 <= result["overall_score"] <= 10


# ─── Advanced tests ───

class TestAdvanced:
    def test_returns_assessment(self, sample_repo):
        result = run_advanced(sample_repo)
        assert "overall_score" in result
        assert 1 <= result["overall_score"] <= 10
        assert "dimension_scores" in result
        assert "evidence" in result
        assert "verification" in result

    def test_has_all_agents(self, sample_repo):
        result = run_advanced(sample_repo)
        agents = result.get("agents_used", [])
        assert "structure" in agents
        assert "test" in agents
        assert "code_quality" in agents
        assert "maintenance" in agents
        assert "verification" in agents
        assert "orchestrator" in agents

    def test_has_findings(self, sample_repo):
        result = run_advanced(sample_repo)
        assert len(result["strengths"]) > 0 or len(result["weaknesses"]) > 0

    def test_has_evidence(self, sample_repo):
        result = run_advanced(sample_repo)
        assert result["evidence_count"] > 0

    def test_security_agent_runs(self, sample_repo):
        result = run_advanced(sample_repo)
        # The code_quality agent now includes security analysis
        assert "Code Quality & Security" in result.get("dimension_scores", {})

    def test_empty_dir(self, empty_dir):
        os.makedirs(empty_dir, exist_ok=True)
        result = run_advanced(empty_dir)
        assert 1 <= result["overall_score"] <= 10

    def test_verification_rate(self, sample_repo):
        result = run_advanced(sample_repo)
        assert 0 <= result["verification"]["verification_rate"] <= 1.0


# ─── Trajectory logger tests ───

class TestTrajectoryLogger:
    def test_logs_instruction(self, tmp_path):
        logger = TrajectoryLogger("test", trajectories_dir=str(tmp_path))
        logger.log_instruction("Test instruction")
        assert len(logger.steps) == 1
        assert logger.steps[0]["type"] == "instruction"

    def test_logs_tool_call(self, tmp_path):
        logger = TrajectoryLogger("test", trajectories_dir=str(tmp_path))
        logger.log_tool_call("test_tool", {"input": "value"}, {"output": "result"})
        assert len(logger.steps) == 1
        assert logger.steps[0]["type"] == "tool_call"
        assert logger.steps[0]["tool"] == "test_tool"

    def test_saves_json(self, tmp_path):
        logger = TrajectoryLogger("test", trajectories_dir=str(tmp_path))
        logger.log_instruction("Test")
        logger.log_result({"score": 5})
        path = logger.save()
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["agent_name"] == "test"
        assert data["total_steps"] == 2

    def test_no_filename_collision(self, tmp_path):
        """Saving twice in the same second should not overwrite."""
        logger1 = TrajectoryLogger("same_name", trajectories_dir=str(tmp_path))
        logger1.log_instruction("First")
        path1 = logger1.save()

        logger2 = TrajectoryLogger("same_name", trajectories_dir=str(tmp_path))
        logger2.log_instruction("Second")
        path2 = logger2.save()

        assert path1 != path2
        assert os.path.exists(path1)
        assert os.path.exists(path2)


# ─── Comparison tests ───

class TestComparison:
    def test_advanced_more_specific(self, sample_repo):
        """Advanced should produce more specific findings than baseline."""
        baseline = run_baseline(sample_repo)
        advanced = run_advanced(sample_repo)

        baseline_findings = len(baseline["strengths"]) + len(baseline["weaknesses"])
        advanced_findings = len(advanced["strengths"]) + len(advanced["weaknesses"])

        assert advanced_findings >= baseline_findings

    def test_advanced_has_evidence(self, sample_repo):
        """Advanced should have evidence backing its findings."""
        advanced = run_advanced(sample_repo)
        assert advanced["evidence_count"] > 0

    def test_advanced_has_security(self, sample_repo):
        """Advanced should include security analysis."""
        advanced = run_advanced(sample_repo)
        assert "Code Quality & Security" in advanced.get("dimension_scores", {})


# ─── Edge case tests ───

class TestEdgeCases:
    def test_syntax_error_repo(self, syntax_error_repo):
        """Should not crash on repos with syntax errors."""
        result = run_advanced(syntax_error_repo)
        assert 1 <= result["overall_score"] <= 10

    def test_baseline_on_syntax_error(self, syntax_error_repo):
        result = run_baseline(syntax_error_repo)
        assert 1 <= result["overall_score"] <= 10
