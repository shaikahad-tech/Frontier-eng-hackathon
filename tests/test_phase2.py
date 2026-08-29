"""
Phase 2 Test Suite — tests the core schema, analyzers, scoring, and pipeline.
Uses fixture repositories created in tmp_path.
"""

import os
import sys
import json
import tempfile
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.phase2.schema import (
    Finding, ToolResult, Severity, Status, ProjectProfile,
    grade_from_score, maturity_from_score, AnalyzerRegistry,
)
from src.phase2.scoring import ScoringEngine
from src.phase2.reporting import ReportGenerator
from src.phase2.pipeline import Pipeline


# --- Fixtures ---

@pytest.fixture
def good_repo(tmp_path):
    """Create a well-engineered test repository."""
    repo = tmp_path / "good"
    repo.mkdir()

    (repo / "README.md").write_text(
        "# Good Project\n\n"
        "A well-tested Python library.\n\n"
        "## Installation\n```bash\npip install -e .\n```\n\n"
        "## Usage\n```python\nfrom goodlib import add\nresult = add(1, 2)\n```\n\n"
        "## Testing\n```bash\npytest\n```\n"
    )
    (repo / "setup.py").write_text("from setuptools import setup\nsetup(name='goodlib', version='1.0.0', packages=['goodlib'])\n")
    (repo / "requirements.txt").write_text("pytest==8.0.0\n")
    (repo / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024\n")
    (repo / "CONTRIBUTING.md").write_text("# Contributing\n\nContributions welcome!\n")
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## v1.0.0\n- Initial release\n")

    (repo / "goodlib").mkdir()
    (repo / "goodlib" / "__init__.py").write_text('"""Good library."""\nfrom .core import add\n')
    (repo / "goodlib" / "core.py").write_text(
        '"""Core functions."""\n\n'
        'def add(a: float, b: float) -> float:\n'
        '    """Add two numbers."""\n'
        '    return a + b\n\n'
        'def subtract(a: float, b: float) -> float:\n'
        '    """Subtract b from a."""\n'
        '    return a - b\n'
    )

    (repo / "tests").mkdir()
    (repo / "tests" / "test_core.py").write_text(
        'from goodlib.core import add, subtract\n\n'
        'def test_add():\n'
        '    assert add(1, 2) == 3\n\n'
        'def test_subtract():\n'
        '    assert subtract(5, 3) == 2\n'
    )

    # Git init
    env = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com", "HOME": "/tmp"}
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(repo), capture_output=True, env=env)
    return str(repo)


@pytest.fixture
def bad_repo(tmp_path):
    """Create a poorly-engineered test repository with security issues."""
    repo = tmp_path / "bad"
    repo.mkdir()

    # No README, no LICENSE, no tests
    (repo / "insecure.py").write_text(
        'import pickle\n'
        'import subprocess\n'
        'import random\n'
        'import hashlib\n'
        '\n'
        'password = "supersecret123"\n'
        'api_key = "sk-1234567890abcdef"\n'
        '\n'
        'def load_data(data):\n'
        '    return pickle.loads(data)\n'
        '\n'
        'def run_command(user_input):\n'
        '    subprocess.run(user_input, shell=True)\n'
        '\n'
        'def get_hash(data):\n'
        '    return hashlib.md5(data.encode()).hexdigest()\n'
        '\n'
        'def safe_divide(a, b):\n'
        '    try:\n'
        '        return a / b\n'
        '    except:\n'
        '        pass\n'
        '\n'
        'def complex_function(x, y, z, a, b, c, d, e, f, g):\n'
        '    if x:\n'
        '        if y:\n'
        '            if z:\n'
        '                if a:\n'
        '                    if b:\n'
        '                        if c:\n'
        '                            return 1\n'
        '    return 0\n'
    )
    return str(repo)


@pytest.fixture
def empty_dir(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    return str(d)


# --- Schema tests ---

class TestSchema:
    def test_finding_creation(self):
        f = Finding(id="TEST-001", category="test", severity="high", status="FAIL", title="Test")
        assert f.id == "TEST-001"
        assert f.confidence == 0.0
        d = f.to_dict()
        assert d["id"] == "TEST-001"

    def test_grade_from_score(self):
        assert grade_from_score(95) == "A+"
        assert grade_from_score(85) == "A"
        assert grade_from_score(75) == "B+"
        assert grade_from_score(65) == "B"
        assert grade_from_score(55) == "C+"
        assert grade_from_score(45) == "C"
        assert grade_from_score(30) == "D"
        assert grade_from_score(20) == "F"

    def test_maturity_from_score(self):
        assert maturity_from_score(90) == 5
        assert maturity_from_score(75) == 4
        assert maturity_from_score(60) == 3
        assert maturity_from_score(40) == 2
        assert maturity_from_score(20) == 1
        assert maturity_from_score(10) == 0


# --- Pipeline tests ---

class TestPipeline:
    def test_runs_on_good_repo(self, good_repo):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        assert "scores" in result
        assert result["scores"]["overall_score"] >= 0
        assert result["scores"]["overall_score"] <= 100
        assert "grade" in result["scores"]
        assert "executive_report" in result
        assert "engineering_report" in result
        assert "machine_report" in result

    def test_runs_on_bad_repo(self, bad_repo):
        pipeline = Pipeline(bad_repo, verbose=False)
        result = pipeline.run()
        assert result["scores"]["overall_score"] >= 0
        assert result["analysis_metadata"]["finding_count"] > 0

    def test_runs_on_empty_dir(self, empty_dir):
        pipeline = Pipeline(empty_dir, verbose=False)
        result = pipeline.run()
        assert result["scores"]["overall_score"] >= 0

    def test_machine_report_structure(self, good_repo):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        machine = result["machine_report"]
        assert "repository" in machine
        assert "scores" in machine
        assert "hard_gates" in machine
        assert "findings" in machine
        assert "tool_results" in machine


# --- Scoring tests ---

class TestScoring:
    def test_scoring_engine(self):
        engine = ScoringEngine(profile="LIBRARY")
        findings = []
        tool_results = [{"tool_name": "test", "metrics": {"testing_score": 80}, "findings": []}]
        result = engine.score(tool_results, findings)
        assert 0 <= result["overall_score"] <= 100
        assert "grade" in result
        assert "category_scores" in result

    def test_hard_gate_triggers(self):
        engine = ScoringEngine()
        finding = Finding(
            id="SEC-001", category="security", severity=Severity.CRITICAL.value,
            status=Status.FAIL.value, title="Critical injection", confidence=0.9
        )
        result = engine.score([], [finding])
        assert result["overall_score"] <= 59
        assert len(result["hard_gates_triggered"]) > 0


# --- Report tests ---

class TestReports:
    def test_executive_report(self, good_repo):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        report = result["executive_report"]
        assert "Executive Report" in report
        assert "Overall Score" in report

    def test_engineering_report(self, good_repo):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        report = result["engineering_report"]
        assert "Engineering Report" in report
        assert "Metrics" in report

    def test_machine_report_json(self, good_repo):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        machine = result["machine_report"]
        json_str = json.dumps(machine, default=str)
        assert len(json_str) > 0


# --- Analyzer-specific tests ---

class TestAnalyzers:
    def test_discovery_detects_python(self, good_repo):
        from src.phase2.analyzers.all_analyzers import RepositoryDiscoveryAnalyzer
        analyzer = RepositoryDiscoveryAnalyzer()
        result = analyzer.analyze(good_repo, {})
        assert "Python" in result.raw_data["discovery"]["languages"]

    def test_security_detects_eval(self, bad_repo):
        from src.phase2.analyzers.all_analyzers import SecuritySASTAnalyzer
        analyzer = SecuritySASTAnalyzer()
        result = analyzer.analyze(bad_repo, {})
        finding_titles = [f.title for f in analyzer.findings]
        assert any("eval" in t.lower() or "exec" in t.lower() or "shell" in t.lower() for t in finding_titles)

    def test_security_detects_secret(self, bad_repo):
        from src.phase2.analyzers.all_analyzers import SecuritySASTAnalyzer
        analyzer = SecuritySASTAnalyzer()
        result = analyzer.analyze(bad_repo, {})
        finding_titles = [f.title for f in analyzer.findings]
        assert any("secret" in t.lower() for t in finding_titles)

    def test_complexity_detects_high(self, bad_repo):
        from src.phase2.analyzers.all_analyzers import ComplexityAnalyzer
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze(bad_repo, {})
        assert analyzer.metrics["high_complexity_count"] > 0 or analyzer.metrics["critical_complexity_count"] > 0

    def test_testing_detects_no_tests(self, bad_repo):
        from src.phase2.analyzers.all_analyzers import TestingAnalyzer
        analyzer = TestingAnalyzer()
        result = analyzer.analyze(bad_repo, {})
        assert analyzer.metrics["test_function_count"] == 0

    def test_documentation_detects_no_readme(self, bad_repo):
        from src.phase2.analyzers.all_analyzers import DocumentationAnalyzer
        analyzer = DocumentationAnalyzer()
        result = analyzer.analyze(bad_repo, {})
        assert any("No README" in f.title for f in analyzer.findings)


# --- Quality Gate tests ---

class TestQualityGates:
    def test_gate_passes_on_good_repo(self, good_repo, tmp_path):
        pipeline = Pipeline(good_repo, verbose=False)
        result = pipeline.run()
        from src.phase2.gates import QualityGate
        gate = QualityGate(min_score=0, no_critical=True, max_severity="critical")
        exit_code, failures = gate.check(result)
        assert result["scores"]["critical_count"] == 0

    def test_gate_fails_on_critical(self, bad_repo):
        pipeline = Pipeline(bad_repo, verbose=False)
        result = pipeline.run()
        from src.phase2.gates import QualityGate
        gate = QualityGate(no_critical=True)
        exit_code, failures = gate.check(result)
        assert exit_code == 1
