from __future__ import annotations

import tomllib
from pathlib import Path

import flexfund
from flexfund import _api_version


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    assert flexfund.__version__ == pyproject["project"]["version"]


def test_api_version_is_exported() -> None:
    assert flexfund.API_VERSION == _api_version.API_VERSION
    assert flexfund.API_VERSION.startswith("v")
