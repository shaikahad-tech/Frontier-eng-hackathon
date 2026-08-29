"""
Repository analysis tools — the tools that agents use to gather real evidence
about a code repository, rather than just reading the README.

Each tool returns structured data that the agent can reason about and cite
in its quality assessment. All tools are pure functions with no side effects
(except run_tests, which runs the repo's test suite in a subprocess).

Design principles:
- Never crash: every tool returns a dict, even on error
- Always cite the source file/line where evidence was found
- Return structured data, not free text
- Skip irrelevant directories (.git, __pycache__, venv, node_modules)
"""

import ast
import json
import os
import re
import subprocess
from collections import Counter


# ─── Constants ───

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".eggs", "dist", "build", ".mypy_cache", ".pytest_cache"}


# ─── Helpers ───

def _safe_read(path: str, max_bytes: int = 50000) -> str:
    """Read a file safely, returning empty string on any error."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read(max_bytes)
    except Exception:
        return ""


def _walk_python_files(repo_path: str, skip_tests: bool = False):
    """Walk all Python files in a repo, skipping irrelevant directories.
    If skip_tests=True, also skip directories named 'tests' or 'test'."""
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if skip_tests:
            dirs[:] = [d for d in dirs if d not in ("tests", "test")]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f), f, root


# ─── Tool: Read README ───

def read_readme(repo_path: str) -> dict:
    """Read the README file from a repository."""
    for name in ["README.md", "README.rst", "README.txt", "README", "readme.md", "readme.txt"]:
        path = os.path.join(repo_path, name)
        if os.path.exists(path):
            content = _safe_read(path)
            return {
                "found": True,
                "filename": name,
                "length_chars": len(content),
                "length_lines": content.count("\n") + 1,
                "preview": content[:3000],
                "has_installation": "install" in content.lower(),
                "has_usage": "usage" in content.lower() or "example" in content.lower(),
                "has_testing": "test" in content.lower() or "pytest" in content.lower(),
            }
    return {"found": False, "filename": None, "length_chars": 0, "length_lines": 0, "preview": ""}


# ─── Tool: Analyze project structure ───

def analyze_structure(repo_path: str) -> dict:
    """Analyze the directory structure of a repository."""
    top_level = []

    try:
        entries = sorted(os.listdir(repo_path))
    except OSError:
        entries = []

    for entry in entries:
        if entry.startswith("."):
            continue
        full_path = os.path.join(repo_path, entry)
        if os.path.isdir(full_path):
            try:
                sub_entries = os.listdir(full_path)
                file_count = sum(1 for e in sub_entries if os.path.isfile(os.path.join(full_path, e)))
                dir_count = sum(1 for e in sub_entries if os.path.isdir(os.path.join(full_path, e)))
            except (PermissionError, OSError):
                file_count = 0
                dir_count = 0
            top_level.append({"name": entry, "type": "dir", "files": file_count, "subdirs": dir_count})
        else:
            top_level.append({"name": entry, "type": "file", "size_bytes": os.path.getsize(full_path)})

    # File extension stats
    extensions = Counter()
    total_files = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext:
                extensions[ext] += 1
            total_files += 1
    file_stats = {"total_files": total_files, "by_extension": dict(extensions.most_common(20))}

    # Detect project type
    has_setup_py = os.path.exists(os.path.join(repo_path, "setup.py"))
    has_pyproject = os.path.exists(os.path.join(repo_path, "pyproject.toml"))
    has_package_json = os.path.exists(os.path.join(repo_path, "package.json"))
    has_cargo_toml = os.path.exists(os.path.join(repo_path, "Cargo.toml"))
    has_go_mod = os.path.exists(os.path.join(repo_path, "go.mod"))
    has_makefile = os.path.exists(os.path.join(repo_path, "Makefile"))
    has_dockerfile = os.path.exists(os.path.join(repo_path, "Dockerfile"))
    has_requirements = os.path.exists(os.path.join(repo_path, "requirements.txt"))

    project_type = "unknown"
    if has_setup_py or has_pyproject or has_requirements:
        project_type = "python"
    elif has_package_json:
        project_type = "javascript/typescript"
    elif has_cargo_toml:
        project_type = "rust"
    elif has_go_mod:
        project_type = "go"

    # Count Python source files
    python_file_count = sum(1 for _, _, _ in _walk_python_files(repo_path))

    return {
        "top_level_entries": top_level[:30],
        "file_stats": file_stats,
        "project_type": project_type,
        "has_setup_py": has_setup_py,
        "has_pyproject": has_pyproject,
        "has_package_json": has_package_json,
        "has_dockerfile": has_dockerfile,
        "has_makefile": has_makefile,
        "has_requirements_txt": has_requirements,
        "python_file_count": python_file_count,
    }


# ─── Tool: Analyze dependencies ───

def analyze_dependencies(repo_path: str) -> dict:
    """Analyze the dependencies declared in the repository."""
    result = {"dependencies": [], "dev_dependencies": [], "total": 0, "source": None}

    # requirements.txt
    req_path = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(req_path):
        content = _safe_read(req_path)
        deps = [line.strip() for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")]
        result["dependencies"] = deps
        result["total"] = len(deps)
        result["source"] = "requirements.txt"

    # pyproject.toml (takes precedence if present)
    pp_path = os.path.join(repo_path, "pyproject.toml")
    if os.path.exists(pp_path):
        content = _safe_read(pp_path)
        dep_lines = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if "dependencies" in stripped and "[" in stripped:
                in_deps = True
            if in_deps:
                dep_lines.append(stripped)
                if "]" in stripped:
                    in_deps = False
        deps = []
        for line in dep_lines:
            matches = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*([><=~!]*\s*[\d.]*)?["\']?', line)
            for name, version in matches:
                if name not in ("dependencies", "dev", "dev-dependencies", "optional"):
                    deps.append(f"{name}{version}".strip())
        if deps:
            result["dependencies"] = deps
            result["total"] = len(deps)
            result["source"] = "pyproject.toml"

    # package.json
    pj_path = os.path.join(repo_path, "package.json")
    if os.path.exists(pj_path):
        content = _safe_read(pj_path)
        try:
            pkg = json.loads(content)
            result["dependencies"] = list(pkg.get("dependencies", {}).keys())
            result["dev_dependencies"] = list(pkg.get("devDependencies", {}).keys())
            result["total"] = len(result["dependencies"]) + len(result["dev_dependencies"])
            result["source"] = "package.json"
        except json.JSONDecodeError:
            pass

    # Cargo.toml
    cargo_path = os.path.join(repo_path, "Cargo.toml")
    if os.path.exists(cargo_path):
        content = _safe_read(cargo_path)
        deps = re.findall(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']', content, re.MULTILINE)
        result["dependencies"] = [d.strip() for d in deps]
        result["total"] = len(deps)
        result["source"] = "Cargo.toml"

    return result


# ─── Tool: Analyze test coverage (structural) ───

def analyze_tests(repo_path: str) -> dict:
    """Analyze the test files and test functions in the repository."""
    test_files = []
    test_functions = 0
    source_files = 0
    source_functions = 0

    for filepath, f, root in _walk_python_files(repo_path):
        rel_path = os.path.relpath(filepath, repo_path)
        content = _safe_read(filepath)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        func_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))

        rel_root = os.path.relpath(root, repo_path)
        dir_name = os.path.basename(rel_root)
        is_test = (
            f.startswith("test_")
            or f.endswith("_test.py")
            or dir_name in ("tests", "test")
        )

        if is_test:
            test_files.append(rel_path)
            test_functions += func_count
        else:
            source_files += 1
            source_functions += func_count

    has_pytest_ini = os.path.exists(os.path.join(repo_path, "pytest.ini"))
    has_tox_ini = os.path.exists(os.path.join(repo_path, "tox.ini"))
    has_conftest = os.path.exists(os.path.join(repo_path, "conftest.py"))
    has_ci = (
        os.path.exists(os.path.join(repo_path, ".github", "workflows"))
        or os.path.exists(os.path.join(repo_path, ".gitlab-ci.yml"))
    )

    ratio = test_functions / source_functions if source_functions > 0 else 0.0

    return {
        "test_files": test_files,
        "test_file_count": len(test_files),
        "test_function_count": test_functions,
        "source_file_count": source_files,
        "source_function_count": source_functions,
        "test_to_source_ratio": round(ratio, 3),
        "has_pytest_config": has_pytest_ini,
        "has_tox_config": has_tox_ini,
        "has_conftest": has_conftest,
        "has_ci": has_ci,
    }


# ─── Tool: Run tests ───

def run_tests(repo_path: str, timeout: int = 30) -> dict:
    """Attempt to run the test suite in the repository using pytest."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=no", "-q", "--no-header"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        passed = 0
        failed = 0
        errors = 0

        for line in result.stdout.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                m = re.search(r"(\d+)\s+passed", line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r"(\d+)\s+failed", line)
                if m:
                    failed = int(m.group(1))
                m = re.search(r"(\d+)\s+error", line)
                if m:
                    errors = int(m.group(1))
                if "no tests ran" in line:
                    return {
                        "runner": "pytest",
                        "ran": False,
                        "error": "no tests found",
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "exit_code": result.returncode,
                        "stdout_tail": result.stdout[-500:],
                        "stderr_tail": result.stderr[-500:] if result.stderr else "",
                    }

        return {
            "runner": "pytest",
            "ran": True,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "exit_code": result.returncode,
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"runner": "pytest", "ran": False, "error": "timeout", "timeout_seconds": timeout}
    except FileNotFoundError:
        return {"runner": "pytest", "ran": False, "error": "pytest not found"}
    except Exception as e:
        return {"runner": "pytest", "ran": False, "error": str(e)}


# ─── Tool: Analyze code complexity ───

def analyze_complexity(repo_path: str) -> dict:
    """Analyze cyclomatic complexity of Python functions using AST."""
    results = []
    total_complexity = 0
    total_functions = 0

    for filepath, f, root in _walk_python_files(repo_path, skip_tests=True):
        rel_path = os.path.relpath(filepath, repo_path)
        content = _safe_read(filepath)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                         ast.Assert, ast.With)):
                        complexity += 1
                    if isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                    if hasattr(ast, 'Match') and isinstance(child, ast.Match):
                        complexity += 1

                results.append({
                    "file": rel_path,
                    "function": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                })
                total_complexity += complexity
                total_functions += 1

    avg_complexity = total_complexity / total_functions if total_functions > 0 else 0
    results.sort(key=lambda x: x["complexity"], reverse=True)
    high_complexity = [r for r in results if r["complexity"] >= 10]

    return {
        "total_functions": total_functions,
        "average_complexity": round(avg_complexity, 2),
        "high_complexity_functions": high_complexity[:20],
        "high_complexity_count": len(high_complexity),
        "most_complex": results[:10],
    }


# ─── Tool: Analyze code quality indicators ───

def analyze_code_quality(repo_path: str) -> dict:
    """Analyze various code quality indicators across all Python files."""
    total_lines = 0
    blank_lines = 0
    comment_lines = 0
    code_lines = 0
    todo_count = 0
    hack_count = 0
    fixme_count = 0
    files_analyzed = 0

    for filepath, f, root in _walk_python_files(repo_path):
        content = _safe_read(filepath)
        files_analyzed += 1

        for line in content.splitlines():
            stripped = line.strip()
            total_lines += 1
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1

            lower = stripped.lower()
            if stripped.startswith("#"):
                if "todo" in lower:
                    todo_count += 1
                if "fixme" in lower:
                    fixme_count += 1
                if "hack" in lower:
                    hack_count += 1

    comment_ratio = comment_lines / code_lines if code_lines > 0 else 0

    return {
        "files_analyzed": files_analyzed,
        "total_lines": total_lines,
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "blank_lines": blank_lines,
        "comment_ratio": round(comment_ratio, 3),
        "todo_count": todo_count,
        "fixme_count": fixme_count,
        "hack_count": hack_count,
        "tech_debt_markers": todo_count + fixme_count + hack_count,
    }


# ─── Tool: Analyze documentation ───

def analyze_documentation(repo_path: str) -> dict:
    """Analyze documentation quality indicators."""
    docstrings_found = 0
    functions_without_docs = 0
    classes_documented = 0
    classes_total = 0

    has_docs_dir = os.path.isdir(os.path.join(repo_path, "docs"))
    has_contributing = os.path.exists(os.path.join(repo_path, "CONTRIBUTING.md"))
    has_license = (
        os.path.exists(os.path.join(repo_path, "LICENSE"))
        or os.path.exists(os.path.join(repo_path, "LICENSE.md"))
        or os.path.exists(os.path.join(repo_path, "LICENSE.txt"))
    )
    has_changelog = (
        os.path.exists(os.path.join(repo_path, "CHANGELOG.md"))
        or os.path.exists(os.path.join(repo_path, "CHANGES.md"))
    )

    for filepath, f, root in _walk_python_files(repo_path, skip_tests=True):
        content = _safe_read(filepath)
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node):
                    docstrings_found += 1
                else:
                    functions_without_docs += 1
            if isinstance(node, ast.ClassDef):
                classes_total += 1
                if ast.get_docstring(node):
                    classes_documented += 1

    total_funcs = docstrings_found + functions_without_docs
    docstring_ratio = docstrings_found / total_funcs if total_funcs > 0 else 0
    class_doc_ratio = classes_documented / classes_total if classes_total > 0 else 0

    return {
        "docstrings_found": docstrings_found,
        "functions_without_docs": functions_without_docs,
        "docstring_ratio": round(docstring_ratio, 3),
        "classes_documented": classes_documented,
        "classes_total": classes_total,
        "class_doc_ratio": round(class_doc_ratio, 3),
        "has_docs_dir": has_docs_dir,
        "has_contributing": has_contributing,
        "has_license": has_license,
        "has_changelog": has_changelog,
    }


# ─── Tool: Analyze git history ───

def analyze_git_history(repo_path: str) -> dict:
    """Analyze git history for maintenance indicators."""

    def _run_git(args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    total_commits_str = _run_git(["rev-list", "--count", "HEAD"])
    total_commits = int(total_commits_str) if total_commits_str.isdigit() else 0

    contributors = _run_git(["shortlog", "-sn", "HEAD"])
    contributor_list = [line.strip() for line in contributors.splitlines() if line.strip()]
    contributor_count = len(contributor_list)

    last_commit_date = _run_git(["log", "-1", "--format=%ci"])

    first_commit_hash = _run_git(["rev-list", "--max-parents=0", "HEAD"]).split("\n")[0]
    first_commit_date = ""
    if first_commit_hash:
        first_commit_date = _run_git(["log", "-1", "--format=%ci", first_commit_hash])

    recent_commits = _run_git(["log", "--since=30 days ago", "--oneline"])
    recent_commit_count = len([l for l in recent_commits.splitlines() if l.strip()]) if recent_commits else 0

    tags = _run_git(["tag", "--list"])
    tag_count = len([t for t in tags.splitlines() if t.strip()]) if tags else 0

    return {
        "total_commits": total_commits,
        "contributor_count": contributor_count,
        "top_contributors": contributor_list[:5],
        "recent_commit_count_30d": recent_commit_count,
        "tag_count": tag_count,
        "last_commit_date": last_commit_date,
        "first_commit_date": first_commit_date,
    }


# ─── Tool: Analyze security indicators ───

def analyze_security(repo_path: str) -> dict:
    """Analyze basic security indicators in Python code."""
    issues = []
    files_checked = 0

    for filepath, f, root in _walk_python_files(repo_path, skip_tests=True):
        content = _safe_read(filepath)
        files_checked += 1
        rel_path = os.path.relpath(filepath, repo_path)

        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped == "except:" or stripped.startswith("except: "):
                issues.append({"file": rel_path, "line": i, "type": "bare_except", "detail": "Bare except clause catches all exceptions including SystemExit"})
            if "eval(" in stripped and not stripped.startswith("#"):
                issues.append({"file": rel_path, "line": i, "type": "eval", "detail": "Use of eval() is dangerous"})
            if "exec(" in stripped and not stripped.startswith("#"):
                issues.append({"file": rel_path, "line": i, "type": "exec", "detail": "Use of exec() is dangerous"})
            if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', stripped, re.IGNORECASE):
                issues.append({"file": rel_path, "line": i, "type": "hardcoded_secret", "detail": "Possible hardcoded secret"})
            if "shell=True" in stripped:
                issues.append({"file": rel_path, "line": i, "type": "shell_injection", "detail": "shell=True can lead to injection"})

    return {
        "files_checked": files_checked,
        "issues_found": issues[:20],
        "issue_count": len(issues),
    }


# ─── Tool registry ───

TOOL_REGISTRY = {
    "read_readme": read_readme,
    "analyze_structure": analyze_structure,
    "analyze_dependencies": analyze_dependencies,
    "analyze_tests": analyze_tests,
    "run_tests": run_tests,
    "analyze_complexity": analyze_complexity,
    "analyze_code_quality": analyze_code_quality,
    "analyze_documentation": analyze_documentation,
    "analyze_git_history": analyze_git_history,
    "analyze_security": analyze_security,
}

TOOL_DESCRIPTIONS = {
    "read_readme": "Read the README file from a repository. Returns content and metadata.",
    "analyze_structure": "Analyze the directory structure, file types, and project configuration.",
    "analyze_dependencies": "Analyze dependencies from requirements.txt, pyproject.toml, package.json, or Cargo.toml.",
    "analyze_tests": "Count test files, test functions, and check for test configuration. Returns test-to-source ratio.",
    "run_tests": "Run the test suite using pytest. Returns pass/fail counts.",
    "analyze_complexity": "Analyze cyclomatic complexity of all Python functions via AST.",
    "analyze_code_quality": "Analyze code quality: comments, TODOs, FIXMEs, HACK markers, tech debt.",
    "analyze_documentation": "Analyze documentation: docstrings, CONTRIBUTING, LICENSE, CHANGELOG.",
    "analyze_git_history": "Analyze git history: commit count, contributors, recent activity, tags.",
    "analyze_security": "Analyze basic security indicators: bare except, eval, exec, hardcoded secrets, shell=True.",
}
