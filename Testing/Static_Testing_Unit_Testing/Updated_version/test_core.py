"""Pytest tests for `core.py`.

Requirements:
- All external dependencies are mocked (requests, static_analysis, utils, rag_core, llm/parser).
- Tests follow Arrange-Act-Assert and have descriptive names.
- No real network or filesystem calls are made.
"""

import os
import sys
import types
import importlib.util
import builtins
from unittest.mock import Mock, mock_open
import pytest


def _load_core_module_with_dummy_deps():
    """Load `core.py` from same directory, injecting dummy modules to avoid import-time side effects."""
    # Ensure a fresh import
    sys.modules.pop("core", None)

    # Dummy config module (avoid using real env)
    cfg = types.ModuleType("config")
    cfg.GITHUB_TOKEN = "gh_tok"
    cfg.GROQ_API_KEY = "groq"
    sys.modules["config"] = cfg

    # Dummy static_analysis module
    stat = types.ModuleType("static_analysis")
    stat.run_static_analysis = lambda diff: "STATIC_ANALYSIS_OUTPUT"
    sys.modules["static_analysis"] = stat

    # Dummy utils module
    utils = types.ModuleType("utils")
    utils.safe_truncate = lambda s, n: (s if len(s) <= n else s[:n])
    sys.modules["utils"] = utils

    # Dummy rag_core module with get_retriever
    rag = types.ModuleType("rag_core")
    class DummyDoc:
        def __init__(self, content):
            self.page_content = content

    class DummyRetriever:
        def __init__(self, docs):
            self.docs = docs
        def invoke(self, query):
            return [DummyDoc(d) for d in self.docs]

    rag.get_retriever = lambda: DummyRetriever(["doc1", "doc2"])
    sys.modules["rag_core"] = rag

    # Dummy langchain_core.output_parsers.StrOutputParser
    langcore = types.ModuleType("langchain_core.output_parsers")
    class StrOutputParser:
        pass
    langcore.StrOutputParser = StrOutputParser
    sys.modules["langchain_core.output_parsers"] = langcore

    # Dummy langchain_groq.ChatGroq
    lg = types.ModuleType("langchain_groq")
    class ChatGroq:
        def __init__(self, *a, **k):
            pass
    lg.ChatGroq = ChatGroq
    sys.modules["langchain_groq"] = lg

    # Import core.py relative to this test file
    here = os.path.dirname(__file__)
    path = os.path.join(here, "core.py")
    spec = importlib.util.spec_from_file_location("core", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== Tests for fetch_pr_diff() =====


def test_fetch_pr_diff_success_returns_diff_text(monkeypatch):
    """Arrange: requests returns PR JSON with diff_url and diff text; Act: call fetch_pr_diff; Assert: diff text returned."""
    mod = _load_core_module_with_dummy_deps()

    # Arrange: create two mock responses for sequential requests.get calls
    resp_pr = Mock()
    resp_pr.status_code = 200
    resp_pr.json.return_value = {"diff_url": "http://example.com/diff"}

    resp_diff = Mock()
    resp_diff.status_code = 200
    resp_diff.text = "DIFF_CONTENT"

    get_mock = Mock(side_effect=[resp_pr, resp_diff])
    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(get=get_mock))

    # Act
    out = mod.fetch_pr_diff("o", "r", 1, token="tk")

    # Assert
    assert out == "DIFF_CONTENT"
    assert get_mock.call_count == 2


def test_fetch_pr_diff_missing_diff_url_raises_runtimeerror(monkeypatch):
    """Arrange: PR JSON missing diff_url; Act: call fetch_pr_diff; Assert: RuntimeError raised."""
    mod = _load_core_module_with_dummy_deps()

    resp_pr = Mock()
    resp_pr.status_code = 200
    resp_pr.json.return_value = {}

    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(get=Mock(return_value=resp_pr)))

    with pytest.raises(RuntimeError) as exc:
        mod.fetch_pr_diff("o", "r", 2, token="t")
    assert "No diff_url" in str(exc.value)


def test_fetch_pr_diff_pr_api_error_raises(monkeypatch):
    """Arrange: PR API returns non-200; Act: call fetch_pr_diff; Assert: RuntimeError with status."""
    mod = _load_core_module_with_dummy_deps()

    resp_pr = Mock()
    resp_pr.status_code = 404
    resp_pr.text = "Not Found"

    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(get=Mock(return_value=resp_pr)))

    with pytest.raises(RuntimeError) as exc:
        mod.fetch_pr_diff("o", "r", 3, token="t")
    assert "GitHub API Error" in str(exc.value)


def test_fetch_pr_diff_diff_fetch_fails_raises(monkeypatch):
    """Arrange: PR ok but diff fetch returns non-200; Act: call fetch_pr_diff; Assert: RuntimeError."""
    mod = _load_core_module_with_dummy_deps()

    resp_pr = Mock()
    resp_pr.status_code = 200
    resp_pr.json.return_value = {"diff_url": "u"}

    resp_diff = Mock()
    resp_diff.status_code = 500
    resp_diff.text = "Server Error"

    get_mock = Mock(side_effect=[resp_pr, resp_diff])
    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(get=get_mock))

    with pytest.raises(RuntimeError) as exc:
        mod.fetch_pr_diff("o", "r", 4, token="t")
    assert "Failed to fetch diff" in str(exc.value)


# ===== Tests for post_review_comment() =====


def test_post_review_comment_success_returns_json(monkeypatch):
    """Arrange: requests.post returns 201; Act: call post_review_comment; Assert: returned json dict."""
    mod = _load_core_module_with_dummy_deps()

    resp = Mock()
    resp.status_code = 201
    resp.json.return_value = {"id": 123}

    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(post=Mock(return_value=resp)))

    out = mod.post_review_comment("o", "r", 5, "nice", token="t")
    assert out == {"id": 123}


def test_post_review_comment_failure_raises(monkeypatch):
    """Arrange: requests.post fails; Act: call post_review_comment; Assert: RuntimeError raised."""
    mod = _load_core_module_with_dummy_deps()

    resp = Mock()
    resp.status_code = 500
    resp.text = "Bad"

    monkeypatch.setattr(mod, "requests", types.SimpleNamespace(post=Mock(return_value=resp)))

    with pytest.raises(RuntimeError) as exc:
        mod.post_review_comment("o", "r", 6, "x", token="t")
    assert "Failed to post comment" in str(exc.value)


# ===== Tests for run_prompt() =====


def test_run_prompt_returns_review_static_and_context(monkeypatch):
    """Arrange: run_static_analysis + retriever + prompt chain; Act: call run_prompt; Assert: returns triple with expected content."""
    mod = _load_core_module_with_dummy_deps()

    # Arrange: override run_static_analysis to return predictable value
    monkeypatch.setattr(mod, "run_static_analysis", lambda d: "STATIC_OK")

    # Create a prompt object that supports `|` operator and captures invoke input
    class FinalChain:
        def __init__(self):
            self.last_kwargs = None
        def invoke(self, kwargs):
            # capture and return a synthetic review
            self.last_kwargs = kwargs
            return "SYNTH_REVIEW"

    class PromptStub:
        def __or__(self, other):
            # return an object that again supports | with parser
            class Mid:
                def __init__(self):
                    self.final = FinalChain()
                def __or__(self, parser):
                    return self.final
            return Mid()

    prompt = PromptStub()

    # Retriever that returns docs with page_content
    class Ret:
        def invoke(self, q):
            return [types.SimpleNamespace(page_content="CTX1"), types.SimpleNamespace(page_content="CTX2")]
    monkeypatch.setattr(mod, "get_retriever", lambda: Ret())

    # monkeypatch safe_truncate to evidence truncation
    monkeypatch.setattr(mod, "safe_truncate", lambda s, n: s if len(s) <= n else s[:n])

    # Act
    review, static_out, retrieved_context = mod.run_prompt(prompt, "DIFF_CONTENT_LONG")

    # Assert
    assert review == "SYNTH_REVIEW"
    assert static_out == "STATIC_OK"
    assert "CTX1" in retrieved_context and "CTX2" in retrieved_context


def test_run_prompt_handles_empty_retriever_results(monkeypatch):
    """Arrange: retriever returns empty list; Act: call run_prompt; Assert: context empty string and still returns review."""
    mod = _load_core_module_with_dummy_deps()

    monkeypatch.setattr(mod, "run_static_analysis", lambda d: "S")

    class PromptStub:
        def __or__(self, other):
            class Mid:
                def __or__(self, parser):
                    return types.SimpleNamespace(invoke=lambda kwargs: "R")
            return Mid()

    monkeypatch.setattr(mod, "get_retriever", lambda: types.SimpleNamespace(invoke=lambda q: []))

    review, static_out, retrieved_context = mod.run_prompt(PromptStub(), "d")
    assert review == "R"
    assert static_out == "S"
    assert retrieved_context == ""


# ===== Tests for save_text_to_file() =====


def test_save_text_to_file_writes_content_to_path(monkeypatch):
    """Arrange: monkeypatch builtins.open; Act: call save_text_to_file; Assert: file wrote given text."""
    mod = _load_core_module_with_dummy_deps()

    m = mock_open()
    monkeypatch.setattr(builtins, "open", m)

    mod.save_text_to_file("out.md", "hello")

    m.assert_called_once_with("out.md", "w", encoding="utf-8")
    handle = m()
    handle.write.assert_called_once_with("hello")
