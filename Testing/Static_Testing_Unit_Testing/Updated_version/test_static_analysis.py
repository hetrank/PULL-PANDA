import sys
import types
import pytest
import subprocess
from unittest.mock import MagicMock

# Import the real module now
import static_analysis


# ============================================================
# TESTS for get_changed_files_and_languages
# ============================================================

def test_get_changed_files_and_languages_normal():
    diff = """+++ b/src/main.py
+++ b/utils/helper.js
+++ b/test/test.cpp
+++ b/README.md
"""
    out = static_analysis.get_changed_files_and_languages(diff)

    assert out == {
        "python": ["src/main.py"],
        "javascript": ["utils/helper.js"],
        "cpp": ["test/test.cpp"],
    }


def test_get_changed_files_and_languages_no_match():
    diff = """+++ b/docs/README.md"""
    out = static_analysis.get_changed_files_and_languages(diff)
    assert out == {}  # no valid language extension


def test_get_changed_files_and_languages_multiple_same_lang():
    diff = """+++ b/app/app.py
+++ b/module/mod.PY
"""
    out = static_analysis.get_changed_files_and_languages(diff)

    # The function keeps the exact filename case
    assert out == {
        "python": [
            "app/app.py",
            "module/mod.PY"
        ]
    }


# ============================================================
# TESTS for run_static_analysis
# ============================================================

def test_run_static_analysis_no_changed_files():
    diff = """+++ b/README.md"""
    out = static_analysis.run_static_analysis(diff)

    assert "No recognizable programming language files" in out


def test_run_static_analysis_lang_with_no_analyzer(monkeypatch):
    """Simulate a language present in map, but no analyzers configured."""
    diff = """+++ b/file.rs"""  # rust IS configured though
    # Patch ANALYZERS to empty dict
    monkeypatch.setattr(static_analysis, "ANALYZERS", {})

    out = static_analysis.run_static_analysis(diff)

    assert "No analyzer configured for rust" in out


def test_run_static_analysis_success_stdout(monkeypatch):
    """Simulate an analyzer returning STDOUT output."""
    diff = """+++ b/app/main.py"""

    # Fake result with stdout
    def fake_run(cmd, capture_output, text, check, timeout):
        m = MagicMock()
        m.stdout = "OK-STDOUT"
        m.stderr = ""
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "OK-STDOUT" in out
    assert "Pylint" in out  # analyzer name


def test_run_static_analysis_success_stderr(monkeypatch):
    """Simulate analyzer returning only stderr."""
    diff = """+++ b/app/main.py"""

    def fake_run(cmd, capture_output, text, check, timeout):
        m = MagicMock()
        m.stdout = ""
        m.stderr = "ERR-ONLY"
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "ERR-ONLY" in out


def test_run_static_analysis_success_no_output(monkeypatch):
    """Simulate analyzer returns no output at all."""
    diff = """+++ b/app/main.py"""

    def fake_run(cmd, capture_output, text, check, timeout):
        m = MagicMock()
        m.stdout = ""
        m.stderr = ""
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "No issues found" in out


def test_run_static_analysis_filenotfound(monkeypatch):
    """Simulate missing analyzer binary in environment."""
    diff = """+++ b/app/main.py"""

    def fake_run(cmd, capture_output, text, check, timeout):
        raise FileNotFoundError("missing exe")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "Command not found" in out


def test_run_static_analysis_timeout(monkeypatch):
    """Simulate analyzer timeout."""
    diff = """+++ b/app/main.py"""

    def fake_run(cmd, capture_output, text, check, timeout):
        raise subprocess.TimeoutExpired(cmd="tool", timeout=120)

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "Execution timed out" in out


def test_run_static_analysis_generic_exception(monkeypatch):
    """Simulate other unexpected analyzer error."""
    diff = """+++ b/app/main.py"""

    def fake_run(cmd, capture_output, text, check, timeout):
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = static_analysis.run_static_analysis(diff)

    assert "Error running analyzer" in out
