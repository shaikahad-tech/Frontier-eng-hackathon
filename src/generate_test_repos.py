"""
Generate 12 synthetic test repositories with known quality characteristics.

Each repo is intentionally crafted to have specific quality traits so we have
ground truth to evaluate against:

- platinum_repo: Excellent quality (tests, docs, low complexity, active)
- good_with_tests: Good quality, strong test suite
- well_documented: Good quality, excellent docstrings
- no_tests: Decent code but zero tests
- high_complexity: Code works but is overly complex
- tech_debt_heavy: Lots of TODOs, FIXMEs, hacks
- no_readme: Missing README entirely
- single_author: Single contributor, low activity
- minimal_project: Bare minimum, almost empty
- dependency_heavy: Too many dependencies
- mixed_quality: Some good, some bad — the challenging case
- broken_tests: Tests exist but are deliberately broken

Each repo gets initialized as a git repo so git history analysis works.
"""

import os
import json
import subprocess
import textwrap
import shutil

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_repos")


def _git_init(path: str, commits: int = 5, author: str = "Test Author"):
    """Initialize a git repo and make N commits."""
    os.makedirs(path, exist_ok=True)

    env = {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": f"{author.lower().replace(' ', '.')}@test.com",
        "GIT_COMMITTER_NAME": author,
        "GIT_COMMITTER_EMAIL": f"{author.lower().replace(' ', '.')}@test.com",
        "HOME": "/tmp",
    }

    subprocess.run(["git", "init"], cwd=path, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", author], cwd=path, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.email", f"{author.lower().replace(' ', '.')}@test.com"], cwd=path, capture_output=True, env=env)

    for i in range(commits):
        marker = os.path.join(path, f".commit_{i}")
        with open(marker, "w") as f:
            f.write(f"Commit {i}\n")
        subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, env=env)
        subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=path, capture_output=True, env=env)
        if i < 3:
            subprocess.run(["git", "tag", f"v0.{i}.0"], cwd=path, capture_output=True, env=env)


def _write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(textwrap.dedent(content))


def gen_platinum_repo():
    """Excellent quality: tests, docs, low complexity, active maintenance."""
    path = os.path.join(BASE_DIR, "platinum_repo")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Platinum Calculator

    A clean, well-tested Python library for mathematical operations.

    ## Features
    - Basic arithmetic (add, subtract, multiply, divide)
    - Advanced operations (power, root, factorial)
    - Full test suite with 95%+ coverage
    - Comprehensive documentation

    ## Installation
    ```bash
    pip install -e .
    ```

    ## Usage
    ```python
    from calculator import Calculator
    calc = Calculator()
    result = calc.add(2, 3)  # Returns 5
    ```

    ## Testing
    ```bash
    pytest
    ```
    """)

    _write_file(f"{path}/setup.py", """
    from setuptools import setup, find_packages
    setup(name="calculator", version="1.0.0", packages=find_packages())
    """)

    _write_file(f"{path}/calculator/__init__.py", '"""Calculator library."""\nfrom .core import Calculator\n')
    _write_file(f"{path}/calculator/core.py", '''
    """Core calculator operations."""

    class Calculator:
        """Provides basic and advanced mathematical operations."""

        def add(self, a: float, b: float) -> float:
            """Add two numbers and return the result."""
            return a + b

        def subtract(self, a: float, b: float) -> float:
            """Subtract b from a."""
            return a - b

        def multiply(self, a: float, b: float) -> float:
            """Multiply two numbers."""
            return a * b

        def divide(self, a: float, b: float) -> float:
            """Divide a by b. Raises ZeroDivisionError if b is zero."""
            if b == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return a / b

        def power(self, base: float, exp: float) -> float:
            """Raise base to the power of exp."""
            return base ** exp

        def factorial(self, n: int) -> int:
            """Calculate the factorial of n. Raises ValueError if n < 0."""
            if n < 0:
                raise ValueError("Factorial not defined for negative numbers")
            if n <= 1:
                return 1
            return n * self.factorial(n - 1)
    ''')

    _write_file(f"{path}/tests/test_core.py", '''
    """Tests for the Calculator class."""
    import pytest
    from calculator.core import Calculator

    @pytest.fixture
    def calc():
        return Calculator()

    def test_add(calc):
        assert calc.add(2, 3) == 5
        assert calc.add(-1, 1) == 0

    def test_subtract(calc):
        assert calc.subtract(5, 3) == 2
        assert calc.subtract(0, 0) == 0

    def test_multiply(calc):
        assert calc.multiply(3, 4) == 12
        assert calc.multiply(-2, 3) == -6

    def test_divide(calc):
        assert calc.divide(10, 2) == 5.0
        assert calc.divide(7, 2) == 3.5

    def test_divide_by_zero(calc):
        with pytest.raises(ZeroDivisionError):
            calc.divide(1, 0)

    def test_power(calc):
        assert calc.power(2, 3) == 8
        assert calc.power(5, 0) == 1

    def test_factorial(calc):
        assert calc.factorial(0) == 1
        assert calc.factorial(5) == 120

    def test_factorial_negative(calc):
        with pytest.raises(ValueError):
            calc.factorial(-1)
    ''')

    _write_file(f"{path}/LICENSE", "MIT License\n\nCopyright (c) 2024\n")
    _write_file(f"{path}/CONTRIBUTING.md", "# Contributing\n\nContributions welcome!\n")
    _write_file(f"{path}/CHANGELOG.md", "# Changelog\n\n## v1.0.0\n- Initial release\n")
    _write_file(f"{path}/Dockerfile", "FROM python:3.12-slim\nCOPY . /app\nWORKDIR /app\nRUN pip install -e .\n")

    _git_init(path, commits=20, author="Alice Engineer")
    return path


def gen_good_with_tests():
    """Good quality with strong test suite."""
    path = os.path.join(BASE_DIR, "good_with_tests")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # String Utils

    A utility library for string manipulation.

    ## Usage
    ```python
    from strutils import slugify, truncate
    ```
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="strutils", version="0.5.0", packages=["strutils"])\n')
    _write_file(f"{path}/strutils/__init__.py", '"""String utilities."""\nfrom .ops import slugify, truncate, camel_to_snake\n')
    _write_file(f"{path}/strutils/ops.py", '''
    """String operation utilities."""
    import re

    def slugify(text: str) -> str:
        """Convert text to a URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    def truncate(text: str, length: int = 50, suffix: str = "...") -> str:
        """Truncate text to a given length."""
        if len(text) <= length:
            return text
        return text[:length - len(suffix)] + suffix

    def camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\\1_\\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", s1).lower()
    ''')

    _write_file(f"{path}/tests/test_ops.py", '''
    """Tests for string operations."""
    import pytest
    from strutils.ops import slugify, truncate, camel_to_snake

    def test_slugify_basic():
        assert slugify("Hello World") == "hello-world"

    def test_slugify_special_chars():
        assert slugify("Hello! World?") == "hello-world"

    def test_slugify_empty():
        assert slugify("") == ""

    def test_truncate_short():
        assert truncate("Hi", 10) == "Hi"

    def test_truncate_exact():
        assert truncate("Hello", 5) == "Hello"

    def test_truncate_long():
        result = truncate("Hello World", 8)
        assert result.endswith("...")

    def test_camel_to_snake():
        assert camel_to_snake("camelCase") == "camel_case"

    def test_camel_to_snake_complex():
        assert camel_to_snake("getHTTPResponseCode") == "get_http_response_code"
    ''')

    _write_file(f"{path}/LICENSE", "Apache 2.0\n")

    _git_init(path, commits=12, author="Bob Developer")
    return path


def gen_well_documented():
    """Excellent docstrings but moderate tests."""
    path = os.path.join(BASE_DIR, "well_documented")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Data Validator

    Validate data structures against schemas.

    ## Installation
    ```bash
    pip install -e .
    ```
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="datavalidator", version="1.2.0", packages=["datavalidator"])\n')
    _write_file(f"{path}/datavalidator/__init__.py", '"""Data validation library."""\nfrom .validator import Validator, ValidationError\n')
    _write_file(f"{path}/datavalidator/validator.py", '''
    """Data validation against schemas."""
    from typing import Any

    class ValidationError(Exception):
        """Raised when data validation fails."""

        def __init__(self, field: str, message: str):
            """Initialize with field name and error message."""
            self.field = field
            self.message = message
            super().__init__(f"{field}: {message}")

    class Validator:
        """Validates data against a schema."""

        def __init__(self, schema: dict):
            """Initialize with a schema dictionary.

            Args:
                schema: A dictionary mapping field names to type validators.
            """
            self.schema = schema

        def validate(self, data: dict) -> bool:
            """Validate data against the schema.

            Args:
                data: The data dictionary to validate.

            Returns:
                True if valid.

            Raises:
                ValidationError: If validation fails.
            """
            for field, expected_type in self.schema.items():
                if field not in data:
                    raise ValidationError(field, "Missing required field")
                if not isinstance(data[field], expected_type):
                    raise ValidationError(field, f"Expected {expected_type.__name__}")
            return True

        def validate_safe(self, data: dict) -> tuple[bool, list[str]]:
            """Validate data and return errors instead of raising.

            Args:
                data: The data dictionary to validate.

            Returns:
                A tuple of (is_valid, list_of_errors).
            """
            errors = []
            for field, expected_type in self.schema.items():
                if field not in data:
                    errors.append(f"{field}: Missing required field")
                elif not isinstance(data[field], expected_type):
                    errors.append(f"{field}: Expected {expected_type.__name__}")
            return (len(errors) == 0, errors)
    ''')

    _write_file(f"{path}/tests/test_validator.py", '''
    from datavalidator.validator import Validator, ValidationError

    def test_valid_data():
        v = Validator({"name": str, "age": int})
        assert v.validate({"name": "Alice", "age": 30})

    def test_missing_field():
        v = Validator({"name": str})
        try:
            v.validate({})
            assert False, "Should have raised"
        except ValidationError:
            pass
    ''')

    _write_file(f"{path}/LICENSE", "MIT License\n")
    _write_file(f"{path}/CONTRIBUTING.md", "# Contributing\n")
    _write_file(f"{path}/CHANGELOG.md", "# Changelog\n## v1.2.0\n- Added validate_safe\n")

    _git_init(path, commits=8, author="Carol Writer")
    return path


def gen_no_tests():
    """Decent code but zero tests."""
    path = os.path.join(BASE_DIR, "no_tests")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Config Loader

    Load configuration from YAML and JSON files.
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="configloader", version="0.3.0", packages=["configloader"])\n')
    _write_file(f"{path}/configloader/__init__.py", '"""Config loading library."""\nfrom .loader import ConfigLoader\n')
    _write_file(f"{path}/configloader/loader.py", '''
    """Configuration loader for YAML and JSON files."""
    import json
    import os

    class ConfigLoader:
        """Loads configuration from files."""

        def __init__(self, config_dir: str = "."):
            self.config_dir = config_dir
            self._cache = {}

        def load(self, name: str) -> dict:
            """Load a config file by name."""
            if name in self._cache:
                return self._cache[name]
            for ext in [".json", ".yaml", ".yml"]:
                filepath = os.path.join(self.config_dir, name + ext)
                if os.path.exists(filepath):
                    with open(filepath) as f:
                        if ext == ".json":
                            data = json.load(f)
                        else:
                            import yaml
                            data = yaml.safe_load(f)
                    self._cache[name] = data
                    return data
            raise FileNotFoundError(f"No config file found for {name}")

        def clear_cache(self):
            self._cache.clear()
    ''')

    _write_file(f"{path}/LICENSE", "MIT License\n")

    _git_init(path, commits=4, author="Dave Coder")
    return path


def gen_high_complexity():
    """Code works but is overly complex."""
    path = os.path.join(BASE_DIR, "high_complexity")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Data Processor

    Process and transform data through multiple stages.
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="dataprocessor", version="0.1.0", packages=["dataprocessor"])\n')
    _write_file(f"{path}/dataprocessor/__init__.py", '"""Data processing library."""\nfrom .processor import DataProcessor\n')
    _write_file(f"{path}/dataprocessor/processor.py", '''
    """Data processing with multiple transformation stages."""
    from typing import Any

    class DataProcessor:
        """Process data through multiple stages."""

        def process(self, data: list, mode: str, options: dict = None) -> list:
            if options is None:
                options = {}
            result = []
            for item in data:
                if mode == "filter" and options.get("filter_key"):
                    if options["filter_key"] in item and item[options["filter_key"]] and isinstance(item[options["filter_key"]], (str, int)):
                        if isinstance(item[options["filter_key"]], str) and len(item[options["filter_key"]]) > 0:
                            if options.get("min_length") and len(item[options["filter_key"]]) >= options["min_length"]:
                                if options.get("max_length") and len(item[options["filter_key"]]) <= options["max_length"]:
                                    result.append(item)
                                elif not options.get("max_length"):
                                    result.append(item)
                            elif not options.get("min_length"):
                                result.append(item)
                elif mode == "transform" and options.get("transform_fn"):
                    try:
                        transformed = options["transform_fn"](item)
                        if transformed and isinstance(transformed, dict):
                            if options.get("validate") and options.get("validator"):
                                if options["validator"](transformed):
                                    result.append(transformed)
                            else:
                                result.append(transformed)
                    except Exception as e:
                        if options.get("ignore_errors"):
                            pass
                        else:
                            raise
                elif mode == "sort":
                    if options.get("sort_key") and options["sort_key"] in item:
                        result.append(item)
                    else:
                        result.append(item)
                else:
                    result.append(item)
            if mode == "sort" and options.get("sort_key"):
                result.sort(key=lambda x: x.get(options["sort_key"], 0) if isinstance(x, dict) else x, reverse=options.get("reverse", False))
            return result

        def aggregate(self, data: list, keys: list, agg_fn=None) -> dict:
            """Aggregate data by multiple keys."""
            if not data or not keys:
                return {}
            result = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                current = result
                for i, key in enumerate(keys):
                    if key not in item:
                        continue
                    val = item[key]
                    if i == len(keys) - 1:
                        if val not in current:
                            current[val] = []
                        if agg_fn:
                            current[val].append(item)
                        else:
                            current[val] = current.get(val, 0) + 1
                    else:
                        if val not in current:
                            current[val] = {}
                        current = current[val]
            return result
    ''')

    _write_file(f"{path}/tests/test_processor.py", '''
    from dataprocessor.processor import DataProcessor

    def test_process_basic():
        dp = DataProcessor()
        result = dp.process([1, 2, 3], "sort")
        assert result == [1, 2, 3]
    ''')

    _git_init(path, commits=3, author="Eve Hacker")
    return path


def gen_tech_debt_heavy():
    """Lots of TODOs, FIXMEs, and hacks."""
    path = os.path.join(BASE_DIR, "tech_debt_heavy")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", "# Legacy Utils\n\nOld utility functions.\n")

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="legacyutils", version="0.0.1", packages=["legacyutils"])\n')
    _write_file(f"{path}/legacyutils/__init__.py", '"""Legacy utilities."""\nfrom .utils import *\n')
    _write_file(f"{path}/legacyutils/utils.py", '''
    """Legacy utility functions."""
    # TODO: refactor this entire module
    # FIXME: the parsing logic is broken for edge cases
    # HACK: this is a temporary fix, need to properly implement later

    import os
    import json

    # TODO: add proper error handling
    def parse_config(path):
        """Parse config file. FIXME: only supports JSON."""
        # HACK: hardcoded path manipulation
        if path.endswith(".json"):
            with open(path) as f:
                return json.load(f)
        else:
            # TODO: support YAML
            raise ValueError("Only JSON supported")

    # FIXME: this function is too slow
    def find_files(directory, pattern):
        """Find files matching pattern."""
        results = []
        for root, dirs, files in os.walk(directory):
            # HACK: skip hidden dirs manually
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                # TODO: use proper regex matching
                if pattern in f:
                    results.append(os.path.join(root, f))
        return results

    # TODO: implement proper caching
    # HACK: using global dict as cache
    _cache = {}

    def cached_lookup(key, lookup_fn):
        """Lookup with caching. FIXME: cache never expires."""
        if key in _cache:
            return _cache[key]
        # TODO: add cache size limit
        result = lookup_fn(key)
        _cache[key] = result
        return result

    # FIXME: error handling is inconsistent
    # TODO: add logging
    # HACK: returning None on error instead of raising
    def safe_divide(a, b):
        """Divide a by b. TODO: handle edge cases."""
        try:
            return a / b
        except:
            # HACK: catching all exceptions
            return None
    ''')

    _git_init(path, commits=2, author="Frank Legacy")
    return path


def gen_no_readme():
    """Missing README entirely."""
    path = os.path.join(BASE_DIR, "no_readme")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name=" mystery_tool", version="0.1.0", packages=["mystery"])\n')
    _write_file(f"{path}/mystery/__init__.py", 'from .core import run\n')
    _write_file(f"{path}/mystery/core.py", """
    def run(data):
        result = []
        for item in data:
            result.append(item * 2)
        return result
    """)

    _git_init(path, commits=1, author="Anon Dev")
    return path


def gen_single_author():
    """Single contributor, low activity."""
    path = os.path.join(BASE_DIR, "single_author")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Solo Project

    A small CLI tool.
    """)

    _write_file(f"{path}/cli.py", '"""CLI entry point."""\nimport sys\n\n\ndef main():\n    print("Hello World")\n\n\nif __name__ == "__main__":\n    main()\n')

    _git_init(path, commits=2, author="Solo Dev")
    return path


def gen_minimal_project():
    """Bare minimum, almost empty."""
    path = os.path.join(BASE_DIR, "minimal_project")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/main.py", "print('hello')\n")

    _git_init(path, commits=1, author="Newbie")
    return path


def gen_dependency_heavy():
    """Too many dependencies."""
    path = os.path.join(BASE_DIR, "dependency_heavy")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", "# Mega Tool\n\nDoes everything.\n")

    _write_file(f"{path}/requirements.txt", """
    requests
    flask
    django
    pandas
    numpy
    scipy
    matplotlib
    seaborn
    scikit-learn
    tensorflow
    torch
    transformers
    openai
    anthropic
    langchain
    langgraph
    celery
    redis
    sqlalchemy
    psycopg2-binary
    pymongo
    elasticsearch
    aiohttp
    websockets
    pydantic
    fastapi
    uvicorn
    gunicorn
    pytest
    coverage
    pylint
    black
    mypy
    """)

    _write_file(f"{path}/app.py", '"""Main app."""\nimport requests\nimport flask\nimport pandas\n\napp = flask.Flask(__name__)\n\n@app.route("/")\ndef hello():\n    return "Hello"\n')

    _git_init(path, commits=3, author="Dependency Installer")
    return path


def gen_mixed_quality():
    """Some good aspects, some bad — the challenging case."""
    path = os.path.join(BASE_DIR, "mixed_quality")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Mixed Bag Utils

    A collection of utilities with varying quality.

    ## Features
    - Data processing
    - File utilities
    - String helpers

    ## Installation
    ```bash
    pip install -e .
    ```
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="mixedutils", version="0.4.0", packages=["mixedutils"])\n')
    _write_file(f"{path}/mixedutils/__init__.py", '"""Mixed utilities."""\n')
    _write_file(f"{path}/mixedutils/data.py", '''
    """Data processing utilities — well documented."""
    from typing import Any

    def deduplicate(items: list) -> list:
        """Remove duplicates while preserving order.

        Args:
            items: A list of items.

        Returns:
            A new list with duplicates removed.
        """
        seen = set()
        result = []
        for item in items:
            key = item if isinstance(item, (str, int, float)) else str(item)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def chunk(items: list, size: int) -> list:
        """Split a list into chunks of the given size."""
        if size <= 0:
            raise ValueError("Chunk size must be positive")
        return [items[i:i + size] for i in range(0, len(items), size)]
    ''')

    _write_file(f"{path}/mixedutils/files.py", '''
    """File utilities — has tech debt."""
    import os

    # TODO: add proper error handling
    # FIXME: doesn't handle symlinks
    def read_file(path):
        """Read a file. TODO: add encoding detection."""
        f = open(path)  # HACK: no context manager
        data = f.read()
        f.close()
        return data

    def list_files(dir_path):
        """List files in directory. FIXME: not recursive."""
        # TODO: add filtering
        return os.listdir(dir_path)
    ''')

    _write_file(f"{path}/mixedutils/strings.py", '''
    """String helpers — no docstrings."""
    def reverse(s):
        return s[::-1]

    def capitalize(s):
        return s.capitalize()

    def count_words(s):
        return len(s.split())
    ''')

    _write_file(f"{path}/tests/test_data.py", '''
    from mixedutils.data import deduplicate, chunk

    def test_deduplicate():
        assert deduplicate([1, 2, 2, 3, 3, 3]) == [1, 2, 3]

    def test_chunk():
        assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    ''')

    # Note: no tests for files.py or strings.py

    _write_file(f"{path}/LICENSE", "MIT License\n")

    _git_init(path, commits=7, author="Mixed Dev")
    return path


# ─── Ground Truth ───

# Expected quality scores for each test repo (1-10 scale)
# These are our "reviewer rankings" — the ground truth we evaluate against
GROUND_TRUTH = {
    "platinum_repo": {"score": 9, "tier": "platinum", "rec": "adopt", "label": "Excellent quality: tests, docs, low complexity"},
    "good_with_tests": {"score": 8, "tier": "gold", "rec": "adopt", "label": "Good quality with strong test suite"},
    "well_documented": {"score": 8, "tier": "gold", "rec": "adopt", "label": "Excellent documentation and decent tests"},
    "no_tests": {"score": 4, "tier": "silver", "rec": "investigate", "label": "Decent code but zero tests"},
    "high_complexity": {"score": 4, "tier": "silver", "rec": "investigate", "label": "Overly complex code, hard to maintain"},
    "tech_debt_heavy": {"score": 2, "tier": "bronze", "rec": "avoid", "label": "Heavy tech debt: TODOs, FIXMEs, hacks"},
    "no_readme": {"score": 2, "tier": "bronze", "rec": "avoid", "label": "No README, minimal code"},
    "single_author": {"score": 3, "tier": "bronze", "rec": "avoid", "label": "Single contributor, low activity, bus factor risk"},
    "minimal_project": {"score": 1, "tier": "bronze", "rec": "avoid", "label": "Bare minimum, almost empty"},
    "dependency_heavy": {"score": 3, "tier": "bronze", "rec": "avoid", "label": "Too many dependencies, no tests"},
    "mixed_quality": {"score": 5, "tier": "silver", "rec": "investigate", "label": "Mixed: good data utils, bad file utils, no string tests"},
    "broken_tests": {"score": 3, "tier": "bronze", "rec": "avoid", "label": "Tests exist but are broken/failing"},
}


def gen_broken_tests():
    """Tests exist but are broken/failing."""
    path = os.path.join(BASE_DIR, "broken_tests")
    if os.path.exists(path):
        shutil.rmtree(path)

    _write_file(f"{path}/README.md", """
    # Math Utils

    A math utility library with tests.
    """)

    _write_file(f"{path}/setup.py", 'from setuptools import setup\nsetup(name="mathutils", version="0.2.0", packages=["mathutils"])\n')
    _write_file(f"{path}/mathutils/__init__.py", '"""Math utilities."""\nfrom .core import square, cube\n')
    _write_file(f"{path}/mathutils/core.py", '''
    """Math utility functions."""

    def square(n):
        """Return n squared."""
        return n * n

    def cube(n):
        """Return n cubed."""
        return n * n * n
    ''')

    # Broken tests — these will fail when run
    _write_file(f"{path}/tests/test_core.py", '''
    """Tests for math utilities — deliberately broken."""
    from mathutils.core import square, cube

    def test_square():
        assert square(3) == 9  # This passes

    def test_square_negative():
        assert square(-2) == -4  # BUG: should be 4, not -4

    def test_cube():
        assert cube(2) == 6  # BUG: should be 8

    def test_missing_function():
        assert square(0) == 1  # BUG: should be 0
    ''')

    _write_file(f"{path}/LICENSE", "MIT License\n")
    _git_init(path, commits=5, author="Greg Tester")
    return path


def generate_all():
    """Generate all test repositories."""
    os.makedirs(BASE_DIR, exist_ok=True)

    generators = [
        gen_platinum_repo,
        gen_good_with_tests,
        gen_well_documented,
        gen_no_tests,
        gen_high_complexity,
        gen_tech_debt_heavy,
        gen_no_readme,
        gen_single_author,
        gen_minimal_project,
        gen_dependency_heavy,
        gen_mixed_quality,
        gen_broken_tests,
    ]

    paths = {}
    for gen in generators:
        name = gen.__name__.replace("gen_", "")
        path = gen()
        paths[name] = path
        print(f"Generated: {name} -> {path}")

    # Save ground truth
    gt_path = os.path.join(BASE_DIR, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(GROUND_TRUTH, f, indent=2)
    print(f"\nGround truth saved to {gt_path}")
    print(f"Total repos: {len(paths)}")

    return paths


if __name__ == "__main__":
    generate_all()
