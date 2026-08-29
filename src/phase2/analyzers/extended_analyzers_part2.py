"""
Phase 2 Extended Analyzers Part 2 — additional analyzers (continued).
"""
from __future__ import annotations
import os, re, ast, json, subprocess, hashlib
from typing import Any
from collections import Counter

from src.phase2.schema import (
    AnalyzerBase, ToolResult, Finding, Status, Severity,
    ProjectProfile, register_analyzer,
)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".eggs", "dist", "build", ".mypy_cache", ".pytest_cache"}

def _safe_read(path, max_bytes=100000):
    try:
        with open(path, "r", errors="replace") as f: return f.read(max_bytes)
    except Exception: return ""

def _walk_python_files(repo_path):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"): yield os.path.join(root, f), f, root

def _walk_all_files(repo_path):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files: yield os.path.join(root, f), f, root

@register_analyzer
class ReleaseVersioningAnalyzer(AnalyzerBase):
    """Checks release and versioning practices."""
    ANALYZER_ID = "release_versioning"; ANALYZER_NAME = "Release & Versioning"
    CATEGORY = "cicd"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        package_version = None; git_tags = []; changelog_consistent = False

        # Check package version
        for vfile in ["setup.py", "pyproject.toml", "package.json", "Cargo.toml"]:
            path = os.path.join(repo_path, vfile)
            if os.path.exists(path):
                content = _safe_read(path)
                m = re.search(r'version["\s:=]+["\']?([0-9]+\.[0-9]+\.[0-9]+)', content)
                if m:
                    package_version = m.group(1)
                    break

        # Check git tags
        try:
            result = subprocess.run(["git", "tag", "--list"], cwd=repo_path, capture_output=True, text=True, timeout=5)
            git_tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
        except:
            pass

        # Check changelog
        for cl in ["CHANGELOG.md", "CHANGES.md", "CHANGELOG.rst"]:
            if os.path.exists(os.path.join(repo_path, cl)):
                changelog_consistent = True

        if package_version and git_tags:
            # Check if version matches latest tag
            latest_tag = git_tags[-1] if git_tags else None
            if latest_tag and package_version not in latest_tag and latest_tag.lstrip("v") not in package_version:
                self._add_finding(Finding(id="REL-001", category="cicd", severity=Severity.MEDIUM.value,
                    status=Status.WARN.value, title=f"Version mismatch: package={package_version}, latest tag={latest_tag}",
                    confidence=0.8, evidence=f"Package version: {package_version}, Git tag: {latest_tag}",
                    recommendation="Ensure package version matches Git tags."))

        if not git_tags and package_version:
            self._add_finding(Finding(id="REL-002", category="cicd", severity=Severity.LOW.value,
                status=Status.WARN.value, title="No Git tags despite having a package version",
                confidence=0.7, recommendation="Tag releases with semantic versioning."))

        score = 50
        if package_version: score += 15
        if git_tags: score += 15
        if changelog_consistent: score += 10
        if package_version and git_tags and changelog_consistent: score += 10

        self._set_raw_data("release", {"package_version": package_version, "tag_count": len(git_tags),
            "has_changelog": changelog_consistent, "score": min(100, score)})
        self._add_metric("release_score", min(100, score))
        self._add_metric("package_version", package_version or "unknown")
        self._add_metric("tag_count", len(git_tags))
        return self._build_result(_t.time() - start)


@register_analyzer
class StaticCodeQualityAnalyzer(AnalyzerBase):
    """Runs or checks for configured static analysis tools."""
    ANALYZER_ID = "static_quality"; ANALYZER_NAME = "Static Code Quality"
    CATEGORY = "maintainability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        configured_linters = []; has_type_checker = False

        # Check for linter configs
        config_checks = {
            "ruff": ["ruff.toml", ".ruff.toml", "[tool.ruff]"],
            "flake8": [".flake8", "[flake8]", "setup.cfg"],
            "pylint": [".pylintrc", "pylintrc", "[tool.pylint]"],
            "eslint": [".eslintrc", ".eslintrc.js", ".eslintrc.json"],
            "mypy": ["mypy.ini", ".mypy.ini", "[tool.mypy]"],
            "pyright": ["pyrightconfig.json"],
        }

        for linter, configs in config_checks.items():
            for cfg in configs:
                # Check for file existence
                if os.path.exists(os.path.join(repo_path, cfg)):
                    configured_linters.append(linter)
                    break
                # Check in pyproject.toml or setup.cfg
                for toml in ["pyproject.toml", "setup.cfg"]:
                    path = os.path.join(repo_path, toml)
                    if os.path.exists(path):
                        if cfg in _safe_read(path):
                            configured_linters.append(linter)
                            break

        if "mypy" in configured_linters or "pyright" in configured_linters:
            has_type_checker = True

        # Try running ruff if available
        ruff_errors = 0
        try:
            result = subprocess.run(["ruff", "check", "--output-format=json", "."],
                                  cwd=repo_path, capture_output=True, text=True, timeout=30)
            if result.returncode != 0 and result.stdout:
                issues = json.loads(result.stdout)
                ruff_errors = len(issues)
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        if not configured_linters:
            self._add_finding(Finding(id="QUALITY-001", category="maintainability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No project static-analysis configuration detected",
                confidence=0.9, recommendation="Configure a linter like Ruff or ESLint."))

        if not has_type_checker:
            self._add_finding(Finding(id="QUALITY-002", category="maintainability", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No type checker configured",
                confidence=0.7, recommendation="Consider adding mypy or pyright."))

        if ruff_errors > 0:
            self._add_finding(Finding(id="QUALITY-003", category="maintainability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"Ruff found {ruff_errors} issues",
                confidence=1.0, evidence=f"{ruff_errors} linting errors", recommendation="Fix linting issues."))

        score = 40
        if configured_linters: score += 30
        if has_type_checker: score += 15
        if ruff_errors == 0 and configured_linters: score += 15
        elif ruff_errors > 0: score -= min(20, ruff_errors)

        self._set_raw_data("static_quality", {"linters": configured_linters,
            "has_type_checker": has_type_checker, "ruff_errors": ruff_errors, "score": max(0, score)})
        self._add_metric("static_quality_score", max(0, score))
        self._add_metric("configured_linters", len(configured_linters))
        return self._build_result(_t.time() - start)


@register_analyzer
class PerformanceAnalyzer(AnalyzerBase):
    """Detects potential performance risks in code."""
    ANALYZER_ID = "performance"; ANALYZER_NAME = "Performance Risk"
    CATEGORY = "reliability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        risks = 0

        for filepath, fname, root in _walk_python_files(repo_path):
            if os.path.basename(root) in ("tests", "test"): continue
            content = _safe_read(filepath)
            rel = os.path.relpath(filepath, repo_path)
            try: tree = ast.parse(content)
            except SyntaxError: continue

            for node in ast.walk(tree):
                # N+1 query pattern: loop + DB call
                if isinstance(node, ast.For):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            fn = child.func.attr if isinstance(child.func, ast.Attribute) else ""
                            if fn in ("execute", "query", "fetch", "fetchall", "filter", "all"):
                                risks += 1
                                if risks <= 10:
                                    self._add_finding(Finding(id="PERF-001", category="reliability",
                                        severity=Severity.MEDIUM.value, status=Status.WARN.value,
                                        title=f"Potential N+1 query pattern in {rel}:{node.lineno}",
                                        confidence=0.5, files=[{"path": rel, "line_start": node.lineno}],
                                        evidence="Database call inside loop",
                                        recommendation="Use batch queries or ORM prefetching."))
                                break

            # Check for list construction in loops
            for i, line in enumerate(content.splitlines(), 1):
                if "list(" in line and "for " in line:
                    pass  # list comprehension is fine
                elif re.search(r'\.append\(.*\)', line) and i > 1:
                    prev = content.splitlines()[i-2].strip() if i > 1 else ""
                    if "for " in prev and "append" in line:
                        risks += 1
                        if risks <= 15:
                            self._add_finding(Finding(id="PERF-002", category="reliability",
                                severity=Severity.LOW.value, status=Status.INFO.value,
                                title=f"List append in loop in {rel}:{i} (consider comprehension)",
                                confidence=0.4, files=[{"path": rel, "line_start": i}],
                                recommendation="Use list comprehension for better performance."))

        score = max(0, 90 - min(30, risks * 5))
        self._set_raw_data("performance", {"risks": risks, "score": score})
        self._add_metric("performance_score", score)
        self._add_metric("performance_risks", risks)
        return self._build_result(_t.time() - start)


@register_analyzer
class SecretsDetectionAnalyzer(AnalyzerBase):
    """Deep secrets detection with entropy analysis and pattern matching."""
    ANALYZER_ID = "secrets"; ANALYZER_NAME = "Secrets Detection"
    CATEGORY = "security"; VERSION = "2.0.0"

    SECRET_PATTERNS = [
        (r'(?i)api[_-]?key\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})["\']', "API Key"),
        (r'(?i)secret\s*[:=]\s*["\']([A-Za-z0-9_\-]{16,})["\']', "Secret"),
        (r'(?i)token\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']', "Token"),
        (r'(?i)password\s*[:=]\s*["\']([^"\']{8,})["\']', "Password"),
        (r'sk-[A-Za-z0-9]{20,}', "Stripe Key"),
        (r'AKIA[A-Z0-9]{16}', "AWS Access Key"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub Token"),
        (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private Key"),
        (r'(?i)jwt[_-]?secret\s*[:=]\s*["\']([^"\']{8,})["\']', "JWT Secret"),
    ]

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        secrets_found = 0

        for filepath, fname, root in _walk_all_files(repo_path):
            if fname.endswith((".pyc", ".pyo", ".so", ".bin")): continue
            content = _safe_read(filepath)
            rel = os.path.relpath(filepath, repo_path)
            # Skip .env.example and test files
            if "example" in fname.lower() or os.path.basename(root) in ("tests", "test"): continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"): continue

                for pattern, secret_type in self.SECRET_PATTERNS:
                    m = re.search(pattern, stripped)
                    if m:
                        # Mask the secret
                        full_match = m.group(0)
                        masked = re.sub(m.group(1) if m.lastindex else full_match,
                                       '***MASKED***', full_match) if m.lastindex else full_match[:20] + "***MASKED***"
                        # Check if it's a placeholder
                        value = m.group(1) if m.lastindex else ""
                        if value.lower() in ("your_key_here", "changeme", "placeholder", "xxx", "example"):
                            continue

                        # Entropy check for high confidence
                        import math
                        entropy = 0
                        if value:
                            freq = Counter(value)
                            total = len(value)
                            entropy = -sum((c/total) * math.log2(c/total) for c in freq.values())

                        confidence = min(0.95, 0.6 + (entropy / 8) * 0.35) if entropy > 3 else 0.5
                        severity = Severity.HIGH.value if confidence > 0.7 else Severity.MEDIUM.value

                        secrets_found += 1
                        self._add_finding(Finding(id="SEC-SECRET-DEEP", category="security", severity=severity,
                            status=Status.FAIL.value, title=f"Potential {secret_type} in {rel}:{i}",
                            confidence=round(confidence, 2), files=[{"path": rel, "line_start": i}],
                            evidence=f"Line {i}: {masked}", cwe_id="CWE-798",
                            impact="Hardcoded credential exposure",
                            recommendation="Use environment variables or a secrets manager.",
                            references=["OWASP A07:2021"]))

        score = max(0, 100 - secrets_found * 20)
        self._set_raw_data("secrets", {"secrets_found": secrets_found, "score": score})
        self._add_metric("secrets_score", score)
        self._add_metric("secrets_found", secrets_found)
        return self._build_result(_t.time() - start)


@register_analyzer
class LicenseHygieneAnalyzer(AnalyzerBase):
    """Checks license coherence and legal hygiene."""
    ANALYZER_ID = "license_hygiene"; ANALYZER_NAME = "License & Legal Hygiene"
    CATEGORY = "documentation"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        has_license = False; license_type = None; has_security_md = False
        has_conduct = False; has_contributing = False

        for fname in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
            path = os.path.join(repo_path, fname)
            if os.path.exists(path):
                has_license = True
                content = _safe_read(path).lower()
                if "mit license" in content: license_type = "MIT"
                elif "apache license" in content: license_type = "Apache"
                elif "bsd license" in content: license_type = "BSD"
                elif "gnu general" in content: license_type = "GPL"
                elif "mozilla" in content: license_type = "MPL"
                break

        if os.path.exists(os.path.join(repo_path, "SECURITY.md")): has_security_md = True
        if os.path.exists(os.path.join(repo_path, "CODE_OF_CONDUCT.md")): has_conduct = True
        if os.path.exists(os.path.join(repo_path, "CONTRIBUTING.md")): has_contributing = True

        if not has_license:
            self._add_finding(Finding(id="LEGAL-001", category="documentation", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title="No LICENSE file found", confidence=1.0,
                recommendation="Add a LICENSE file with an appropriate license."))
        if not has_security_md:
            self._add_finding(Finding(id="LEGAL-002", category="documentation", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No SECURITY.md file", confidence=0.7,
                recommendation="Add SECURITY.md for vulnerability reporting guidance."))
        if not has_contributing:
            self._add_finding(Finding(id="LEGAL-003", category="documentation", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No CONTRIBUTING.md file", confidence=0.6,
                recommendation="Add CONTRIBUTING.md to guide contributors."))

        score = 30
        if has_license: score += 40
        if has_security_md: score += 10
        if has_contributing: score += 10
        if has_conduct: score += 10

        self._set_raw_data("license", {"has_license": has_license, "license_type": license_type,
            "has_security_md": has_security_md, "has_contributing": has_contributing, "score": score})
        self._add_metric("license_score", score)
        self._add_metric("license_type", license_type or "none")
        return self._build_result(_t.time() - start)


@register_analyzer
class BuildPackagingAnalyzer(AnalyzerBase):
    """Evaluates build and packaging configuration."""
    ANALYZER_ID = "build_packaging"; ANALYZER_NAME = "Build & Packaging"
    CATEGORY = "reproducibility"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        has_setup_py = os.path.exists(os.path.join(repo_path, "setup.py"))
        has_pyproject = os.path.exists(os.path.join(repo_path, "pyproject.toml"))
        has_package_json = os.path.exists(os.path.join(repo_path, "package.json"))
        has_cargo_toml = os.path.exists(os.path.join(repo_path, "Cargo.toml"))
        has_go_mod = os.path.exists(os.path.join(repo_path, "go.mod"))
        has_dockerfile = os.path.exists(os.path.join(repo_path, "Dockerfile"))
        has_makefile = os.path.exists(os.path.join(repo_path, "Makefile"))

        build_files = []
        if has_setup_py: build_files.append("setup.py")
        if has_pyproject: build_files.append("pyproject.toml")
        if has_package_json: build_files.append("package.json")
        if has_cargo_toml: build_files.append("Cargo.toml")
        if has_go_mod: build_files.append("go.mod")
        if has_dockerfile: build_files.append("Dockerfile")
        if has_makefile: build_files.append("Makefile")

        if not build_files:
            self._add_finding(Finding(id="BUILD-001", category="reproducibility", severity=Severity.LOW.value,
                status=Status.WARN.value, title="No build configuration detected", confidence=0.7,
                recommendation="Add a build configuration file."))

        # Check for .gitignore
        if not os.path.exists(os.path.join(repo_path, ".gitignore")):
            self._add_finding(Finding(id="BUILD-002", category="reproducibility", severity=Severity.LOW.value,
                status=Status.WARN.value, title="No .gitignore file", confidence=0.8,
                recommendation="Add .gitignore to exclude build artifacts."))

        score = 50
        if build_files: score += 25
        if has_dockerfile: score += 10
        if has_makefile: score += 5
        if os.path.exists(os.path.join(repo_path, ".gitignore")): score += 10

        self._set_raw_data("build", {"build_files": build_files, "score": min(100, score)})
        self._add_metric("build_score", min(100, score))
        self._add_metric("build_files", len(build_files))
        return self._build_result(_t.time() - start)


@register_analyzer
class CoverageAnalyzer(AnalyzerBase):
    """Attempts to measure test coverage where tooling supports it."""
    ANALYZER_ID = "coverage"; ANALYZER_NAME = "Coverage Analysis"
    CATEGORY = "testing"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        coverage_pct = None; has_coverage_config = False; has_coverage_report = False

        # Check for coverage configuration
        for cfg in [".coveragerc", "pyproject.toml", "setup.cfg", "pytest.ini"]:
            path = os.path.join(repo_path, cfg)
            if os.path.exists(path):
                content = _safe_read(path)
                if "coverage" in content.lower() or "[tool.coverage]" in content:
                    has_coverage_config = True
                    break

        # Check for coverage reports
        for report in ["coverage.xml", ".coverage", "htmlcov", "coverage"]:
            if os.path.exists(os.path.join(repo_path, report)):
                has_coverage_report = True
                break

        # Try running coverage
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov", "--cov-report=json", "-q", "--no-header", "--tb=no"],
                cwd=repo_path, capture_output=True, text=True, timeout=30
            )
            cov_path = os.path.join(repo_path, "coverage.json")
            if os.path.exists(cov_path):
                with open(cov_path) as f:
                    cov_data = json.load(f)
                    coverage_pct = cov_data.get("totals", {}).get("percent_covered", 0)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, Exception):
            pass

        if not has_coverage_config and not has_coverage_report:
            self._add_finding(Finding(id="COV-001", category="testing", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No coverage configuration detected", confidence=0.8,
                recommendation="Add coverage measurement (e.g., pytest-cov)."))

        if coverage_pct is not None and coverage_pct < 50:
            self._add_finding(Finding(id="COV-002", category="testing", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"Low test coverage: {coverage_pct:.1f}%", confidence=1.0,
                evidence=f"Coverage: {coverage_pct:.1f}%", recommendation="Increase test coverage."))

        score = 40
        if has_coverage_config: score += 20
        if has_coverage_report: score += 15
        if coverage_pct is not None:
            score = min(100, int(coverage_pct))
        elif has_coverage_config:
            score = 60

        self._set_raw_data("coverage", {"has_config": has_coverage_config,
            "has_report": has_coverage_report, "coverage_pct": coverage_pct, "score": score})
        self._add_metric("coverage_score", score)
        self._add_metric("coverage_pct", coverage_pct or 0)
        return self._build_result(_t.time() - start)


@register_analyzer
class VulnerabilityAnalyzer(AnalyzerBase):
    """Checks for known vulnerability indicators in dependencies."""
    ANALYZER_ID = "vulnerability"; ANALYZER_NAME = "Vulnerability Analysis"
    CATEGORY = "security"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        known_vulns = []; risky_deps = []

        # Check for dependency files and look for known vulnerable patterns
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            content = _safe_read(req_path)
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or not stripped: continue
                # Check for known vulnerable versions (simplified)
                if "Flask==0.12" in stripped or "Flask<1.0" in stripped:
                    known_vulns.append({"package": "Flask", "version": stripped, "issue": "Known XSS in old versions"})
                    self._add_finding(Finding(id="VULN-001", category="security", severity=Severity.HIGH.value,
                        status=Status.FAIL.value, title=f"Known vulnerable dependency: Flask (old version)",
                        confidence=0.9, files=[{"path": "requirements.txt", "line_start": i}],
                        evidence=f"Line {i}: {stripped}", cwe_id="CWE-1104",
                        recommendation="Upgrade to latest Flask."))
                if "Django<3.2" in stripped or "Django==2" in stripped:
                    known_vulns.append({"package": "Django", "version": stripped, "issue": "Multiple CVEs in old Django"})
                    self._add_finding(Finding(id="VULN-002", category="security", severity=Severity.HIGH.value,
                        status=Status.FAIL.value, title=f"Known vulnerable dependency: Django (old version)",
                        confidence=0.9, files=[{"path": "requirements.txt", "line_start": i}],
                        evidence=f"Line {i}: {stripped}", cwe_id="CWE-1104",
                        recommendation="Upgrade to latest Django."))

        # Check for unpinned dependencies as risky
        if os.path.exists(req_path):
            content = _safe_read(req_path)
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or not stripped: continue
                # Check for unpinned (no version specifier)
                if "==" not in stripped and ">=" not in stripped and "<" not in stripped:
                    pkg = stripped.split("[")[0].split(";")[0].strip()
                    if pkg:
                        risky_deps.append(pkg)
                        if len(risky_deps) <= 10:
                            self._add_finding(Finding(id="VULN-003", category="security", severity=Severity.LOW.value,
                                status=Status.WARN.value, title=f"Unpinned dependency: {pkg}",
                                confidence=0.6, files=[{"path": "requirements.txt", "line_start": i}],
                                evidence=f"Line {i}: {stripped} (no version pin)",
                                recommendation="Pin dependencies to specific versions."))

        # Check for GitHub security advisories
        dep_review_path = os.path.join(repo_path, ".github", "dependabot.yml")
        if not os.path.exists(dep_review_path):
            if os.path.exists(os.path.join(repo_path, "requirements.txt")) or                os.path.exists(os.path.join(repo_path, "package.json")):
                self._add_finding(Finding(id="VULN-004", category="security", severity=Severity.LOW.value,
                    status=Status.INFO.value, title="No Dependabot configuration detected",
                    confidence=0.7, recommendation="Enable Dependabot for automated vulnerability alerts."))

        score = 80
        if known_vulns: score = min(score, 30)
        if risky_deps: score -= min(20, len(risky_deps) * 2)

        self._set_raw_data("vulnerability", {"known_vulns": len(known_vulns),
            "risky_deps": len(risky_deps), "score": max(0, score)})
        self._add_metric("vulnerability_score", max(0, score))
        self._add_metric("known_vulnerabilities", len(known_vulns))
        self._add_metric("risky_dependencies", len(risky_deps))
        return self._build_result(_t.time() - start)
