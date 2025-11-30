# ===== Tests for config module load and variables =====
"""Pytest tests for `config.py`.

Covers normal flows, edge cases, and boundary conditions. All external effects are mocked:
- `dotenv.load_dotenv` is replaced with a noop via an injected dummy module.
- The module is imported via `importlib.util.spec_from_file_location` using a path
  relative to this test file (no absolute paths).
Each test follows Arrange-Act-Assert and uses `monkeypatch` to set environment variables.
"""

import os
import sys
import types
import importlib.util
import pytest


def _import_config_module():
    """Import `config.py` from the same directory as this test file.

    This uses a fresh module import each call (removes previous `config` from sys.modules)
    and ensures a dummy `dotenv` module is present so no file I/O occurs.
    """
    # Ensure we import a fresh copy
    sys.modules.pop("config", None)

    # Ensure a dummy dotenv module so load_dotenv() is a no-op
    dummy_dotenv = types.ModuleType("dotenv")
    dummy_dotenv.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = dummy_dotenv

    # Locate file relative to this test file
    import os as _os
    here = _os.path.dirname(__file__)
    path = _os.path.join(here, "config.py")

    spec = importlib.util.spec_from_file_location("config", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== Tests for config module load and variables =====


def test_config_loads_all_variables_when_present(monkeypatch, capsys):
    """Arrange: all required env vars present (including Pinecone); Act: import config; Assert: values set correctly and no SystemExit.

    AAA structure: set env, import, assert attributes.
    """
    # Arrange
    monkeypatch.setenv("OWNER", "alice")
    monkeypatch.setenv("REPO", "repo")
    monkeypatch.setenv("GITHUB_TOKEN", "gh_tok")
    monkeypatch.setenv("GROQ_API_KEY", "groq")
    monkeypatch.setenv("PINECONE_API_KEY", "pine_key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "pine_idx")
    monkeypatch.setenv("PR_NUMBER", "42")

    # Act
    mod = _import_config_module()

    # Assert
    assert mod.OWNER == "alice"
    assert mod.REPO == "repo"
    assert mod.GITHUB_TOKEN == "gh_tok"
    assert mod.GROQ_API_KEY == "groq"
    assert mod.PINECONE_API_KEY == "pine_key"
    assert mod.PINECONE_INDEX_NAME == "pine_idx"
    assert isinstance(mod.PR_NUMBER, int) and mod.PR_NUMBER == 42

    # Ensure no warning printed for PR_NUMBER
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out


@pytest.mark.parametrize("val", [None, "abc"])
def test_config_invalid_or_missing_pr_number_defaults_to_zero_and_warns(monkeypatch, capsys, val):
    """Arrange: PR_NUMBER missing or invalid; Act: import config; Assert: PR_NUMBER==0 and warning printed.

    Parametrized for missing (None) and invalid string.
    """
    # Arrange
    monkeypatch.setenv("OWNER", "o")
    monkeypatch.setenv("REPO", "r")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setenv("PINECONE_API_KEY", "p_k")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "p_idx")
    if val is None:
        # ensure PR_NUMBER not set
        monkeypatch.delenv("PR_NUMBER", raising=False)
    else:
        monkeypatch.setenv("PR_NUMBER", val)

    # Act
    mod = _import_config_module()

    # Assert
    assert mod.PR_NUMBER == 0
    captured = capsys.readouterr()
    assert "PR_NUMBER is missing or invalid" in captured.out


@pytest.mark.parametrize("val", ["0", "-5"])
def test_config_pr_number_non_positive_prints_warning_and_retains_numeric(monkeypatch, capsys, val):
    """Arrange: PR_NUMBER set to non-positive numeric; Act: import config; Assert: PR_NUMBER numeric and warning printed.

    Tests edge boundaries 0 and negative values.
    """
    # Arrange
    monkeypatch.setenv("OWNER", "o2")
    monkeypatch.setenv("REPO", "r2")
    monkeypatch.setenv("GITHUB_TOKEN", "t2")
    monkeypatch.setenv("GROQ_API_KEY", "g2")
    monkeypatch.setenv("PINECONE_API_KEY", "p_k2")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "p_idx2")
    monkeypatch.setenv("PR_NUMBER", val)

    # Act
    mod = _import_config_module()

    # Assert: conversion succeeds to int but is <= 0
    assert isinstance(mod.PR_NUMBER, int)
    assert mod.PR_NUMBER <= 0
    captured = capsys.readouterr()
    assert "PR_NUMBER is missing or invalid" in captured.out


def test_config_raises_systemexit_when_required_envs_missing(monkeypatch):
    """Arrange: missing OWNER or REPO or tokens; Act: import config; Assert: SystemExit raised with helpful message.
    """
    # Arrange - leave out OWNER
    monkeypatch.delenv("OWNER", raising=False)
    monkeypatch.setenv("REPO", "r")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setenv("PINECONE_API_KEY", "p_k")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "p_idx")

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        _import_config_module()
    assert "Missing required .env variables" in str(exc.value)


def test_config_raises_systemexit_when_pinecone_vars_missing(monkeypatch):
    """Arrange: missing pinecone envs; Act: import config; Assert: SystemExit raised about Pinecone.
    """
    # Arrange - have the main required vars but omit pinecone index
    monkeypatch.setenv("OWNER", "o3")
    monkeypatch.setenv("REPO", "r3")
    monkeypatch.setenv("GITHUB_TOKEN", "t3")
    monkeypatch.setenv("GROQ_API_KEY", "g3")
    monkeypatch.setenv("PINECONE_API_KEY", "")
    monkeypatch.delenv("PINECONE_INDEX_NAME", raising=False)

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        _import_config_module()
    assert "Missing PINECONE_API_KEY or PINECONE_INDEX_NAME" in str(exc.value)
