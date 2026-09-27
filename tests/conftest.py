"""Shared fixtures for the pytest suite.

The project's scripts are numbered (01_simulate_data.py, etc.) so they sort
in run order in a directory listing, which means they aren't valid Python
module names for a plain `import`. These fixtures load them by file path
instead, once per test session, so both test files can reuse the same
loaded module.
"""

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def simulate_module():
    return _load_module("simulate_data", "01_simulate_data.py")


@pytest.fixture(scope="session")
def clean_module():
    return _load_module("clean_data", "03_clean_data.py")


@pytest.fixture(scope="session")
def analysis_module():
    return _load_module("analysis", "04_analysis.py")
