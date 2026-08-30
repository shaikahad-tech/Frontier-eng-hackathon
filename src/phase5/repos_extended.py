"""Phase 5 — Additional synthetic repo generators (repos 16-25)

Expands the benchmark from 15 to 25 repositories.
"""
import os
from src.phase5.repos import _write_file, _git_init


def generate_repo_16(base_path: str) -> str:
    """Minimal viable project."""
    repo_path = os.path.join(base_path, "repo_16")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# MiniApp\n\nA minimal app.\n")
    _write_file(os.path.join(repo_path, "app.py"), "def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()\n")
    _write_file(os.path.join(repo_path, "test_app.py"), "from app import main\n\ndef test_main():\n    assert main is not None\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'miniapp'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_17(base_path: str) -> str:
    """Over-engineered with unnecessary abstraction layers."""
    repo_path = os.path.join(base_path, "repo_17")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# AbstractFramework\n\nAn enterprise framework.\n")
    _write_file(os.path.join(repo_path, "src/abstract/base.py"), '"""Abstract base factory manager."""\nfrom abc import ABC, abstractmethod\n\nclass IFactoryManager(ABC):\n    @abstractmethod\n    def create(self): pass\n\nclass AbstractFactoryManagerBase(IFactoryManager):\n    def create(self): return self._do_create()\n    def _do_create(self): raise NotImplementedError\n\nclass ConcreteFactoryManager(AbstractFactoryManagerBase):\n    def _do_create(self): return object()\n')
    _write_file(os.path.join(repo_path, "src/abstract/handler.py"), '"""Chain of responsibility handler."""\nclass Handler:\n    def __init__(self): self._next = None\n    def set_next(self, h): self._next = h; return h\n    def handle(self, req):\n        if self._next: return self._next.handle(req)\n        return None\n')
    _write_file(os.path.join(repo_path, "tests/test_abstract.py"), 'from src.abstract.base import ConcreteFactoryManager\nfrom src.abstract.handler import Handler\n\ndef test_create():\n    m = ConcreteFactoryManager()\n    assert m.create() is not None\n\ndef test_handler():\n    h = Handler()\n    assert h.handle("test") is None\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'abstractframework'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_18(base_path: str) -> str:
    """Perfect tests but no source code quality enforcement."""
    repo_path = os.path.join(base_path, "repo_18")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# CalcLib\n\nA calculator library.\n")
    _write_file(os.path.join(repo_path, "src/calc.py"), '"""Calculator library."""\ndef add(a,b):\n    return a+b\ndef subtract(a,b):\n    return a-b\ndef multiply(a,b):\n    return a*b\ndef divide(a,b):\n    if b==0: raise ValueError("div by zero")\n    return a/b\n')
    _write_file(os.path.join(repo_path, "tests/test_calc.py"), 'import pytest\nfrom src.calc import add, subtract, multiply, divide\n\ndef test_add():\n    assert add(2,3)==5\n    assert add(-1,1)==0\n\ndef test_subtract():\n    assert subtract(5,3)==2\n\ndef test_multiply():\n    assert multiply(2,3)==6\n\ndef test_divide():\n    assert divide(6,2)==3\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        divide(1,0)\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'calclib'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_19(base_path: str) -> str:
    """Monorepo with mixed quality across packages."""
    repo_path = os.path.join(base_path, "repo_19")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# MonoRepo\n\nA monorepo with multiple packages.\n")
    _write_file(os.path.join(repo_path, "packages/pkg_a/__init__.py"), '"""Core utilities."""\n')
    _write_file(os.path.join(repo_path, "packages/pkg_a/utils.py"), 'def clamp(val, lo, hi):\n    """Clamp a value between bounds."""\n    return max(lo, min(val, hi))\n\ndef safe_div(a, b):\n    """Safely divide."""\n    if b == 0: return 0\n    return a / b\n')
    _write_file(os.path.join(repo_path, "packages/pkg_a/test_utils.py"), 'from packages.pkg_a.utils import clamp, safe_div\n\ndef test_clamp():\n    assert clamp(5, 0, 10) == 5\n\ndef test_safe_div():\n    assert safe_div(10, 2) == 5\n    assert safe_div(10, 0) == 0\n')
    _write_file(os.path.join(repo_path, "packages/pkg_b/__init__.py"), '"""API layer."""\n')
    _write_file(os.path.join(repo_path, "packages/pkg_b/api.py"), 'import subprocess\nclass API:\n    def run(self,cmd):\n        return subprocess.check_output(cmd,shell=True)\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'monorepo'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_20(base_path: str) -> str:
    """CLI tool with excellent UX but poor internal quality."""
    repo_path = os.path.join(base_path, "repo_20")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# CLIPro\n\nA beautiful CLI tool for managing projects.\n\n## Installation\n\n```bash\npip install clipro\n```\n\n## Usage\n\n```bash\nclipro init my-project\nclipro build\nclipro deploy\n```\n\n## License\n\nMIT\n")
    _write_file(os.path.join(repo_path, "src/cli.py"), 'import sys,os\nclass CLI:\n    def __init__(self): self.cmds={}\n    def cmd(self,n):\n        def d(f): self.cmds[n]=f; return f\n        return d\n    def run(self,a):\n        if not a: return\n        c=a[0]\n        if c in self.cmds: self.cmds[c](a[1:])\nc=CLI()\n@c.cmd("init")\ndef _init(a): os.makedirs(a[0] if a else "new",exist_ok=True)\n')
    _write_file(os.path.join(repo_path, "tests/test_cli.py"), "from src.cli import CLI\n\ndef test_cli():\n    c = CLI()\n    assert c is not None\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'clipro'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_21(base_path: str) -> str:
    """Library with type hints and docstrings but no tests."""
    repo_path = os.path.join(base_path, "repo_21")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# TypedLib\n\nA typed utility library.\n")
    _write_file(os.path.join(repo_path, "src/typedlib.py"), '"""Typed utility library."""\nfrom typing import Optional, Union\n\ndef parse_int(value: str) -> Optional[int]:\n    """Parse a string to an integer."""\n    try:\n        return int(value)\n    except ValueError:\n        return None\n\ndef format_string(value: Union[str, int], width: int = 10) -> str:\n    """Format a value to a fixed-width string."""\n    return str(value).rjust(width)\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'typedlib'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_22(base_path: str) -> str:
    """Microservice with Docker but no tests or CI."""
    repo_path = os.path.join(base_path, "repo_22")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# MicroService\n\nA containerized microservice.\n")
    _write_file(os.path.join(repo_path, "src/service.py"), '"""Simple microservice."""\nclass Service:\n    def __init__(self):\n        self.routes = {}\n    def handle(self, path, method="GET"):\n        handler = self.routes.get(f"{method}:{path}")\n        if handler:\n            return handler()\n        return {"error": "not found", "code": 404}\n')
    _write_file(os.path.join(repo_path, "Dockerfile"), "FROM python:3.12-slim\nWORKDIR /app\nCOPY . /app\nEXPOSE 8080\nCMD [\"python\", \"-m\", \"src.service\"]\n")
    _write_file(os.path.join(repo_path, "requirements.txt"), "flask>=3.0\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'microservice'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_23(base_path: str) -> str:
    """Well-tested library with committed API key."""
    repo_path = os.path.join(base_path, "repo_23")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# DataLib\n\nA data processing library.\n")
    _write_file(os.path.join(repo_path, "src/datalib.py"), '"""Data processing library."""\ndef transform(data: list) -> list:\n    """Transform data by applying normalization."""\n    if not data: return []\n    max_val = max(abs(x) for x in data) or 1\n    return [x / max_val for x in data]\n\ndef aggregate(data: list, key: str = "value") -> dict:\n    """Aggregate data by computing statistics."""\n    if not data: return {"count": 0, "sum": 0, "avg": 0}\n    return {"count": len(data), "sum": sum(data), "avg": sum(data) / len(data)}\n')
    _write_file(os.path.join(repo_path, "tests/test_datalib.py"), 'import pytest\nfrom src.datalib import transform, aggregate\n\ndef test_transform_empty():\n    assert transform([]) == []\n\ndef test_transform_basic():\n    result = transform([1, 2, 3])\n    assert result[0] == 1.0\n\ndef test_aggregate_empty():\n    result = aggregate([])\n    assert result["count"] == 0\n\ndef test_aggregate_basic():\n    result = aggregate([1, 2, 3])\n    assert result["count"] == 3\n    assert result["sum"] == 6\n')
    _write_file(os.path.join(repo_path, ".env"), "API_KEY=sk-proj-1234567890abcdefghijklmnopqrstuvwxyz\nSECRET_KEY=a1b2c3d4e5f6g7h8i9j0\n")
    _write_file(os.path.join(repo_path, "config/settings.py"), "API_KEY = 'sk-proj-1234567890abcdefghijklmnopqrstuvwxyz'\nSECRET = 'a1b2c3d4e5f6g7h8i9j0'\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'datalib'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_24(base_path: str) -> str:
    """Empty repository with only README and license."""
    repo_path = os.path.join(base_path, "repo_24")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# Placeholder\n\nThis is a placeholder repository.\n")
    _write_file(os.path.join(repo_path, "LICENSE"), "MIT License\n\nCopyright (c) 2024\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_25(base_path: str) -> str:
    """Production-grade library with CI, coverage, linting, and security scanning."""
    repo_path = os.path.join(base_path, "repo_25")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# ProLib\n\nA production-grade utility library with comprehensive testing, CI/CD,\nlinting, coverage tracking, and security scanning.\n\n## Installation\n\n```bash\npip install prolib\n```\n\n## Testing\n\n```bash\npytest --cov=prolib --cov-report=html\n```\n\n## License\n\nMIT\n")
    _write_file(os.path.join(repo_path, "src/prolib.py"), '"""Production-grade utility library."""\nfrom typing import Any\nfrom dataclasses import dataclass, field\nfrom collections.abc import Callable\n\n@dataclass\nclass Pipeline:\n    """A data processing pipeline."""\n    _steps: list[Callable] = field(default_factory=list)\n    def add(self, step: Callable[[Any], Any]) -> "Pipeline":\n        self._steps.append(step); return self\n    def run(self, data: Any) -> Any:\n        result = data\n        for step in self._steps: result = step(result)\n        return result\n\ndef validate(data: list) -> bool:\n    """Validate that data is a non-empty list of numbers."""\n    if not isinstance(data, list) or len(data) == 0: return False\n    return all(isinstance(x, (int, float)) for x in data)\n\ndef normalize(data: list) -> list:\n    """Normalize data to 0-1 range."""\n    if not data: return []\n    max_val = max(abs(x) for x in data) or 1\n    return [x / max_val for x in data]\n')
    _write_file(os.path.join(repo_path, "tests/test_prolib.py"), 'import pytest\nfrom src.prolib import Pipeline, validate, normalize\n\ndef test_validate_empty():\n    assert validate([]) is False\n\ndef test_validate_valid():\n    assert validate([1, 2, 3]) is True\n\ndef test_normalize_empty():\n    assert normalize([]) == []\n\ndef test_normalize_basic():\n    result = normalize([1, 2, 4])\n    assert result[2] == 1.0\n\ndef test_pipeline_empty():\n    p = Pipeline()\n    assert p.run([1, 2, 3]) == [1, 2, 3]\n\ndef test_pipeline_with_steps():\n    p = Pipeline().add(normalize)\n    result = p.run([1, 2, 4])\n    assert result[2] == 1.0\n')
    _write_file(os.path.join(repo_path, ".github/workflows/ci.yml"), "name: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pytest --cov=prolib --cov-fail-under=90\n      - run: bandit -r src/\n")
    _write_file(os.path.join(repo_path, "ruff.toml"), 'line-length = 100\n[lint]\nselect = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'prolib'\nversion = '1.0.0'\n[project.optional-dependencies]\ndev = ['pytest', 'pytest-cov', 'ruff', 'bandit']\n[tool.pytest.ini_options]\ntestpaths = ['tests']\n")
    _git_init(repo_path)
    return repo_path
