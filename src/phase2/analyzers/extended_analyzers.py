"""
Phase 2 Extended Analyzers — additional analyzers to reach 25 analysis domains.
These complement the analyzers in all_analyzers.py.
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
        with open(path, "r", errors="replace") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def _walk_python_files(repo_path):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f), f, root


def _walk_all_files(repo_path):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(root, f), f, root


@register_analyzer
class TestExecutionAnalyzer(AnalyzerBase):
    """Actually executes the test suite when safe."""
    ANALYZER_ID = "test_execution"; ANALYZER_NAME = "Test Execution"
    CATEGORY = "testing"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        test_framework = context.get("discovery", {}).get("test_frameworks", [])
        passed = failed = errors = skipped = 0
        test_command = None

        # Try pytest
        if "pytest" in test_framework or os.path.exists(os.path.join(repo_path, "pytest.ini")):
            test_command = "pytest"
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "--tb=no", "-q", "--no-header"],
                    cwd=repo_path, capture_output=True, text=True, timeout=30
                )
                output = result.stdout + result.stderr
                # Parse pytest output
                for line in output.splitlines():
                    if "passed" in line and "failed" not in line:
                        m = re.search(r'(\d+) passed', line)
                        if m: passed = int(m.group(1))
                    if "failed" in line:
                        m = re.search(r'(\d+) failed', line)
                        if m: failed = int(m.group(1))
                    if "error" in line.lower():
                        m = re.search(r'(\d+) error', line.lower())
                        if m: errors = int(m.group(1))
                    if "skipped" in line:
                        m = re.search(r'(\d+) skipped', line)
                        if m: skipped = int(m.group(1))
            except subprocess.TimeoutExpired:
                self._add_finding(Finding(id="TESTEXEC-002", category="testing", severity=Severity.MEDIUM.value,
                    status=Status.WARN.value, title="Test execution timed out (30s)", confidence=1.0,
                    evidence="pytest exceeded 30s timeout", recommendation="Optimize test suite or increase timeout."))
            except Exception as e:
                self._add_finding(Finding(id="TESTEXEC-003", category="testing", severity=Severity.LOW.value,
                    status=Status.WARN.value, title=f"Test execution failed: {type(e).__name__}", confidence=0.8,
                    evidence=str(e)[:200], recommendation="Ensure tests can run in a clean environment."))

        if test_command and passed + failed + errors + skipped == 0:
            self._add_finding(Finding(id="TESTEXEC-001", category="testing", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="Tests detected but execution yielded no results", confidence=0.75,
                evidence=f"Command: {test_command}", recommendation="Verify test configuration."))
        if failed > 0:
            self._add_finding(Finding(id="TESTEXEC-004", category="testing", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title=f"{failed} test(s) failing", confidence=1.0,
                evidence=f"{failed} failed, {passed} passed, {skipped} skipped",
                recommendation="Fix failing tests before deployment."))
        if errors > 0:
            self._add_finding(Finding(id="TESTEXEC-005", category="testing", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title=f"{errors} test error(s)", confidence=1.0,
                evidence=f"{errors} errors during collection or execution",
                recommendation="Fix test errors."))

        score = 50
        if passed > 0 and failed == 0 and errors == 0: score = 90
        elif passed > failed: score = 65
        elif passed == 0 and failed == 0: score = 30

        self._set_raw_data("test_execution", {"command": test_command, "passed": passed, "failed": failed,
            "errors": errors, "skipped": skipped, "score": score})
        self._add_metric("test_execution_score", score)
        self._add_metric("tests_passed", passed)
        self._add_metric("tests_failed", failed)
        return self._build_result(_t.time() - start)


@register_analyzer
class ContainerAnalyzer(AnalyzerBase):
    """Analyzes Dockerfiles for container security best practices."""
    ANALYZER_ID = "container"; ANALYZER_NAME = "Container Security"
    CATEGORY = "security"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        dockerfiles = []
        for filepath, fname, root in _walk_all_files(repo_path):
            if fname == "Dockerfile" or fname.endswith(".dockerfile"):
                dockerfiles.append(os.path.relpath(filepath, repo_path))

        if not dockerfiles:
            self._set_raw_data("container", {"has_dockerfile": False, "score": 50})
            self._add_metric("container_score", 50)
            return self._build_result(_t.time() - start)

        issues = 0
        for df_path in dockerfiles:
            full_path = os.path.join(repo_path, df_path)
            content = _safe_read(full_path)
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("FROM") and ":latest" in stripped:
                    self._add_finding(Finding(id="CONT-001", category="security", severity=Severity.HIGH.value,
                        status=Status.WARN.value, title=f"Base image uses :latest tag in {df_path}",
                        confidence=0.9, files=[{"path": df_path, "line_start": i}],
                        evidence=f"Line {i}: {stripped}", recommendation="Pin to a specific version."))
                    issues += 1
                if stripped == "USER root" or "USER root" in stripped:
                    self._add_finding(Finding(id="CONT-002", category="security", severity=Severity.MEDIUM.value,
                        status=Status.WARN.value, title=f"Container runs as root in {df_path}",
                        confidence=0.85, files=[{"path": df_path, "line_start": i}],
                        evidence=f"Line {i}: {stripped}", recommendation="Use a non-root user."))
                    issues += 1
                if "COPY . ." in stripped or "ADD . ." in stripped:
                    self._add_finding(Finding(id="CONT-003", category="security", severity=Severity.MEDIUM.value,
                        status=Status.WARN.value, title=f"Broad COPY in {df_path} may include secrets",
                        confidence=0.6, files=[{"path": df_path, "line_start": i}],
                        evidence=f"Line {i}: {stripped}", recommendation="Use .dockerignore and copy specific files."))
                    issues += 1
            if not any("USER" in l for l in lines):
                self._add_finding(Finding(id="CONT-004", category="security", severity=Severity.LOW.value,
                    status=Status.WARN.value, title=f"No USER directive in {df_path} (runs as root)",
                    confidence=0.8, files=[{"path": df_path}],
                    recommendation="Add USER directive to run as non-root."))
                issues += 1
            if not any("HEALTHCHECK" in l for l in lines):
                self._add_finding(Finding(id="CONT-005", category="security", severity=Severity.LOW.value,
                    status=Status.INFO.value, title=f"No HEALTHCHECK in {df_path}",
                    confidence=0.7, files=[{"path": df_path}],
                    recommendation="Add HEALTHCHECK for production containers."))
            if not any("multi-stage" in l.lower() or "AS " in l for l in lines):
                if len(lines) > 20:
                    self._add_finding(Finding(id="CONT-006", category="security", severity=Severity.LOW.value,
                        status=Status.INFO.value, title=f"No multi-stage build in {df_path}",
                        confidence=0.6, files=[{"path": df_path}],
                        recommendation="Use multi-stage builds to reduce image size."))

        score = max(0, 90 - issues * 10)
        self._set_raw_data("container", {"has_dockerfile": True, "dockerfiles": dockerfiles,
            "issues": issues, "score": score})
        self._add_metric("container_score", score)
        self._add_metric("has_dockerfile", True)
        return self._build_result(_t.time() - start)


@register_analyzer
class DeadCodeAnalyzer(AnalyzerBase):
    """Detects likely unused imports and unreachable code."""
    ANALYZER_ID = "dead_code"; ANALYZER_NAME = "Dead Code Analysis"
    CATEGORY = "maintainability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        unused_imports = 0; unreachable_code = 0

        for filepath, fname, root in _walk_python_files(repo_path):
            if os.path.basename(root) in ("tests", "test"): continue
            content = _safe_read(filepath)
            rel = os.path.relpath(filepath, repo_path)
            try: tree = ast.parse(content)
            except SyntaxError: continue

            # Check for unused imports
            imported_names = set()
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name != "*":
                            imported_names.add(alias.asname or alias.name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)

            unused = imported_names - used_names - {"__all__", "__version__"}
            for name in unused:
                unused_imports += 1
                if unused_imports <= 20:  # Limit findings
                    self._add_finding(Finding(id="DEAD-001", category="maintainability", severity=Severity.LOW.value,
                        status=Status.WARN.value, title=f"Unused import: {name} in {rel}",
                        confidence=0.6, files=[{"path": rel}],
                        evidence=f"Import '{name}' not used in file",
                        recommendation="Remove unused import."))

            # Check for unreachable code after return/raise
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for i, stmt in enumerate(node.body):
                        if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                            if i < len(node.body) - 1:
                                unreachable_code += 1
                                if unreachable_code <= 10:
                                    self._add_finding(Finding(id="DEAD-002", category="maintainability",
                                        severity=Severity.LOW.value, status=Status.WARN.value,
                                        title=f"Unreachable code after {type(stmt).__name__} in {rel}:{node.lineno}",
                                        confidence=0.8, files=[{"path": rel, "line_start": node.lineno}],
                                        recommendation="Remove unreachable code."))

        score = max(0, 90 - min(30, unused_imports * 2 + unreachable_code * 3))
        self._set_raw_data("dead_code", {"unused_imports": unused_imports, "unreachable": unreachable_code, "score": score})
        self._add_metric("dead_code_score", score)
        self._add_metric("unused_imports", unused_imports)
        self._add_metric("unreachable_code", unreachable_code)
        return self._build_result(_t.time() - start)


@register_analyzer
class DuplicationAnalyzer(AnalyzerBase):
    """Detects duplicated code blocks across Python files."""
    ANALYZER_ID = "duplication"; ANALYZER_NAME = "Code Duplication"
    CATEGORY = "maintainability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        # Simple approach: hash normalized 6-line blocks
        block_hashes = {}
        duplicates = 0
        min_lines = 6

        for filepath, fname, root in _walk_python_files(repo_path):
            if os.path.basename(root) in ("tests", "test"): continue
            content = _safe_read(filepath)
            rel = os.path.relpath(filepath, repo_path)
            lines = content.splitlines()
            for i in range(len(lines) - min_lines + 1):
                block = "\n".join(l.strip() for l in lines[i:i+min_lines] if l.strip() and not l.strip().startswith("#"))
                if len(block) < 50: continue
                h = hashlib.md5(block.encode()).hexdigest()
                if h in block_hashes:
                    duplicates += 1
                    if duplicates <= 15:
                        orig = block_hashes[h]
                        self._add_finding(Finding(id="DUP-001", category="maintainability", severity=Severity.LOW.value,
                            status=Status.WARN.value, title=f"Duplicated code block in {rel} (line {i+1})",
                            confidence=0.7, files=[{"path": rel, "line_start": i+1}, {"path": orig[0], "line_start": orig[1]}],
                            evidence=f"Block matches {orig[0]}:{orig[1]}", recommendation="Extract to a shared function."))
                else:
                    block_hashes[h] = (rel, i + 1)

        score = max(0, 100 - min(40, duplicates * 3))
        self._set_raw_data("duplication", {"duplicate_blocks": duplicates, "score": score})
        self._add_metric("duplication_score", score)
        self._add_metric("duplicate_blocks", duplicates)
        return self._build_result(_t.time() - start)


@register_analyzer
class ConfigAnalyzer(AnalyzerBase):
    """Analyzes configuration files and environment variables."""
    ANALYZER_ID = "config"; ANALYZER_NAME = "Configuration Analysis"
    CATEGORY = "reliability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        config_files = []; env_vars_in_code = set(); env_vars_documented = set()
        has_env_example = False; has_dotenv = False

        for filepath, fname, root in _walk_all_files(repo_path):
            rel = os.path.relpath(filepath, repo_path)
            if fname == ".env":
                has_dotenv = True
                content = _safe_read(filepath)
                config_files.append(rel)
                for line in content.splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        env_vars_documented.add(line.split("=")[0].strip())
            elif fname == ".env.example" or fname == ".env.sample":
                has_env_example = True
                content = _safe_read(filepath)
                for line in content.splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        env_vars_documented.add(line.split("=")[0].strip())
            elif fname.endswith(".py"):
                content = _safe_read(filepath)
                # Find os.environ and os.getenv references
                for m in re.finditer(r'os\.(?:environ(?:\.get)?|getenv)\(["\']([^"\']+)["\']', content):
                    env_vars_in_code.add(m.group(1))

        # Check for undocumented env vars
        undocumented = env_vars_in_code - env_vars_documented
        for var in list(undocumented)[:10]:
            self._add_finding(Finding(id="ENV-003", category="reliability", severity=Severity.LOW.value,
                status=Status.WARN.value, title=f"Undocumented environment variable: {var}",
                confidence=0.7, evidence=f"Code references {var} but no .env.example documents it",
                recommendation="Document required environment variables in .env.example."))

        # Check for committed .env (potential secrets)
        if has_dotenv:
            self._add_finding(Finding(id="ENV-001", category="security", severity=Severity.HIGH.value,
                status=Status.WARN.value, title=".env file committed to repository",
                confidence=0.85, evidence=".env file found in repository root",
                recommendation="Add .env to .gitignore and use .env.example instead."))

        if not has_env_example and env_vars_in_code:
            self._add_finding(Finding(id="ENV-002", category="reliability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No .env.example file despite environment variable usage",
                confidence=0.8, evidence=f"Code references {len(env_vars_in_code)} env vars but no .env.example",
                recommendation="Create .env.example with all required variables."))

        score = 70
        if has_env_example: score += 15
        if has_dotenv: score -= 20
        if undocumented: score -= min(15, len(undocumented) * 3)

        self._set_raw_data("config", {"has_env_example": has_env_example, "has_dotenv": has_dotenv,
            "env_vars_in_code": len(env_vars_in_code), "undocumented": len(undocumented), "score": max(0, score)})
        self._add_metric("config_score", max(0, score))
        self._add_metric("undocumented_env_vars", len(undocumented))
        return self._build_result(_t.time() - start)


@register_analyzer
class ObservabilityAnalyzer(AnalyzerBase):
    """Checks for logging, metrics, tracing, and health checks."""
    ANALYZER_ID = "observability"; ANALYZER_NAME = "Observability"
    CATEGORY = "reliability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        profile = context.get("discovery", {}).get("project_profile", "UNKNOWN")
        has_logging = has_structured = has_metrics = has_tracing = has_health = False

        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath)
            if "import logging" in content or "getLogger" in content or "logger" in content.lower():
                has_logging = True
            if "structlog" in content or "json.dumps" in content and "log" in content.lower():
                has_structured = True
            if "prometheus" in content.lower() or "metrics" in content.lower() and "counter" in content.lower():
                has_metrics = True
            if "opentelemetry" in content.lower() or "jaeger" in content.lower() or "trace" in content.lower():
                has_tracing = True
            if "health" in content.lower() and ("endpoint" in content.lower() or "route" in content.lower() or "/health" in content):
                has_health = True

        # Context-aware: CLI doesn't need observability
        if profile in ("CLI", "SCRIPT", "LIBRARY", "EDUCATIONAL", "EXPERIMENT"):
            score = 70 if has_logging else 40
            self._set_raw_data("observability", {"profile": profile, "has_logging": has_logging,
                "note": f"Reduced expectations for {profile} profile", "score": score})
            self._add_metric("observability_score", score)
            return self._build_result(_t.time() - start)

        # Service/API profiles need more
        score = 30
        if has_logging: score += 20
        if has_structured: score += 15
        if has_metrics: score += 15
        if has_tracing: score += 10
        if has_health: score += 10

        if not has_logging:
            self._add_finding(Finding(id="OBS-001", category="reliability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No logging framework detected", confidence=0.85,
                recommendation="Add structured logging."))
        if not has_health and profile in ("API", "BACKEND_SERVICE", "WEB_APP"):
            self._add_finding(Finding(id="OBS-002", category="reliability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No health check endpoint for service", confidence=0.7,
                recommendation="Add /health endpoint for production services."))
        if not has_metrics and profile in ("API", "BACKEND_SERVICE"):
            self._add_finding(Finding(id="OBS-003", category="reliability", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No metrics collection detected", confidence=0.6,
                recommendation="Consider adding Prometheus or similar metrics."))

        self._set_raw_data("observability", {"has_logging": has_logging, "has_structured": has_structured,
            "has_metrics": has_metrics, "has_tracing": has_tracing, "has_health": has_health, "score": score})
        self._add_metric("observability_score", score)
        return self._build_result(_t.time() - start)


@register_analyzer
class APIAnalysisAnalyzer(AnalyzerBase):
    """Analyzes API routes, validation, and documentation for web/API projects."""
    ANALYZER_ID = "api_analysis"; ANALYZER_NAME = "API Analysis"
    CATEGORY = "architecture"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        profile = context.get("discovery", {}).get("project_profile", "UNKNOWN")
        frameworks = context.get("discovery", {}).get("frameworks", [])

        # Only run for API/web profiles
        if profile not in ("API", "WEB_APP", "BACKEND_SERVICE"):
            self._set_raw_data("api", {"applicable": False, "score": 50, "note": f"Not applicable for {profile}"})
            self._add_metric("api_score", 50)
            return self._build_result(_t.time() - start)

        routes = []; has_openapi = has_validation = has_auth = False

        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath)
            rel = os.path.relpath(filepath, repo_path)
            # Detect Flask/FastAPI/Django routes
            for m in re.finditer(r'@(?:app|router|blueprint)\.(get|post|put|delete|patch|route)\(["\']([^"\']+)["\']', content):
                routes.append({"method": m.group(1).upper(), "path": m.group(2), "file": rel})
            if "openapi" in content.lower() or "swagger" in content.lower() or "api.yaml" in fname.lower():
                has_openapi = True
            if "pydantic" in content.lower() or "BaseModel" in content or "marshmallow" in content.lower():
                has_validation = True
            if "jwt" in content.lower() or "auth" in content.lower() or "token" in content.lower():
                has_auth = True

        # Check for openapi spec files
        for spec_file in ["openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json"]:
            if os.path.exists(os.path.join(repo_path, spec_file)):
                has_openapi = True

        if routes and not has_openapi:
            self._add_finding(Finding(id="API-001", category="architecture", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"API has {len(routes)} routes but no OpenAPI/Swagger spec",
                confidence=0.85, evidence=f"Routes: {len(routes)}", recommendation="Add OpenAPI documentation."))
        if routes and not has_validation:
            self._add_finding(Finding(id="API-002", category="architecture", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No input validation framework detected",
                confidence=0.7, recommendation="Use Pydantic or similar for input validation."))
        if routes and not has_auth:
            self._add_finding(Finding(id="API-003", category="security", severity=Severity.LOW.value,
                status=Status.INFO.value, title="No authentication mechanism detected",
                confidence=0.5, recommendation="Consider adding authentication for API endpoints."))

        score = 50
        if has_openapi: score += 20
        if has_validation: score += 15
        if has_auth: score += 15
        if len(routes) > 0: score = min(score, 85)

        self._set_raw_data("api", {"routes": len(routes), "has_openapi": has_openapi,
            "has_validation": has_validation, "has_auth": has_auth, "score": score})
        self._add_metric("api_score", score)
        self._add_metric("route_count", len(routes))
        return self._build_result(_t.time() - start)

