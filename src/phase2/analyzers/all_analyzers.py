"""
Phase 2 Analyzers — all analyzer modules.
Each analyzer extends AnalyzerBase and registers via @register_analyzer.
"""
from __future__ import annotations
import os, re, ast, json, subprocess
from collections import Counter
from typing import Any

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


@register_analyzer
class RepositoryDiscoveryAnalyzer(AnalyzerBase):
    ANALYZER_ID = "repository_discovery"; ANALYZER_NAME = "Repository Discovery"
    CATEGORY = "discovery"; VERSION = "2.0.0"
    LANG_BY_EXT = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
                   ".tsx": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
                   ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C/C++",
                   ".swift": "Swift", ".scala": "Scala", ".sh": "Shell", ".sql": "SQL",
                   ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".vue": "Vue", ".svelte": "Svelte"}

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        languages = Counter(); frameworks = []; package_managers = []
        build_systems = []; test_frameworks = []; lockfiles = []
        ci_configs = []; config_files = []; entrypoints = []
        total_files = 0; source_files = 0; test_files = 0; generated_files = 0
        services = []; applications = []; libraries = []
        generated_code = []; vendor_dirs = []

        for filepath, fname, root in _walk_files_all(repo_path):
            total_files += 1; ext = os.path.splitext(fname)[1].lower()
            if ext in self.LANG_BY_EXT:
                languages[self.LANG_BY_EXT[ext]] += 1; source_files += 1
            dir_name = os.path.basename(root)
            if fname.startswith("test_") or fname.endswith("_test.py") or \
               fname.endswith(".test.js") or fname.endswith(".spec.ts") or dir_name in ("tests", "test"):
                test_files += 1
            if fname.endswith(".pb.go") or fname.endswith("_pb2.py") or "generated" in filepath.lower():
                generated_files += 1
            if fname in ("main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs", "server.js"):
                entrypoints.append(os.path.relpath(filepath, repo_path))

        pm_map = {"requirements.txt": "pip", "pyproject.toml": "pip/poetry", "setup.py": "setuptools",
                  "package.json": "npm", "Cargo.toml": "cargo", "go.mod": "go modules",
                  "Gemfile": "bundler", "pom.xml": "maven"}
        for fname, pm in pm_map.items():
            if os.path.exists(os.path.join(repo_path, fname)): package_managers.append(pm)

        pkg_json = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_json):
            c = _safe_read(pkg_json)
            try:
                pkg = json.loads(c)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps: frameworks.append("React")
                if "vue" in deps: frameworks.append("Vue")
                if "next" in deps: frameworks.append("Next.js")
                if "express" in deps: frameworks.append("Express")
                if "jest" in deps or "vitest" in deps: test_frameworks.append("Jest/Vitest")
            except json.JSONDecodeError: pass

        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            c = _safe_read(req_path).lower()
            if "django" in c: frameworks.append("Django")
            if "flask" in c: frameworks.append("Flask")
            if "fastapi" in c: frameworks.append("FastAPI")
            if "pytest" in c: test_frameworks.append("pytest")

        if os.path.exists(os.path.join(repo_path, "go.mod")):
            build_systems.append("go"); test_frameworks.append("go test")
            if os.path.exists(os.path.join(repo_path, "go.sum")): lockfiles.append("go.sum")
        if os.path.exists(os.path.join(repo_path, "Cargo.toml")):
            build_systems.append("cargo"); test_frameworks.append("cargo test")
            if os.path.exists(os.path.join(repo_path, "Cargo.lock")): lockfiles.append("Cargo.lock")

        ci_paths = [(".github/workflows", "GitHub Actions"), (".gitlab-ci.yml", "GitLab CI"),
                    (".circleci/config.yml", "CircleCI"), ("Jenkinsfile", "Jenkins")]
        for ci_path, ci_name in ci_paths:
            if os.path.exists(os.path.join(repo_path, ci_path)):
                ci_configs.append({"system": ci_name, "path": ci_path})

        for cp in [".env", ".env.example", "config.yaml", "config.yml", "docker-compose.yml"]:
            if os.path.exists(os.path.join(repo_path, cp)): config_files.append(cp)

        if os.path.exists(os.path.join(repo_path, "Dockerfile")): services.append("Docker container")
        has_main = bool(entrypoints)
        if package_managers and not has_main: libraries.append("Library")

        is_monorepo = any(os.path.exists(os.path.join(repo_path, m)) for m in
                         ["lerna.json", "nx.json", "pnpm-workspace.yaml", "turbo.json"])

        profile = self._detect_profile(languages, frameworks, entrypoints, is_monorepo, services)

        discovery = {"repository_type": "monorepo" if is_monorepo else "single_project",
            "languages": dict(languages.most_common(10)),
            "primary_language": languages.most_common(1)[0][0] if languages else "unknown",
            "frameworks": list(set(frameworks)), "package_managers": list(set(package_managers)),
            "build_systems": list(set(build_systems)), "test_frameworks": list(set(test_frameworks)),
            "services": services, "applications": applications, "libraries": libraries,
            "lockfiles": lockfiles, "ci_configs": ci_configs, "config_files": config_files,
            "entrypoints": entrypoints, "is_monorepo": is_monorepo, "project_profile": profile,
            "file_stats": {"total_files": total_files, "source_files": source_files,
                           "test_files": test_files, "generated_files": generated_files,
                           "source_to_test_ratio": round(test_files/max(1,source_files), 3)}}

        if total_files == 0:
            self._add_finding(Finding(id="DISC-001", category="discovery", severity=Severity.CRITICAL.value,
                status=Status.FAIL.value, title="Empty repository", confidence=1.0,
                evidence=f"Total files: {total_files}", impact="No engineering value."))
        if not package_managers and total_files > 5:
            self._add_finding(Finding(id="DISC-003", category="discovery", severity=Severity.LOW.value,
                status=Status.WARN.value, title="No package manager detected", confidence=0.8,
                evidence="No package manifest found.", recommendation="Add a package manifest."))
        if not lockfiles and package_managers:
            self._add_finding(Finding(id="DISC-004", category="discovery", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No lockfile detected", confidence=0.85,
                evidence="No lockfile found.", impact="Builds may not be reproducible.",
                recommendation="Generate a lockfile."))
        if not ci_configs and total_files > 10:
            self._add_finding(Finding(id="DISC-005", category="discovery", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No CI/CD configuration detected", confidence=0.9,
                evidence="No CI config found.", recommendation="Add CI/CD configuration."))

        self._set_raw_data("discovery", discovery)
        self._add_metric("total_files", total_files)
        self._add_metric("project_profile", profile)
        self._add_metric("primary_language", discovery["primary_language"])
        return self._build_result(_t.time() - start)

    def _detect_profile(self, languages, frameworks, entrypoints, is_monorepo, services):
        if is_monorepo: return ProjectProfile.MONOREPO.value
        web_fw = {"Django", "Flask", "FastAPI", "React", "Vue", "Next.js", "Express"}
        has_web = bool(set(frameworks) & web_fw)
        api_fw = {"FastAPI", "Flask", "Django", "Express"}
        has_api = bool(set(frameworks) & api_fw)
        if has_api and ("FastAPI" in frameworks or "Flask" in frameworks): return ProjectProfile.API.value
        if has_web and ("React" in frameworks or "Vue" in frameworks): return ProjectProfile.FRONTEND.value
        if has_web: return ProjectProfile.WEB_APP.value
        if services: return ProjectProfile.BACKEND_SERVICE.value
        if entrypoints: return ProjectProfile.CLI.value
        return ProjectProfile.UNKNOWN.value


def _walk_files_all(repo_path):
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files: yield os.path.join(root, f), f, root


@register_analyzer
class DocumentationAnalyzer(AnalyzerBase):
    ANALYZER_ID = "documentation"; ANALYZER_NAME = "Documentation Quality"
    CATEGORY = "documentation"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        readme = self._check_readme(repo_path)
        license_data = self._check_license(repo_path)
        score = 0
        if readme["found"]:
            score += 10
            if readme["length_chars"] > 500: score += 5
            if readme["length_chars"] > 2000: score += 5
            for kw in ["install", "usage", "test", "contribut", "license", "example"]:
                if readme.get(f"has_{kw}"): score += 5
        else:
            self._add_finding(Finding(id="DOC-001", category="documentation", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title="No README file found", confidence=1.0,
                evidence="No README found.", recommendation="Create a README.md."))
        if license_data["found"]: score += 5
        else:
            self._add_finding(Finding(id="DOC-LIC-002", category="documentation", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title="No LICENSE file found", confidence=0.95,
                recommendation="Add a LICENSE file."))
        self._set_raw_data("documentation", {"readme": readme, "license": license_data, "score": max(0,min(100,score))})
        self._add_metric("documentation_score", max(0, min(100, score)))
        return self._build_result(_t.time() - start)

    def _check_readme(self, repo_path):
        for name in ["README.md", "README.rst", "README.txt", "README", "readme.md"]:
            path = os.path.join(repo_path, name)
            if os.path.exists(path):
                content = _safe_read(path); lower = content.lower()
                return {"found": True, "filename": name, "length_chars": len(content),
                        "has_install": "install" in lower, "has_usage": "usage" in lower or "example" in lower,
                        "has_test": "test" in lower, "has_contribut": "contribut" in lower,
                        "has_license": "license" in lower, "has_example": "```" in content}
        return {"found": False}

    def _check_license(self, repo_path):
        for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
            path = os.path.join(repo_path, name)
            if os.path.exists(path):
                content = _safe_read(path).lower()
                is_std = any(kw in content for kw in ["mit license", "apache license", "bsd license", "gnu general"])
                return {"found": True, "filename": name, "is_standard": is_std}
        return {"found": False, "filename": None, "is_standard": False}


@register_analyzer
class StructureAnalyzer(AnalyzerBase):
    ANALYZER_ID = "structure"; ANALYZER_NAME = "Structure & Architecture"
    CATEGORY = "architecture"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        total_loc = code_loc = test_loc = 0; file_sizes = {}; cyclic = []
        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath); rel = os.path.relpath(filepath, repo_path)
            lines = content.splitlines(); loc = len(lines); total_loc += loc
            file_sizes[rel] = loc
            is_test = fname.startswith("test_") or os.path.basename(root) in ("tests", "test")
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"): code_loc += 1
                if is_test: test_loc += 1
            if loc > 1000:
                self._add_finding(Finding(id="ARCH-004", category="architecture", severity=Severity.HIGH.value,
                    status=Status.WARN.value, title=f"Oversized file: {rel} ({loc} LOC)",
                    confidence=0.9, files=[{"path": rel}], evidence=f"LOC: {loc}",
                    recommendation="Split the file into smaller modules."))
        edges = set()
        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath)
            try: tree = ast.parse(content)
            except SyntaxError: continue
            rel = os.path.relpath(filepath, repo_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for fp2, _, _ in _walk_python_files(repo_path):
                        rel2 = os.path.relpath(fp2, repo_path)
                        if node.module in rel2 and (rel2, rel) in edges:
                            cyclic.append({"a": rel, "b": rel2})
                        edges.add((rel, node.module))
        for c in cyclic[:10]:
            self._add_finding(Finding(id="ARCH-002", category="architecture", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"Circular dependency: {c['a']} <-> {c['b']}",
                confidence=0.75, evidence="Mutual import", recommendation="Break the cycle."))
        score = 70 - len(cyclic)*5 - sum(10 for f in file_sizes.values() if f > 1000)
        if test_loc > 0 and code_loc > 0:
            ratio = test_loc / code_loc
            if ratio > 0.5: score += 10
            elif ratio > 0.2: score += 5
        if test_loc == 0 and code_loc > 100: score -= 15
        self._set_raw_data("structure", {"total_loc": total_loc, "code_loc": code_loc, "test_loc": test_loc,
            "cyclic_deps": cyclic[:10], "score": max(0, min(100, score))})
        self._add_metric("architecture_score", max(0, min(100, score)))
        self._add_metric("cyclic_dependencies", len(cyclic))
        return self._build_result(_t.time() - start)


@register_analyzer
class TestingAnalyzer(AnalyzerBase):
    ANALYZER_ID = "testing"; ANALYZER_NAME = "Testing Quality"
    CATEGORY = "testing"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        test_files = []; test_functions = 0; source_functions = 0
        tests_without_assertions = 0; skipped_tests = 0
        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath)
            try: tree = ast.parse(content)
            except SyntaxError: continue
            rel = os.path.relpath(filepath, repo_path)
            dir_name = os.path.basename(root)
            is_test = fname.startswith("test_") or fname.endswith("_test.py") or dir_name in ("tests", "test")
            func_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            if is_test:
                test_files.append(rel); test_functions += func_count
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        has_assert = any(isinstance(n, (ast.Assert,)) or
                            (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                             "assert" in n.func.attr.lower()) for n in ast.walk(node))
                        if not has_assert: tests_without_assertions += 1
            else: source_functions += func_count
        if test_functions == 0 and source_functions > 0:
            self._add_finding(Finding(id="TEST-003", category="testing", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title="No tests found", confidence=1.0,
                evidence=f"Source functions: {source_functions}, test functions: 0",
                recommendation="Add tests."))
        ratio = test_functions / source_functions if source_functions > 0 else 0.0
        score = 50
        if test_functions > 0: score += 15
        if ratio > 0.5: score += 20
        elif ratio > 0.2: score += 10
        if tests_without_assertions > 0: score -= min(20, tests_without_assertions * 2)
        self._set_raw_data("testing", {"test_file_count": len(test_files), "test_function_count": test_functions,
            "source_function_count": source_functions, "test_to_source_ratio": round(ratio, 3),
            "tests_without_assertions": tests_without_assertions, "score": max(0, min(100, score))})
        self._add_metric("testing_score", max(0, min(100, score)))
        self._add_metric("test_function_count", test_functions)
        self._add_metric("test_to_source_ratio", round(ratio, 3))
        return self._build_result(_t.time() - start)


@register_analyzer
class ComplexityAnalyzer(AnalyzerBase):
    ANALYZER_ID = "complexity"; ANALYZER_NAME = "Complexity & Maintainability"
    CATEGORY = "maintainability"; VERSION = "2.0.0"
    THRESHOLDS = {"low": 3, "moderate": 5, "high": 7, "critical": 10}

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        functions = []; high_count = 0; critical_count = 0
        for filepath, fname, root in _walk_python_files(repo_path):
            if os.path.basename(root) in ("tests", "test"): continue
            content = _safe_read(filepath)
            try: tree = ast.parse(content)
            except SyntaxError: continue
            rel = os.path.relpath(filepath, repo_path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.Assert, ast.With)):
                            complexity += 1
                        if isinstance(child, ast.BoolOp): complexity += len(child.values) - 1
                    if complexity >= self.THRESHOLDS["critical"]:
                        critical_count += 1
                        self._add_finding(Finding(id="CPLX-001", category="maintainability",
                            severity=Severity.CRITICAL.value, status=Status.FAIL.value,
                            title=f"Critical complexity: {node.name} (={complexity})", confidence=0.95,
                            files=[{"path": rel, "line_start": node.lineno}],
                            evidence=f"Complexity: {complexity}", recommendation="Refactor."))
                    elif complexity >= self.THRESHOLDS["high"]:
                        high_count += 1
                        self._add_finding(Finding(id="CPLX-002", category="maintainability",
                            severity=Severity.HIGH.value, status=Status.WARN.value,
                            title=f"High complexity: {node.name} (={complexity})", confidence=0.9,
                            files=[{"path": rel, "line_start": node.lineno}], recommendation="Consider refactoring."))
                    functions.append({"name": node.name, "complexity": complexity, "file": rel})
        avg = sum(f["complexity"] for f in functions) / max(1, len(functions))
        score = 100 - min(40, critical_count * 10) - min(25, high_count * 5)
        if avg > self.THRESHOLDS["high"]: score -= 15
        self._set_raw_data("complexity", {"avg": round(avg, 2), "high": high_count, "critical": critical_count, "score": max(0,min(100,score))})
        self._add_metric("maintainability_score", max(0, min(100, score)))
        self._add_metric("avg_complexity", round(avg, 2))
        self._add_metric("high_complexity_count", high_count)
        self._add_metric("critical_complexity_count", critical_count)
        return self._build_result(_t.time() - start)


@register_analyzer
class SecuritySASTAnalyzer(AnalyzerBase):
    ANALYZER_ID = "security_sast"; ANALYZER_NAME = "Security SAST"
    CATEGORY = "security"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        for filepath, fname, root in _walk_python_files(repo_path):
            if os.path.basename(root) in ("tests", "test"): continue
            content = _safe_read(filepath); rel = os.path.relpath(filepath, repo_path)
            try: tree = ast.parse(content)
            except SyntaxError: continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fn = self._get_name(node)
                    if fn == "eval":
                        self._add_finding(Finding(id="SEC-EVAL-001", category="security", severity=Severity.HIGH.value,
                            status=Status.FAIL.value, title="Use of eval()", confidence=0.9, cwe_id="CWE-95",
                            files=[{"path": rel, "line_start": node.lineno}], evidence=f"Line {node.lineno}: eval()",
                            recommendation="Replace with ast.literal_eval()."))
                    if fn == "exec":
                        self._add_finding(Finding(id="SEC-EXEC-001", category="security", severity=Severity.HIGH.value,
                            status=Status.FAIL.value, title="Use of exec()", confidence=0.9, cwe_id="CWE-95",
                            files=[{"path": rel, "line_start": node.lineno}], recommendation="Avoid exec()."))
                    if fn in ("Popen", "run", "call", "check_output", "check_call"):
                        for kw in node.keywords:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                self._add_finding(Finding(id="SEC-CMD-001", category="security", severity=Severity.CRITICAL.value,
                                    status=Status.FAIL.value, title="Potential command injection (shell=True)", confidence=0.85,
                                    cwe_id="CWE-78", files=[{"path": rel, "line_start": node.lineno}],
                                    evidence=f"Line {node.lineno}: subprocess.{fn}(shell=True)",
                                    recommendation="Use shell=False.", references=["OWASP A03:2021"]))
                    if fn in ("loads", "load") and self._is_unsafe_deser(node):
                        self._add_finding(Finding(id="SEC-DESER-001", category="security", severity=Severity.CRITICAL.value,
                            status=Status.FAIL.value, title="Unsafe deserialization", confidence=0.75, cwe_id="CWE-502",
                            files=[{"path": rel, "line_start": node.lineno}], recommendation="Use json.loads()."))
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    self._add_finding(Finding(id="SEC-EXCEPT-001", category="security", severity=Severity.MEDIUM.value,
                        status=Status.WARN.value, title="Bare except clause", confidence=0.9, cwe_id="CWE-396",
                        files=[{"path": rel, "line_start": node.lineno}], recommendation="Use specific exceptions."))
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if not stripped.startswith("#"):
                    if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', stripped, re.IGNORECASE):
                        masked = re.sub(r'(["\']).{8,}(["\'])', r'\1***MASKED***\2', stripped)
                        self._add_finding(Finding(id="SEC-SECRET-001", category="security", severity=Severity.HIGH.value,
                            status=Status.FAIL.value, title="Potential hardcoded secret", confidence=0.7, cwe_id="CWE-798",
                            files=[{"path": rel, "line_start": i}], evidence=f"Line {i}: {masked}",
                            recommendation="Use environment variables."))
                    if "shell=True" in stripped:
                        self._add_finding(Finding(id="SEC-SHELL-001", category="security", severity=Severity.HIGH.value,
                            status=Status.WARN.value, title="shell=True in subprocess", confidence=0.7, cwe_id="CWE-78",
                            files=[{"path": rel, "line_start": i}], recommendation="Use shell=False."))
                    if re.search(r'verify\s*=\s*False', stripped, re.IGNORECASE):
                        self._add_finding(Finding(id="SEC-TLS-001", category="security", severity=Severity.HIGH.value,
                            status=Status.FAIL.value, title="TLS verification disabled", confidence=0.85, cwe_id="CWE-295",
                            files=[{"path": rel, "line_start": i}], recommendation="Enable verification."))
                    if re.search(r'debug\s*=\s*True', stripped, re.IGNORECASE):
                        self._add_finding(Finding(id="SEC-DEBUG-001", category="security", severity=Severity.MEDIUM.value,
                            status=Status.WARN.value, title="Debug mode enabled", confidence=0.6, cwe_id="CWE-489",
                            files=[{"path": rel, "line_start": i}], recommendation="Disable in production."))
        score = 100
        for f in self.findings:
            score -= {Severity.CRITICAL.value: 25, Severity.HIGH.value: 15,
                      Severity.MEDIUM.value: 8, Severity.LOW.value: 3}.get(f.severity, 0)
        self._set_raw_data("security", {"score": max(0, min(100, score)), "issue_count": len(self.findings)})
        self._add_metric("security_score", max(0, min(100, score)))
        self._add_metric("critical_count", sum(1 for f in self.findings if f.severity == Severity.CRITICAL.value))
        return self._build_result(_t.time() - start)

    def _get_name(self, node):
        if isinstance(node.func, ast.Name): return node.func.id
        if isinstance(node.func, ast.Attribute): return node.func.attr
        return ""
    def _is_unsafe_deser(self, node):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            return node.func.value.id in ("pickle", "cPickle", "marshal", "yaml") and node.func.attr == "load"
        return False


@register_analyzer
class DependencyAnalyzer(AnalyzerBase):
    ANALYZER_ID = "dependencies"; ANALYZER_NAME = "Dependency & Supply Chain"
    CATEGORY = "dependencies"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        deps = []; total = 0; source = None; lockfile = False
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            content = _safe_read(req_path)
            deps = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
            total = len(deps); source = "requirements.txt"
            lockfile = os.path.exists(os.path.join(repo_path, "poetry.lock"))
        pj_path = os.path.join(repo_path, "package.json")
        if os.path.exists(pj_path):
            try:
                pkg = json.loads(_safe_read(pj_path))
                deps = list(pkg.get("dependencies", {}).keys())
                total = len(deps); source = "package.json"
                lockfile = any(os.path.exists(os.path.join(repo_path, lf)) for lf in ["package-lock.json", "yarn.lock"])
            except: pass
        if total > 50:
            self._add_finding(Finding(id="DEP-003", category="dependencies", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"Excessive dependencies: {total}", confidence=0.85,
                evidence=f"Total deps: {total}", recommendation="Reduce dependencies."))
        if total > 0 and not lockfile:
            self._add_finding(Finding(id="DEP-001", category="dependencies", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No lockfile present", confidence=0.9,
                evidence=f"Source: {source}", recommendation="Generate a lockfile."))
        wf_dir = os.path.join(repo_path, ".github", "workflows")
        if os.path.isdir(wf_dir):
            for wf in os.listdir(wf_dir):
                if not wf.endswith((".yml", ".yaml")): continue
                content = _safe_read(os.path.join(wf_dir, wf))
                for i, line in enumerate(content.splitlines(), 1):
                    if line.strip().startswith("uses:") and "@" in line:
                        ref = line.strip().split("@")[1].split()[0] if "@" in line.strip() else ""
                        action = line.strip().replace("uses:", "").strip().split("@")[0]
                        if not action.startswith("actions/") and not re.match(r'^[0-9a-f]{40}$', ref):
                            self._add_finding(Finding(id="DEP-CI-001", category="dependencies", severity=Severity.MEDIUM.value,
                                status=Status.WARN.value, title=f"Unpinned GitHub Action: {action}@{ref}", confidence=0.8,
                                files=[{"path": f".github/workflows/{wf}", "line_start": i}],
                                evidence=f"uses: {action}@{ref}", recommendation="Pin to commit SHA."))
        score = 70
        if total <= 20 and total > 0: score += 15
        elif total > 50: score -= 20
        elif total > 30: score -= 10
        if lockfile: score += 10
        else: score -= 10
        self._set_raw_data("dependencies", {"total": total, "lockfile": lockfile, "score": max(0,min(100,score))})
        self._add_metric("dependency_score", max(0, min(100, score)))
        self._add_metric("total_dependencies", total)
        self._add_metric("lockfile_present", lockfile)
        return self._build_result(_t.time() - start)


@register_analyzer
class GitMaturityAnalyzer(AnalyzerBase):
    ANALYZER_ID = "git_maturity"; ANALYZER_NAME = "Git & Source Control Maturity"
    CATEGORY = "git"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        def _git(args):
            try:
                r = subprocess.run(["git"]+args, cwd=repo_path, capture_output=True, text=True, timeout=10)
                return r.stdout.strip() if r.returncode == 0 else ""
            except: return ""
        commits_str = _git(["rev-list", "--count", "HEAD"])
        total_commits = int(commits_str) if commits_str.isdigit() else 0
        contributors = _git(["shortlog", "-sn", "HEAD"])
        contrib_list = [l.strip() for l in contributors.splitlines() if l.strip()]
        recent = _git(["log", "--since=30 days ago", "--oneline"])
        recent_count = len([l for l in recent.splitlines() if l.strip()]) if recent else 0
        tags = _git(["tag", "--list"])
        tag_count = len([t for t in tags.splitlines() if t.strip()]) if tags else 0
        if len(contrib_list) <= 1 and total_commits > 5:
            self._add_finding(Finding(id="GIT-002", category="git", severity=Severity.LOW.value,
                status=Status.WARN.value, title="Single contributor (bus factor risk)", confidence=0.85,
                evidence=f"Contributors: {contrib_list}", recommendation="Encourage contributions."))
        if recent_count == 0 and total_commits > 0:
            self._add_finding(Finding(id="GIT-003", category="git", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title="No recent commits (30+ days)", confidence=0.85,
                evidence="0 commits in 30 days", recommendation="Verify if project is maintained."))
        score = 50
        if total_commits > 50: score += 10
        if len(contrib_list) > 3: score += 15
        elif len(contrib_list) > 1: score += 8
        if recent_count > 5: score += 15
        elif recent_count > 0: score += 8
        else: score -= 10
        if tag_count > 3: score += 5
        self._set_raw_data("git", {"total_commits": total_commits, "contributor_count": len(contrib_list),
            "recent_count": recent_count, "tag_count": tag_count, "score": max(0,min(100,score))})
        self._add_metric("git_score", max(0, min(100, score)))
        self._add_metric("total_commits", total_commits)
        self._add_metric("contributor_count", len(contrib_list))
        return self._build_result(_t.time() - start)


@register_analyzer
class CICDAnalyzer(AnalyzerBase):
    ANALYZER_ID = "cicd"; ANALYZER_NAME = "CI/CD Quality"
    CATEGORY = "cicd"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        wf_dir = os.path.join(repo_path, ".github", "workflows")
        has_ci = os.path.isdir(wf_dir) or os.path.exists(os.path.join(repo_path, ".gitlab-ci.yml"))
        runs_tests = runs_lint = runs_sec = False
        if os.path.isdir(wf_dir):
            for wf in os.listdir(wf_dir):
                if wf.endswith((".yml", ".yaml")):
                    c = _safe_read(os.path.join(wf_dir, wf)).lower()
                    if "pytest" in c or "npm test" in c or "cargo test" in c: runs_tests = True
                    if "ruff" in c or "eslint" in c or "flake8" in c: runs_lint = True
                    if "trivy" in c or "snyk" in c or "codeql" in c or "bandit" in c: runs_sec = True
        if not has_ci:
            self._add_finding(Finding(id="CICD-001", category="cicd", severity=Severity.HIGH.value,
                status=Status.FAIL.value, title="No CI/CD pipeline", confidence=0.95,
                evidence="No CI config found.", recommendation="Add CI/CD."))
        else:
            if not runs_tests:
                self._add_finding(Finding(id="CICD-002", category="cicd", severity=Severity.HIGH.value,
                    status=Status.FAIL.value, title="CI does not run tests", confidence=0.7,
                    recommendation="Add test step."))
        score = 10 if not has_ci else 50 + (20 if runs_tests else 0) + (10 if runs_lint else 0) + (10 if runs_sec else 0)
        self._set_raw_data("cicd", {"has_ci": has_ci, "score": max(0,min(100,score))})
        self._add_metric("cicd_score", max(0, min(100, score)))
        self._add_metric("has_ci", has_ci)
        return self._build_result(_t.time() - start)


@register_analyzer
class TechDebtAnalyzer(AnalyzerBase):
    ANALYZER_ID = "tech_debt"; ANALYZER_NAME = "Technical Debt"
    CATEGORY = "maintainability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        total = 0; by_type = {}
        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath); rel = os.path.relpath(filepath, repo_path)
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    lower = stripped.lower()
                    for marker in ["todo", "fixme", "hack", "xxx"]:
                        if marker in lower:
                            total += 1; by_type[marker.upper()] = by_type.get(marker.upper(), 0) + 1
        if total > 20:
            self._add_finding(Finding(id="DEBT-001", category="maintainability", severity=Severity.HIGH.value,
                status=Status.WARN.value, title=f"High technical debt: {total} markers", confidence=0.95,
                evidence=f"By type: {by_type}", recommendation="Address technical debt."))
        score = 100 - min(60, total * 3)
        self._set_raw_data("tech_debt", {"total": total, "by_type": by_type, "score": max(0,score)})
        self._add_metric("tech_debt_count", total)
        self._add_metric("tech_debt_score", max(0, score))
        return self._build_result(_t.time() - start)


@register_analyzer
class ErrorHandlingAnalyzer(AnalyzerBase):
    ANALYZER_ID = "error_handling"; ANALYZER_NAME = "Error Handling & Reliability"
    CATEGORY = "reliability"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        bare_except = 0; swallowed = 0; missing_timeout = 0
        for filepath, fname, root in _walk_python_files(repo_path):
            content = _safe_read(filepath); rel = os.path.relpath(filepath, repo_path)
            try: tree = ast.parse(content)
            except SyntaxError: continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None: bare_except += 1
                if isinstance(node, ast.ExceptHandler):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Pass): swallowed += 1; break
            for i, line in enumerate(content.splitlines(), 1):
                if ("requests.get" in line or "requests.post" in line) and "timeout" not in line:
                    missing_timeout += 1
        if bare_except > 0:
            self._add_finding(Finding(id="REL-001", category="reliability", severity=Severity.MEDIUM.value,
                status=Status.WARN.value, title=f"{bare_except} bare except clauses", confidence=0.9,
                recommendation="Use specific exceptions."))
        if missing_timeout > 0:
            self._add_finding(Finding(id="REL-003", category="reliability", severity=Severity.HIGH.value,
                status=Status.WARN.value, title=f"{missing_timeout} HTTP calls without timeout", confidence=0.75,
                recommendation="Add timeouts to HTTP calls."))
        score = 100 - bare_except * 3 - swallowed * 5 - missing_timeout * 8
        self._set_raw_data("error_handling", {"bare_except": bare_except, "swallowed": swallowed,
            "missing_timeout": missing_timeout, "score": max(0,score)})
        self._add_metric("reliability_score", max(0, min(100, score)))
        return self._build_result(_t.time() - start)


@register_analyzer
class ReproducibilityAnalyzer(AnalyzerBase):
    ANALYZER_ID = "reproducibility"; ANALYZER_NAME = "Reproducibility"
    CATEGORY = "reproducibility"; VERSION = "2.0.0"

    def analyze(self, repo_path, context):
        import time as _t; start = _t.time()
        lockfiles = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "go.sum", "poetry.lock"]
        has_lock = any(os.path.exists(os.path.join(repo_path, lf)) for lf in lockfiles)
        if not has_lock:
            self._add_finding(Finding(id="REPRO-001", category="reproducibility", severity=Severity.HIGH.value,
                status=Status.WARN.value, title="No lockfile", confidence=0.9,
                evidence="No lockfile found.", recommendation="Generate and commit a lockfile."))
        score = 20 if not has_lock else 80
        self._set_raw_data("reproducibility", {"has_lockfile": has_lock, "score": score})
        self._add_metric("reproducibility_score", score)
        self._add_metric("has_lockfile", has_lock)
        return self._build_result(_t.time() - start)
