import os
import builtins
import pytest
import version2
import requests
import subprocess
from unittest.mock import (
    patch,
    MagicMock,
)


# ============================================================
# 1. ENVIRONMENT + CONFIG TESTS
# ============================================================

def test_missing_groq_key(monkeypatch):
    """Ensure ValueError when GROQ_API_KEY is missing."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(ValueError):
        with patch("version2.load_dotenv"):
            import importlib
            importlib.reload(version2)


def test_partial_github_config(monkeypatch):
    """Ensure code warns but doesn't crash when GitHub config missing."""
    monkeypatch.setenv("GROQ_API_KEY", "123")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OWNER", raising=False)
    monkeypatch.delenv("REPO", raising=False)
    monkeypatch.delenv("PR_NUMBER", raising=False)

    with patch("version2.load_dotenv"):
        import importlib
        importlib.reload(version2)


# ============================================================
# 2. GITHUB FETCHING
# ============================================================

def test_fetch_pr_data_success(monkeypatch):
    data = {"title": "Fix bug", "diff_url": "https://example.com/diff"}
    mock_resp = MagicMock(status_code=200, json=lambda: data)

    monkeypatch.setattr(requests, "get", lambda *a, **k: mock_resp)
    out = version2.fetch_pr_data("a", "b", 1, "token")
    assert out == data


def test_fetch_pr_data_failure(monkeypatch):
    mock_resp = MagicMock(status_code=400, json=lambda: {"error": "bad"})
    monkeypatch.setattr(requests, "get", lambda *a, **k: mock_resp)

    with pytest.raises(ValueError):
        version2.fetch_pr_data("a", "b", 1, "token")


def test_fetch_pr_diff(monkeypatch):
    """Ensure diff and title extracted correctly."""
    pr_data = {"title": "Fix bug", "diff_url": "url"}
    mock_meta = MagicMock(status_code=200, json=lambda: pr_data)
    mock_diff = MagicMock(text="diff-lines")

    def fake_get(url, *a, **k):
        return mock_meta if "pulls" in url else mock_diff

    monkeypatch.setattr(requests, "get", fake_get)

    diff, title = version2.fetch_pr_diff("a", "b", 2, "token")
    assert diff == "diff-lines"
    assert title == "Fix bug"


def test_post_review_comment_success(monkeypatch):
    resp_data = {"html_url": "http://github/comment"}
    mock_resp = MagicMock(status_code=201, json=lambda: resp_data)

    monkeypatch.setattr(requests, "post", lambda *a, **k: mock_resp)

    res = version2.post_review_comment("a", "b", 3, "tok", "hello")
    assert res["html_url"] == "http://github/comment"


def test_post_review_comment_failure(monkeypatch):
    mock_resp = MagicMock(status_code=403, text="Forbidden")
    monkeypatch.setattr(requests, "post", lambda *a, **k: mock_resp)

    res = version2.post_review_comment("a", "b", 3, "tok", "hello")
    assert res is None


# ============================================================
# 3. STATIC ANALYSIS
# ============================================================

def test_get_changed_files_and_languages():
    diff = """
        +++ b/app.py
        +++ b/utils.cpp
        +++ b/test.js
    """
    out = version2.get_changed_files_and_languages(diff)
    assert "python" in out
    assert "cpp" in out
    assert "javascript" in out


def test_run_static_analysis_no_files(monkeypatch):
    monkeypatch.setattr(version2, "get_changed_files_and_languages", lambda x: {})
    assert version2.run_static_analysis("dummy") == "No supported language files detected."


def test_run_static_analysis_file_not_found(monkeypatch):
    monkeypatch.setattr(version2, "get_changed_files_and_languages",
                        lambda x: {"python": ["missing.py"]})

    monkeypatch.setattr(os.path, "exists", lambda x: False)

    out = version2.run_static_analysis("dummy")
    assert "Skipped" in out


def test_run_static_analysis_tool_error(monkeypatch):
    monkeypatch.setattr(version2, "get_changed_files_and_languages",
                        lambda x: {"python": ["main.py"]})

    monkeypatch.setattr(os.path, "exists", lambda x: True)

    def fake_run(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = version2.run_static_analysis("dummy")
    assert "Tool not installed" in out


def test_run_static_analysis_tool_output(monkeypatch):
    monkeypatch.setattr(version2, "get_changed_files_and_languages",
                        lambda x: {"python": ["main.py"]})
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    mock_proc = MagicMock(stdout="lint ok", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_proc)

    out = version2.run_static_analysis("dummy")
    assert "lint ok" in out


# ============================================================
# 4. RAG INDEXING + RETRIEVAL
# ============================================================

def test_index_repository_no_docs(monkeypatch):
    monkeypatch.setattr(os, "walk", lambda x: [])
    mock_print = MagicMock()
    monkeypatch.setattr(builtins, "print", mock_print)

    version2.index_repository(".", "repo_index")
    mock_print.assert_any_call("No documents found to index.")


def test_index_repository_success(monkeypatch):
    fake_files = [("root", [], ["a.py", "b.md"])]
    monkeypatch.setattr(os, "walk", lambda x: fake_files)

    mock_loader = MagicMock()
    mock_loader.load.return_value = ["doc1"]
    monkeypatch.setattr(version2, "TextLoader", lambda *a, **k: mock_loader)

    mock_splitter = MagicMock()
    mock_splitter.split_documents.return_value = ["chunk1"]
    monkeypatch.setattr(version2, "RecursiveCharacterTextSplitter", lambda *a, **k: mock_splitter)

    chroma_mock = MagicMock()
    monkeypatch.setattr(version2.Chroma, "from_documents", chroma_mock)

    version2.index_repository(".", "repo_index")
    chroma_mock.assert_called()


def test_load_vector_index_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        version2.load_vector_index(str(tmp_path / "missing"))


def test_load_vector_index_success(monkeypatch, tmp_path):
    os.makedirs(tmp_path / "repo", exist_ok=True)
    mock_chroma = MagicMock()
    monkeypatch.setattr(version2, "Chroma", lambda *a, **k: mock_chroma)

    out = version2.load_vector_index(str(tmp_path / "repo"))
    assert out == mock_chroma


def test_query_repo_context(monkeypatch):
    mock_db = MagicMock()
    mock_db.similarity_search.return_value = [
        MagicMock(page_content="A"),
        MagicMock(page_content="B"),
        MagicMock(page_content="A"),  # duplicate
    ]
    monkeypatch.setattr(version2, "load_vector_index", lambda *a, **k: mock_db)

    out = version2.query_repo_context("q")
    assert out.count("A") == 1
    assert "B" in out


# ============================================================
# 5. MAIN EXECUTION
# ============================================================

def test_main_success(monkeypatch):
    """Test full pipeline (mocked end to end)."""

    # ENV
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("OWNER", "o")
    monkeypatch.setenv("REPO", "r")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("GROQ_API_KEY", "abc")

    # GitHub
    monkeypatch.setattr(version2, "fetch_pr_diff", lambda *a, **k: ("diff", "title"))

    # static analysis
    monkeypatch.setattr(version2, "run_static_analysis", lambda x: "static")

    # RAG
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(version2, "query_repo_context", lambda *a, **k: "ctx")

    # LLM
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "review"
    monkeypatch.setattr(version2, "review_chain", mock_chain)

    # GitHub POST
    monkeypatch.setattr(version2, "post_review_comment",
                        lambda *a, **k: {"ok": True})

    version2.main()


def test_main_missing_github(monkeypatch):
    """Ensure main() fails when GitHub config missing."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "abc")

    with pytest.raises(ValueError):
        version2.main()
