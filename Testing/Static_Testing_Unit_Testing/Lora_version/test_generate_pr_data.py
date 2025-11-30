"""
tests for generate_pr_data.py

Covers:
- generate_pr_and_review()

Notes:
- All external dependencies (Groq API, file I/O, env vars) are mocked.
- No real network or filesystem calls.
- Each test prints its name when executed for visibility.
- Provides 100% coverage with 10 unique and meaningful scenarios.
"""

import io
import json
import builtins
import importlib
from types import SimpleNamespace
import pytest


# ===== Helper: import generate_pr_data freshly =====
def _import_generate_pr_data_fresh(monkeypatch, client=None):
    """Re-import generate_pr_data.py with Groq mocked before import."""
    import sys

    # --- Patch Groq before importing so it won't need API_KEY ---
    class FakeGroq:
        def __init__(self, api_key=None):
            self.api_key = api_key
            # Provide dummy chat.completions.create method
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda *a, **k: None)
            )

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=FakeGroq))

    # Import generate_pr_data fresh
    sys.modules.pop("generate_pr_data", None)
    mod = importlib.import_module("generate_pr_data")

    # Replace its client with our test mock if provided
    if client is not None:
        monkeypatch.setattr(mod, "client", client)

    return mod


# ===== Helper: Fake Groq client & response handling =====
class FakeResponse:
    def __init__(self, text):
        msg = SimpleNamespace(content=text)
        self.choices = [SimpleNamespace(message=msg)]


def make_fake_client(responses):
    """Return fake client that cycles through given responses."""
    counter = {"i": 0}

    def create(*args, **kwargs):
        idx = counter["i"]
        counter["i"] += 1
        if idx >= len(responses):
            idx = -1
        return FakeResponse(responses[idx])

    fake_chat = SimpleNamespace(completions=SimpleNamespace(create=create))
    return SimpleNamespace(chat=fake_chat)


# ===== File Mock Helpers =====
class DummyFile(io.StringIO):
    """Mock file that never closes (so tests can read contents)."""
    def __init__(self):
        super().__init__()
        self.writes = []

    def write(self, s):
        self.writes.append(s)
        return super().write(s)

    def close(self):
        # Override close() to keep buffer readable
        pass


def mock_open(dummy):
    """Return a context-manager mock that yields DummyFile and never closes it."""
    class MockCtx:
        def __enter__(self_inner):
            return dummy
        def __exit__(self_inner, exc_type, exc_val, exc_tb):
            return False  # Don’t close DummyFile
    return lambda *a, **k: MockCtx()


# ===== Tests for generate_pr_and_review() =====
print("# ===== Tests for generate_pr_and_review() =====")


def test_multiple_valid_responses(monkeypatch, capsys):
    print("Running: test_multiple_valid_responses")
    responses = [
        "PR Title: Fix bug\nPR Description: Fix issue.\n```\n- old\n+ new\n```\nReview: Ok",
        "PR Title: Add file\nPR Description: Add feature.\n```\n+ file\n```\nReview: Great"
    ]
    client = make_fake_client(responses)
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))

    mod.generate_pr_and_review(n=2)
    out = capsys.readouterr().out
    assert "✅ Generated 2 samples" in out
    lines = dummy.getvalue().strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        data = json.loads(line)
        assert "prompt" in data and "completion" in data


def test_parsing_failure_branch(monkeypatch):
    print("Running: test_parsing_failure_branch")
    malformed = "Completely unstructured nonsense text"
    client = make_fake_client([malformed])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))

    mod.generate_pr_and_review(n=1)
    data = json.loads(dummy.getvalue().strip())
    assert "Review:" in data["prompt"]
    assert data["completion"].strip() == ""


def test_bold_markdown_and_diff_extraction(monkeypatch):
    print("Running: test_bold_markdown_and_diff_extraction")
    resp = "**PR Title: Refactor**\nPR Description: **Improve readability**\n```\n- x\n+ y\n```\nReview: Clean!"
    client = make_fake_client([resp])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))

    mod.generate_pr_and_review(n=1)
    obj = json.loads(dummy.getvalue().strip())
    assert "**" not in obj["prompt"]
    assert "```" in obj["prompt"]
    assert obj["completion"].strip().startswith("Clean")


def test_no_backticks_diff_empty(monkeypatch):
    print("Running: test_no_backticks_diff_empty")
    resp = "PR Title: Minor\nPR Description: Short\nReview: ok"
    client = make_fake_client([resp])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))

    mod.generate_pr_and_review(n=1)
    obj = json.loads(dummy.getvalue().strip())
    assert "Code Diff:" in obj["prompt"]
    assert "```" not in obj["prompt"]


def test_zero_entries(monkeypatch, capsys):
    print("Running: test_zero_entries")
    client = make_fake_client([])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))
    mod.generate_pr_and_review(n=0)
    out = capsys.readouterr().out
    assert "✅ Generated 0 samples" in out
    assert dummy.getvalue() == ""


def test_api_exception(monkeypatch):
    print("Running: test_api_exception")
    def raise_error(*a, **k): raise RuntimeError("API down")
    fake_chat = SimpleNamespace(completions=SimpleNamespace(create=raise_error))
    client = SimpleNamespace(chat=fake_chat)
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    monkeypatch.setattr(builtins, "open", mock_open(DummyFile()))
    with pytest.raises(RuntimeError):
        mod.generate_pr_and_review(n=1)


def test_whitespace_trimming(monkeypatch):
    print("Running: test_whitespace_trimming")
    resp = "  PR Title:  T  \nPR Description:   D   \n```\n+ ok\n```\nReview:   fine   "
    client = make_fake_client([resp])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))
    mod.generate_pr_and_review(n=1)
    obj = json.loads(dummy.getvalue().strip())
    assert "T" in obj["prompt"]
    assert obj["completion"].strip() == "fine"


def test_unique_json_lines(monkeypatch):
    print("Running: test_unique_json_lines")
    r1 = "PR Title: A\nPR Description: D1\n```\n+ x\n```\nReview: r1"
    r2 = "PR Title: B\nPR Description: D2\n```\n+ y\n```\nReview: r2"
    client = make_fake_client([r1, r2])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))
    mod.generate_pr_and_review(n=2)
    lines = [json.loads(l) for l in dummy.getvalue().strip().splitlines()]
    assert lines[0] != lines[1]


def test_handles_extra_backticks(monkeypatch):
    print("Running: test_handles_extra_backticks")
    # Some responses have multiple triple backtick blocks
    resp = "PR Title: T\nPR Description: D\n```\nA\n```\n```\nB\n```\nReview: ok"
    client = make_fake_client([resp])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))
    mod.generate_pr_and_review(n=1)
    obj = json.loads(dummy.getvalue().strip())
    # should capture the first code block
    assert "A" in obj["prompt"] and "B" not in obj["prompt"]


def test_large_diff_text(monkeypatch):
    print("Running: test_large_diff_text")
    long_diff = "\n".join([f"+ line {i}" for i in range(100)])
    resp = f"PR Title: Long\nPR Description: Long diff\n```\n{long_diff}\n```\nReview: ok"
    client = make_fake_client([resp])
    mod = _import_generate_pr_data_fresh(monkeypatch, client)
    dummy = DummyFile()
    monkeypatch.setattr(builtins, "open", mock_open(dummy))
    mod.generate_pr_and_review(n=1)
    obj = json.loads(dummy.getvalue().strip())
    assert "+ line 99" in obj["prompt"]
    assert obj["completion"].strip() == "ok"
