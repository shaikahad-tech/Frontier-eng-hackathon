"""Phase 5 — Additional synthetic repo generators (repos 06-15)

These generators are imported by repos.py to complete the 15-repo benchmark suite.
"""
import os
from src.phase5.repos import _write_file, _git_init


def generate_repo_06(base_path: str) -> str:
    """High complexity but otherwise healthy."""
    repo_path = os.path.join(base_path, "repo_06")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# DataPipeline\n\nA data pipeline tool.\n\n## Installation\n\n```bash\npip install datapipeline\n```\n")
    _write_file(os.path.join(repo_path, "src/pipeline.py"), '"""Complex pipeline."""\ndef process(data, mode, flags, options):\n    if mode == 1:\n        if flags & 0x1:\n            if flags & 0x2:\n                if flags & 0x4:\n                    if data:\n                        for item in data:\n                            if item > 0:\n                                if options.get("transform"):\n                                    if options["transform"] == "double":\n                                        item = item * 2\n                                    elif options["transform"] == "triple":\n                                        item = item * 3\n                                    elif options["transform"] == "quad":\n                                        item = item * 4\n                                    else:\n                                        item = item\n                                if options.get("filter"):\n                                    if item < options["filter"]:\n                                        continue\n                            else:\n                                pass\n                        return data\n                    else:\n                        return None\n                else:\n                    return None\n            else:\n                return None\n        else:\n            return data\n    return None\n')
    _write_file(os.path.join(repo_path, "tests/test_pipeline.py"), '"""Tests."""\nfrom src.pipeline import process\n\ndef test_basic():\n    assert process([1], 1, 0, {}) == [1]\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'datapipeline'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_08(base_path: str) -> str:
    """Good repository with broken CI."""
    repo_path = os.path.join(base_path, "repo_08")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# ApiService\n\nA REST API service.\n\n## Installation\n\n```bash\npip install apiservice\n```\n")
    _write_file(os.path.join(repo_path, "src/api.py"), '"""API service."""\nfrom typing import Any\n\n\nclass ApiService:\n    """Simple API service."""\n    def __init__(self):\n        self._routes = {}\n    def add_route(self, path: str, handler: Any) -> None:\n        self._routes[path] = handler\n    def get_route(self, path: str):\n        return self._routes.get(path)\n')
    _write_file(os.path.join(repo_path, "tests/test_api.py"), '"""Tests."""\nfrom src.api import ApiService\n\ndef test_add_and_get():\n    api = ApiService()\n    api.add_route("/test", lambda: "ok")\n    assert api.get_route("/test")() == "ok"\n')
    _write_file(os.path.join(repo_path, ".github/workflows/ci.yml"), "name: CI\non: [push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'apiservice'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_09(base_path: str) -> str:
    """Good repository with dependency vulnerabilities."""
    repo_path = os.path.join(base_path, "repo_09")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# WebApp\n\nA web application.\n\n## Installation\n\n```bash\npip install webapp\n```\n")
    _write_file(os.path.join(repo_path, "src/app.py"), '"""Web application."""\n\nclass App:\n    """Simple web app."""\n    def __init__(self):\n        self.routes = {}\n    def route(self, path):\n        def decorator(fn):\n            self.routes[path] = fn\n            return fn\n        return decorator\n')
    _write_file(os.path.join(repo_path, "tests/test_app.py"), '"""Tests."""\nfrom src.app import App\n\ndef test_route():\n    app = App()\n    @app.route("/test")\n    def handler(): return "ok"\n    assert app.routes["/test"] == handler\n')
    _write_file(os.path.join(repo_path, "requirements.txt"), "flask==0.12\nrequests\ndjango<2.0\n")
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'webapp'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_10(base_path: str) -> str:
    """Healthy code but abandoned Git history."""
    repo_path = os.path.join(base_path, "repo_10")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# LegacyLib\n\nA legacy library.\n")
    _write_file(os.path.join(repo_path, "src/legacy.py"), '"""Legacy library."""\n\n\nclass Calculator:\n    """Simple calculator."""\n    def add(self, a, b): return a + b\n    def subtract(self, a, b): return a - b\n    def multiply(self, a, b): return a * b\n    def divide(self, a, b):\n        if b == 0: raise ValueError("Cannot divide by zero")\n        return a / b\n')
    _write_file(os.path.join(repo_path, "tests/test_legacy.py"), '"""Tests."""\nimport pytest\nfrom src.legacy import Calculator\n\ndef test_add():\n    assert Calculator().add(1, 2) == 3\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        Calculator().divide(1, 0)\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'legacylib'\nversion = '0.1.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_11(base_path: str) -> str:
    """Active repository with poor architecture."""
    repo_path = os.path.join(base_path, "repo_11")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# QuickScript\n\nA collection of scripts.\n")
    _write_file(os.path.join(repo_path, "main.py"), '"""Main entry point with everything mixed in."""\nimport os, sys, json, subprocess\n\ndef run():\n    data = {"config": {}, "state": {}, "handlers": []}\n    return data\n\ndef process(data):\n    return data\n\ndef save(data, path):\n    with open(path, "w") as f: json.dump(data, f)\n\ndef load(path):\n    with open(path) as f: return json.load(f)\n')
    _write_file(os.path.join(repo_path, "utils.py"), '"""Utils mixed with business logic."""\ndef helper():\n    return True\n\ndef business_logic():\n    return helper() and True\n')
    _write_file(os.path.join(repo_path, "test_main.py"), 'def test_run():\n    from main import run\n    assert run() is not None\n')
    _git_init(repo_path)
    return repo_path


def generate_repo_14(base_path: str) -> str:
    """Adversarial: Security camouflage."""
    repo_path = os.path.join(base_path, "repo_14")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# SecureAPI\n\nA secure API with encryption.\n\n## Installation\n\n```bash\npip install secureapi\n```\n")
    _write_file(os.path.join(repo_path, "src/secure_api.py"), '"""Secure API with hidden vulnerabilities."""\nimport subprocess\nimport base64\n\n# Encoded dangerous command\n_CMD = base64.b64decode(b"c3lzdGVtY3RsIHJlc3RhcnQgbmdpbng=").decode()\n\n\nclass SecureAPI:\n    """API that appears secure but has hidden command injection."""\n\n    def __init__(self):\n        self._handlers = {}\n\n    def register(self, path, handler):\n        self._handlers[path] = handler\n\n    def execute(self, path, *args):\n        handler = self._handlers.get(path)\n        if handler:\n            return handler(*args)\n\n    def _system_call(self, user_input):\n        # Hidden command injection\n        return subprocess.check_output(user_input, shell=True)\n\n    def _health_check(self):\n        # Decoded dangerous command\n        return subprocess.check_output(_CMD, shell=True)\n')
    _write_file(os.path.join(repo_path, "tests/test_api.py"), '"""Tests."""\nfrom src.secure_api import SecureAPI\n\ndef test_register():\n    api = SecureAPI()\n    api.register("/test", lambda: "ok")\n    assert api.execute("/test") == "ok"\n')
    _write_file(os.path.join(repo_path, "pyproject.toml"), "[project]\nname = 'secureapi'\nversion = '1.0.0'\n")
    _git_init(repo_path)
    return repo_path


def generate_repo_15(base_path: str) -> str:
    """Adversarial: Test camouflage."""
    repo_path = os.path.join(base_path, "repo_15")
    os.makedirs(repo_path, exist_ok=True)
    _write_file(os.path.join(repo_path, "README.md"), "# TestedLib\n\nA well-tested library.\n")
    _write_file(os.path.join(repo_path, "src/lib.py"), '"""Library."""\n\ndef func_a(): return True\ndef func_b(): return 0\ndef func_c(): return None\ndef func_d(): return []\ndef func_e(): return {}\n')
    test_code = '"""Tests."""\nfrom src.lib import *\n\n'
    for i in range(200):
        test_code += f"def test_func_{i:03d}():\n    assert True\n"
    _write_file(os.path.join(repo_path, "tests/test_lib.py"), test_code)
    _write_file(os.path.join(repo_path, "setup.py"), "from setuptools import setup\nsetup(name='testedlib', version='1.0.0')\n")
    _git_init(repo_path)
    return repo_path
