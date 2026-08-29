"""Phase 5 — Synthetic repository generators and registry

Generates 15 synthetic repositories (12 standard + 3 adversarial) for benchmarking.
Ground truth manifests are in ground_truth.py.
Additional generators (repos 06-15) are in repos_adversarial.py.

Repos generated here (01-05, 07, 12, 13):
  01: Excellent across every dimension
  02: Excellent documentation but terrible code
  03: Excellent code but almost no documentation
  04: Many tests but tests mostly meaningless
  05: Few tests but very strong tests
  07: Low complexity but severe security issues
  12: Surface-perfect repository with hidden severe problems
  13: Adversarial: Fake quality (enormous README, meaningless tests, fake CI)
"""
import os
import json
from src.phase5.ground_truth import GROUND_TRUTH, SCORING_RUBRICS


def _write_file(path: str, content: str):
    """Write a file, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _git_init(repo_path: str, commits: list[dict] = None):
    """Initialize a git repo and optionally create commits."""
    import subprocess
    try:
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, timeout=5)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)
        if commits:
            for commit in commits:
                for fname, content in commit.get("files", {}).items():
                    _write_file(os.path.join(repo_path, fname), content)
                subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True)
                subprocess.run(["git", "commit", "-m", commit.get("message", "update")],
                             cwd=repo_path, capture_output=True, timeout=5)
        else:
            subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path,
                         capture_output=True, timeout=5)
    except Exception:
        pass


def generate_repo_01(base_path: str) -> str:
    """Excellent across every dimension."""
    repo_path = os.path.join(base_path, "repo_01")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# DataProcessor

A high-performance data processing library with clean architecture, comprehensive tests,
and production-ready features.

## Installation

```bash
pip install dataprocessor
```

## Usage

```python
from dataprocessor import Pipeline

pipeline = Pipeline()
result = pipeline.process(data)
```

## Testing

```bash
pytest --cov=dataprocessor
```

## License

MIT License

## Contributing

See CONTRIBUTING.md for guidelines.
""")
    _write_file(os.path.join(repo_path, "pyproject.toml"), """[project]
name = "dataprocessor"
version = "1.2.0"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]
""")
    _write_file(os.path.join(repo_path, ".gitignore"), "*.pyc\n__pycache__/\n.env\n")
    _write_file(os.path.join(repo_path, "src/dataprocessor/__init__.py"),
                '"""DataProcessor package."""\n__version__ = "1.2.0"\n')
    _write_file(os.path.join(repo_path, "src/dataprocessor/pipeline.py"), '''"""Pipeline module for data processing."""
import logging

logger = logging.getLogger(__name__)


class Pipeline:
    """Data processing pipeline with validation and error handling."""

    def __init__(self, validators=None):
        self.validators = validators or []
        self._processed = 0

    def process(self, data):
        """Process data through the pipeline."""
        if not data:
            raise ValueError("Data cannot be empty")
        for validator in self.validators:
            data = validator(data)
        self._processed += 1
        logger.info(f"Processed {self._processed} items")
        return data

    def reset(self):
        """Reset pipeline state."""
        self._processed = 0
''')
    _write_file(os.path.join(repo_path, "tests/test_pipeline.py"), '''"""Comprehensive tests for Pipeline."""
import pytest
from dataprocessor.pipeline import Pipeline


def test_pipeline_basic():
    p = Pipeline()
    result = p.process([1, 2, 3])
    assert result == [1, 2, 3]


def test_pipeline_empty_data():
    p = Pipeline()
    with pytest.raises(ValueError):
        p.process([])


def test_pipeline_with_validator():
    def double(x):
        return [i * 2 for i in x]
    p = Pipeline(validators=[double])
    assert p.process([1, 2]) == [2, 4]


def test_pipeline_reset():
    p = Pipeline()
    p.process([1])
    p.reset()
    assert p._processed == 0


def test_pipeline_multiple_validators():
    def add_one(x):
        return [i + 1 for i in x]
    def multiply_two(x):
        return [i * 2 for i in x]
    p = Pipeline(validators=[add_one, multiply_two])
    assert p.process([1, 2]) == [4, 6]
''')
    _write_file(os.path.join(repo_path, ".github/workflows/ci.yml"), """name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install pytest pytest-cov
      - run: pytest --cov=src
""")
    _write_file(os.path.join(repo_path, "Dockerfile"), """FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY src/ src/
USER nonroot
HEALTHCHECK CMD python -c "import dataprocessor"
""")
    _write_file(os.path.join(repo_path, "CONTRIBUTING.md"), "# Contributing\n\nContributions welcome!\n")
    _write_file(os.path.join(repo_path, "LICENSE"), "MIT License\n\nCopyright (c) 2024\n")
    _write_file(os.path.join(repo_path, "SECURITY.md"), "# Security Policy\n\nReport vulnerabilities to security@example.com\n")
    _git_init(repo_path, [
        {"files": {"README.md": open(os.path.join(repo_path, "README.md")).read()}, "message": "Add README"},
        {"files": {"src/dataprocessor/__init__.py": "", "src/dataprocessor/pipeline.py": "initial"}, "message": "Add core module"},
        {"files": {"tests/test_pipeline.py": "initial"}, "message": "Add tests"},
    ])
    return repo_path


def generate_repo_02(base_path: str) -> str:
    """Excellent documentation but terrible code."""
    repo_path = os.path.join(base_path, "repo_02")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# AwesomeToolkit

A comprehensive toolkit for building amazing applications with detailed documentation,
extensive examples, and beautiful API references.

## Installation

```bash
pip install awesometoolkit
```

## Usage

```python
from awesometoolkit import Builder

builder = Builder()
result = builder.build(config)
```

## Examples

### Basic Example
```python
builder = Builder()
result = builder.build({"name": "test"})
```

### Advanced Example
```python
builder = Builder(debug=True)
result = builder.build({"name": "test", "nested": {"a": 1}})
```

## API Reference

See `docs/api.md` for full API documentation.

## Testing

```bash
pytest
```

## License

MIT License

## Contributing

See CONTRIBUTING.md
""")
    _write_file(os.path.join(repo_path, "src/awesometoolkit.py"), '''import os
import subprocess

def do_stuff(data, mode, flag, x, y, z):
    if mode == 1:
        if flag:
            if x > 0:
                if y > 0:
                    if z > 0:
                        result = data
                        for i in range(100):
                            if i % 2 == 0:
                                if i % 3 == 0:
                                    result = result + str(i)
                                else:
                                    result = result + str(i * 2)
                            else:
                                if i % 5 == 0:
                                    result = result + str(i * 3)
                                else:
                                    result = result + str(i)
                        return result
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            if x < 0:
                return None
            else:
                return data
    elif mode == 2:
        # Command injection vulnerability
        cmd = "process " + data
        return subprocess.check_output(cmd, shell=True)
    else:
        return None

def parse_input(user_input):
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    return query

def hardcoded_key():
    api_key = "sk-1234567890abcdef1234567890abcdef"
    return api_key
''')
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='awesometoolkit', version='0.1')\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_03(base_path: str) -> str:
    """Excellent code but almost no documentation."""
    repo_path = os.path.join(base_path, "repo_03")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# project\n")
    _write_file(os.path.join(repo_path, "src/core.py"), '''"""Core module."""
import logging

logger = logging.getLogger(__name__)


class Manager:
    """Manages resources with proper lifecycle."""

    def __init__(self):
        self._resources = {}

    def add(self, key, value):
        if key in self._resources:
            raise KeyError(f"Key {key} already exists")
        self._resources[key] = value
        logger.debug(f"Added key {key}")

    def get(self, key):
        return self._resources.get(key)

    def remove(self, key):
        if key not in self._resources:
            raise KeyError(f"Key {key} not found")
        del self._resources[key]

    def clear(self):
        self._resources.clear()
''')
    _write_file(os.path.join(repo_path, "tests/test_core.py"), '''"""Tests for core module."""
import pytest
from src.core import Manager


def test_add_and_get():
    m = Manager()
    m.add("key1", "value1")
    assert m.get("key1") == "value1"


def test_add_duplicate():
    m = Manager()
    m.add("key1", "value1")
    with pytest.raises(KeyError):
        m.add("key1", "value2")


def test_remove():
    m = Manager()
    m.add("key1", "value1")
    m.remove("key1")
    assert m.get("key1") is None


def test_remove_missing():
    m = Manager()
    with pytest.raises(KeyError):
        m.remove("nonexistent")


def test_clear():
    m = Manager()
    m.add("a", 1)
    m.add("b", 2)
    m.clear()
    assert m.get("a") is None
    assert m.get("b") is None
''')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'core'\nversion = '0.1.0'\n")
    _write_file(os.path.join(repo_path, ".gitignore"), "*.pyc\n__pycache__/\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_04(base_path: str) -> str:
    """Many tests but tests mostly meaningless."""
    repo_path = os.path.join(base_path, "repo_04")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# UtilsLib

A utility library with various helper functions.

## Installation

```bash
pip install utilslib
```

## Usage

```python
from utilslib import helpers
helpers.do_something()
```
""")
    _write_file(os.path.join(repo_path, "src/utilslib.py"), '''"""Utility functions."""
import os


def do_something():
    return True


def process_data(data):
    return data


def transform(input_val):
    return str(input_val)


def calculate(x, y):
    return x + y
''')
    test_code = '''"""Tests for utilslib."""
from utilslib import do_something, process_data, transform, calculate


def test_01():
    assert do_something() == True


def test_02():
    assert do_something() == True


def test_03():
    assert do_something() == True
'''
    for i in range(4, 50):
        test_code += f"\ndef test_{i:02d}():\n    assert do_something() == True\n"
    _write_file(os.path.join(repo_path, "tests/test_utils.py"), test_code)
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='utilslib', version='0.1')\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_05(base_path: str) -> str:
    """Few tests but very strong tests."""
    repo_path = os.path.join(base_path, "repo_05")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# SecureStore

A secure data storage library with encryption and access control.

## Installation

```bash
pip install securestore
```

## Usage

```python
from securestore import SecureStore

store = SecureStore(key="my-secret-key")
store.set("user", {"name": "Alice"})
data = store.get("user")
```
""")
    _write_file(os.path.join(repo_path, "src/securestore.py"), '''"""Secure storage with encryption."""
import hashlib
import json
from typing import Any, Optional


class SecureStore:
    """Encrypted key-value store with access control."""

    def __init__(self, key: str):
        if not key or len(key) < 8:
            raise ValueError("Key must be at least 8 characters")
        self._key_hash = hashlib.sha256(key.encode()).hexdigest()
        self._data = {}

    def set(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("Key cannot be empty")
        self._data[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def size(self) -> int:
        return len(self._data)
''')
    _write_file(os.path.join(repo_path, "tests/test_securestore.py"), '''"""Meaningful tests for SecureStore."""
import pytest
from securestore import SecureStore


def test_store_and_retrieve():
    store = SecureStore(key="test-key-123")
    store.set("user", {"name": "Alice"})
    assert store.get("user") == {"name": "Alice"}


def test_weak_key_rejected():
    with pytest.raises(ValueError, match="at least 8 characters"):
        SecureStore(key="short")


def test_empty_key_rejected():
    with pytest.raises(ValueError):
        SecureStore(key="")


def test_delete_existing():
    store = SecureStore(key="test-key-123")
    store.set("temp", "value")
    assert store.delete("temp") is True
    assert store.get("temp") is None


def test_delete_nonexisting():
    store = SecureStore(key="test-key-123")
    assert store.delete("nonexistent") is False


def test_empty_key_not_allowed():
    store = SecureStore(key="test-key-123")
    with pytest.raises(ValueError):
        store.set("", "value")


def test_keys_and_size():
    store = SecureStore(key="test-key-123")
    store.set("a", 1)
    store.set("b", 2)
    assert set(store.keys()) == {"a", "b"}
    assert store.size() == 2
''')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'securestore'\nversion = '1.0.0'\n")
    _write_file(os.path.join(repo_path, ".gitignore"), "*.pyc\n.env\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_07(base_path: str) -> str:
    """Low complexity but severe security issues."""
    repo_path = os.path.join(base_path, "repo_07")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# ConfigManager

A simple configuration manager with environment variable support.

## Installation

```bash
pip install configmanager
```

## Usage

```python
from configmanager import ConfigManager

config = ConfigManager()
config.set("key", "value")
print(config.get("key"))
```

## Testing

```bash
pytest
```

## License

MIT
""")
    _write_file(os.path.join(repo_path, "src/configmanager.py"), '''"""Configuration manager."""
import os
import subprocess


class ConfigManager:
    """Simple config manager."""

    def __init__(self):
        self._config = {}

    def set(self, key, value):
        self._config[key] = value

    def get(self, key, default=None):
        return self._config.get(key, default)

    def load_from_env(self, prefix):
        for k, v in os.environ.items():
            if k.startswith(prefix):
                self._config[k] = v

    def execute_hook(self, hook_command):
        # Command injection vulnerability
        return subprocess.check_output(hook_command, shell=True)
''')
    _write_file(os.path.join(repo_path, "tests/test_config.py"), '''"""Tests for ConfigManager."""
import pytest
from configmanager import ConfigManager


def test_set_and_get():
    cm = ConfigManager()
    cm.set("key", "value")
    assert cm.get("key") == "value"


def test_get_default():
    cm = ConfigManager()
    assert cm.get("nonexistent", "default") == "default"


def test_set_overwrite():
    cm = ConfigManager()
    cm.set("key", "value1")
    cm.set("key", "value2")
    assert cm.get("key") == "value2"


def test_load_from_env(monkeypatch):
    monkeypatch.setenv("APP_HOST", "localhost")
    monkeypatch.setenv("APP_PORT", "8080")
    cm = ConfigManager()
    cm.load_from_env("APP_")
    assert cm.get("APP_HOST") == "localhost"
    assert cm.get("APP_PORT") == "8080"
''')
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='configmanager', version='0.1')\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_12(base_path: str) -> str:
    """Surface-perfect repository with hidden severe problems."""
    repo_path = os.path.join(base_path, "repo_12")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), """# CloudScale

A production-grade, enterprise-ready cloud scaling platform with auto-scaling,
load balancing, health monitoring, and zero-downtime deployments.

## Features

- Auto-scaling based on CPU/memory metrics
- Zero-downtime deployments with rolling updates
- Health monitoring with circuit breakers
- Multi-region failover
- Real-time dashboards

## Installation

```bash
pip install cloudscale
```

## Quick Start

```python
from cloudscale import Scaler

scaler = Scaler(region="us-east-1")
scaler.deploy(config="production.yaml")
```

## Testing

```bash
pytest --cov=cloudscale
```

## CI/CD

Full CI/CD pipeline with automated testing, security scanning, and deployment.

## License

MIT License
""")
    _write_file(os.path.join(repo_path, ".env"), "AWS_SECRET_KEY=AKIA1234567890ABCDEF\nDATABASE_PASSWORD=super_secret_123\n")
    _write_file(os.path.join(repo_path, ".github/workflows/security.yml"), """name: Security Scan
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: echo "Security scan complete"
""")
    _write_file(os.path.join(repo_path, "tests/test_cloudscale.py"), '''"""Tests for CloudScale."""
def test scaler_exists():
    assert True

def test_deployment():
    assert True

def test_scaling():
    assert True
''')
    _write_file(os.path.join(repo_path, "src/cloudscale.py"), '''"""CloudScale - placeholder."""
import os

API_KEY = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"

def deploy(config):
    return True

def scale(metrics):
    return True
''')
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='cloudscale', version='1.0.0')\n")
    _write_file(os.path.join(repo_path, "Dockerfile"), "FROM python:3.12\nCOPY . .\nCMD python -c 'pass'\n")
    commits = [{"files": {f"file_{i}.txt": f"content {i}"}, "message": f"update {i}"} for i in range(20)]
    _git_init(repo_path, commits)
    return repo_path


def generate_repo_13(base_path: str) -> str:
    """Adversarial: Fake quality."""
    repo_path = os.path.join(base_path, "repo_13")
    os.makedirs(repo_path, exist_ok=True)
    readme = "# SuperFramework\n\nA framework.\n\n"
    for i in range(200):
        readme += f"## Section {i}\n\nLorem ipsum dolor sit amet {i}. " * 20 + "\n\n"
    _write_file(os.path.join(repo_path, "README.md"), readme)
    test_code = '''"""Tests."""
def test_01(): assert True
'''
    for i in range(2, 100):
        test_code += f"def test_{i:02d}(): assert True\n"
    _write_file(os.path.join(repo_path, "tests/test_all.py"), test_code)
    _write_file(os.path.join(repo_path, ".github/workflows/test.yml"), """name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "All tests passed"
""")
    _write_file(os.path.join(repo_path, "src/framework.py"), '''# This is a framework
# It does many things
# It is very good
# Trust me
# This function does X
# X is important
# Very important
# The best
def run():
    # This runs the framework
    # It runs very well
    # Excellent
    pass
''')
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='superframework', version='1.0.0')\n")
    _git_init(repo_path)
    return repo_path


# Import additional generators from repos_adversarial.py
from src.phase5.repos_adversarial import (
    generate_repo_06, generate_repo_08, generate_repo_09, generate_repo_10,
    generate_repo_11, generate_repo_14, generate_repo_15,
)


# Repository generators registry
REPO_GENERATORS = {
    "repo_01": generate_repo_01, "repo_02": generate_repo_02, "repo_03": generate_repo_03,
    "repo_04": generate_repo_04, "repo_05": generate_repo_05, "repo_06": generate_repo_06,
    "repo_07": generate_repo_07, "repo_08": generate_repo_08, "repo_09": generate_repo_09,
    "repo_10": generate_repo_10, "repo_11": generate_repo_11, "repo_12": generate_repo_12,
    "repo_13": generate_repo_13, "repo_14": generate_repo_14, "repo_15": generate_repo_15,
}


def generate_all_repos(base_path: str) -> dict[str, str]:
    """Generate all synthetic repositories.

    Returns mapping of repo_name -> repo_path.
    """
    repos = {}
    for repo_name, generator in REPO_GENERATORS.items():
        repo_path = generator(base_path)
        repos[repo_name] = repo_path

        # Write ground truth manifest INTO the repo (for reproducibility)
        gt = GROUND_TRUTH[repo_name]
        manifest_path = os.path.join(repo_path, ".ground_truth.json")
        with open(manifest_path, "w") as f:
            json.dump(gt, f, indent=2)

    return repos
