"""
Test suite for version_1_traditional_rag.py module.

Tests cover:
- API key loading and validation
- GitHub PR fetching and error handling
- PR diff retrieval
- Review comment posting
- AI review chain integration
- End-to-end main workflow
"""
import requests
import importlib
import os
import sys
import pytest
import builtins
import json
from unittest.mock import patch, MagicMock, mock_open
import version_1_traditional_rag as v1


# --------------------------
# FIXTURES
# --------------------------
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set fake environment variables for every test."""
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")
    monkeypatch.setenv("API_KEY", "fake_api")


# --------------------------
# TEST: get_latest_pr
# --------------------------
@patch("version_1_traditional_rag.requests.get")
def test_get_latest_pr_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"number": 42, "html_url": "https://github.com/example/pr/42"}
    ]
    pr_number, pr_url = v1.get_latest_pr("owner", "repo", "token")
    assert pr_number == 42
    assert "example" in pr_url


@patch("version_1_traditional_rag.requests.get")
def test_get_latest_pr_no_open_prs(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []
    with pytest.raises(ValueError, match="No open PRs"):
        v1.get_latest_pr("owner", "repo", "token")


@patch("version_1_traditional_rag.requests.get")
def test_get_latest_pr_api_error(mock_get):
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {"error": "not found"}
    with pytest.raises(ValueError, match="GitHub API Error"):
        v1.get_latest_pr("owner", "repo", "token")


# --------------------------
# TEST: fetch_pr_diff
# --------------------------
@patch("version_1_traditional_rag.requests.get")
@patch("builtins.open", new_callable=mock_open)
def test_fetch_pr_diff_success(mock_open_file, mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "diff --git a/file.py b/file.py"
    diff = v1.fetch_pr_diff("owner", "repo", 5, "token")
    assert "diff --git" in diff
    mock_open_file.assert_called_once_with("latest_pr.diff", "w", encoding="utf-8")


@patch("version_1_traditional_rag.requests.get")
def test_fetch_pr_diff_error(mock_get, capsys):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "error"
    result = v1.fetch_pr_diff("owner", "repo", 99, "token")
    captured = capsys.readouterr()
    assert "Error fetching diff" in captured.out
    assert result == ""


@patch("version_1_traditional_rag.requests.get")
def test_fetch_pr_diff_too_small_warning(mock_get, capsys):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "short diff"
    _ = v1.fetch_pr_diff("owner", "repo", 1, "token")
    captured = capsys.readouterr()
    assert "Warning" in captured.out


# --------------------------
# TEST: post_review_comment
# --------------------------
@patch("version_1_traditional_rag.requests.post")
def test_post_review_comment_success(mock_post):
    mock_post.return_value.json.return_value = {"id": 1, "html_url": "ok"}
    res = v1.post_review_comment("owner", "repo", 9, "token", "nice work")
    assert res["html_url"] == "ok"
    mock_post.assert_called_once()


# --------------------------
# TEST: main function
# --------------------------
@patch("version_1_traditional_rag.post_review_comment")
@patch("version_1_traditional_rag.review_chain")
@patch("version_1_traditional_rag.assemble_context")
@patch("version_1_traditional_rag.get_latest_pr")
@patch("version_1_traditional_rag.fetch_pr_diff")
@patch("version_1_traditional_rag.build_index_for_repo")
@patch.object(sys, "argv", ["version_1_traditional_rag.py", "user", "repo"])
def test_main_success(mock_build, mock_diff, mock_get_pr, mock_assemble, mock_chain, mock_post):
    # Mock RAG retriever
    mock_retriever = MagicMock()
    mock_retriever.get_relevant_documents.return_value = ["doc1", "doc2"]
    mock_build.return_value.as_retriever.return_value = mock_retriever

    # PR and Diff data
    mock_get_pr.return_value = (123, "https://github.com/x/pr/123")
    mock_diff.return_value = "diff --git"

    mock_assemble.return_value = "assembled context"
    mock_chain.invoke.return_value = "AI review text"
    mock_post.return_value = {"html_url": "https://github.com/review/comment"}

    v1.main()

    mock_build.assert_called_once()
    mock_chain.invoke.assert_called_once()
    mock_post.assert_called_once()


@patch("version_1_traditional_rag.build_index_for_repo")
@patch.object(sys, "argv", ["version_1_traditional_rag.py"])
def test_main_missing_args(mock_build, capsys):
    with pytest.raises(SystemExit):
        v1.main()
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


@patch("version_1_traditional_rag.get_latest_pr", side_effect=ValueError("bad repo"))
@patch("version_1_traditional_rag.build_index_for_repo")
@patch.object(sys, "argv", ["version_1_traditional_rag.py", "user", "repo"])
def test_main_value_error(mock_build, mock_get_pr, capsys):
    v1.main()
    captured = capsys.readouterr()
    assert "Error:" in captured.out


@patch("version_1_traditional_rag.fetch_pr_diff", return_value="")
@patch("version_1_traditional_rag.get_latest_pr", return_value=(1, "url"))
@patch("version_1_traditional_rag.build_index_for_repo")
@patch.object(sys, "argv", ["version_1_traditional_rag.py", "user", "repo"])
def test_main_no_diff(mock_build, mock_get, mock_diff, capsys):
    v1.main()
    captured = capsys.readouterr()
    assert "Error" in captured.out


@patch("version_1_traditional_rag.post_review_comment", return_value={"error": "fail"})
@patch("version_1_traditional_rag.review_chain")
@patch("version_1_traditional_rag.assemble_context")
@patch("version_1_traditional_rag.get_latest_pr", return_value=(2, "url"))
@patch("version_1_traditional_rag.fetch_pr_diff", return_value="diff --git")
@patch("version_1_traditional_rag.build_index_for_repo")
@patch.object(sys, "argv", ["version_1_traditional_rag.py", "user", "repo"])
def test_main_post_failure(mock_build, mock_diff, mock_get, mock_assemble, mock_chain, mock_post, capsys):
    mock_retriever = MagicMock()
    mock_retriever.get_relevant_documents.return_value = ["doc"]
    mock_build.return_value.as_retriever.return_value = mock_retriever
    mock_chain.invoke.return_value = "Review"

    v1.main()
    captured = capsys.readouterr()
    assert "Failed to post review" in captured.out


# --------------------------
# TEST: API key validation
# --------------------------
# Mock os.getenv globally to control what the module sees when asking for env vars.
# We also use @patch.dict to clear the environment variables for completeness.
@patch.dict(os.environ, {}, clear=True)
@patch('os.getenv') 
@patch('version_1_traditional_rag.load_dotenv') # Crucial to stop keys loading from a physical .env file
def test_missing_api_keys(mock_load_dotenv, mock_getenv, monkeypatch):
    
    # Define a side effect for os.getenv to return None for the keys we are testing.
    # This guarantees the keys are seen as missing.
    def mock_getenv_side_effect(key):
        if key in ("GITHUB_TOKEN", "API_KEY"):
            return None
        # Allow other system environment variables to be accessed normally if needed
        return os.environ.get(key) 

    mock_getenv.side_effect = mock_getenv_side_effect
    
    # Ensure the environment is clean, even though the mock handles the return value
    # You are testing for 'API_KEY' which is what GROQ_API_KEY is loaded from
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    
    # Assert that reloading the module (which runs the top-level key check) 
    # raises the expected ValueError.
    with pytest.raises(ValueError, match="Missing API keys"):
        importlib.reload(v1)

# --------------------------
# EXTRA TESTS FOR FULL COVERAGE
# --------------------------

@patch("version_1_traditional_rag.requests.get")
def test_fetch_pr_diff_exactly_50_chars(mock_get, capsys):
    """Covers diff length == 50 branch in fetch_pr_diff."""
    # Create a fake diff of exactly 50 characters
    fake_diff = "a" * 50
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = fake_diff

    result = v1.fetch_pr_diff("owner", "repo", 1, "token")
    captured = capsys.readouterr()
    # Ensure the function returns correctly without warning
    assert result == fake_diff
    # No warning should appear since len(diff) == 50
    assert "Warning" not in captured.out


@patch("version_1_traditional_rag.build_index_for_repo", side_effect=__import__("requests").RequestException("Network error"))
@patch.object(sys, "argv", ["version_1_traditional_rag.py", "user", "repo"])
def test_main_requests_exception(mock_build, capsys):
    """Covers requests.RequestException branch in main()."""
    v1.main()
    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "Network error" in captured.out
