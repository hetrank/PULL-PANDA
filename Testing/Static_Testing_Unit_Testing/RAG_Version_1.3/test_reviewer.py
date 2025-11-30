import sys
import types
import pytest
from unittest.mock import MagicMock


# ===========================================================
# Fake heavy modules
# ===========================================================

fake_groq = types.ModuleType("langchain_groq")
class FakeChatGroq:
    def __init__(self, model, temperature, api_key):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
fake_groq.ChatGroq = FakeChatGroq
sys.modules["langchain_groq"] = fake_groq

fake_output = types.ModuleType("langchain_core.output_parsers")
class FakeParser:
    def parse(self, x):
        return x
fake_output.StrOutputParser = FakeParser
sys.modules["langchain_core.output_parsers"] = fake_output

fake_config = types.ModuleType("config")
fake_config.GITHUB_TOKEN = "t"
fake_config.OWNER = "o"
fake_config.REPO = "r"
fake_config.GROQ_API_KEY = "key"
sys.modules["config"] = fake_config

# Must import AFTER mocks
import reviewer

import requests


# Helper Response class
class FakeResponse:
    def __init__(self, status=200, text="OK", json_data=None):
        self.status_code = status
        self.text = text
        self._json = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)

    def json(self):
        return self._json


# ===========================================================
# fetch_pr_diff tests
# ===========================================================

def test_fetch_pr_diff_success(monkeypatch):
    def fake_get(url, headers, timeout):
        return FakeResponse(status=200, text="DIFF")
    monkeypatch.setattr(requests, "get", fake_get)

    out = reviewer.fetch_pr_diff("o", "r", 1, "t")
    assert out == "DIFF"


def test_fetch_pr_diff_404(monkeypatch, capsys):
    def fake_get(url, headers, timeout):
        return FakeResponse(status=404, text="nope")

    def fake_raise(self):
        raise requests.exceptions.HTTPError(response=self)

    monkeypatch.setattr(FakeResponse, "raise_for_status", fake_raise)
    monkeypatch.setattr(requests, "get", fake_get)

    out = reviewer.fetch_pr_diff("o", "r", 5, "t")
    assert out == ""
    assert "Could not find PR #5" in capsys.readouterr().out


def test_fetch_pr_diff_401(monkeypatch, capsys):
    def fake_get(url, headers, timeout):
        return FakeResponse(status=401, text="unauth")

    def fake_raise(self):
        raise requests.exceptions.HTTPError(response=self)

    monkeypatch.setattr(FakeResponse, "raise_for_status", fake_raise)
    monkeypatch.setattr(requests, "get", fake_get)

    out = reviewer.fetch_pr_diff("o", "r", 9, "t")
    assert out == ""
    assert "Invalid GitHub Token" in capsys.readouterr().out


def test_fetch_pr_diff_other_http_error(monkeypatch, capsys):
    """Covers missing branch: status NOT 401, NOT 404, but still error."""
    def fake_get(url, headers, timeout):
        return FakeResponse(status=500, text="server error")

    def fake_raise(self):
        raise requests.exceptions.HTTPError(response=self)

    monkeypatch.setattr(FakeResponse, "raise_for_status", fake_raise)
    monkeypatch.setattr(requests, "get", fake_get)

    out = reviewer.fetch_pr_diff("o", "r", 3, "t")

    captured = capsys.readouterr()
    assert "GitHub API Error" in captured.out
    assert out == ""


def test_fetch_pr_diff_network_error(monkeypatch, capsys):
    def fake_get(url, headers, timeout):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "get", fake_get)

    out = reviewer.fetch_pr_diff("o", "r", 7, "t")
    assert out == ""
    assert "Unexpected network error" in capsys.readouterr().out


# ===========================================================
# post_review_comment tests
# ===========================================================

def test_post_review_comment_success(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(status=201, json_data={"done": True})
    monkeypatch.setattr(requests, "post", fake_post)

    out = reviewer.post_review_comment("o", "r", 2, "t", "hi")
    assert out == {"done": True}


def test_post_review_comment_api_error(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(status=400, json_data={"err": "bad"})
    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        reviewer.post_review_comment("o", "r", 3, "t", "body")


def test_post_review_comment_network(monkeypatch):
    def fake_post(url, headers, json, timeout):
        raise requests.exceptions.RequestException("net")
    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        reviewer.post_review_comment("o", "r", 4, "t", "msg")


# ===========================================================
# save_text_to_file tests
# ===========================================================

def test_save_text_to_file_success(tmp_path):
    p = tmp_path / "a.txt"
    reviewer.save_text_to_file(str(p), "hello")
    assert p.read_text(encoding="utf-8") == "hello"


def test_save_text_to_file_oserror(monkeypatch, capsys):
    def fake_open(*args, **kwargs):
        raise OSError("Disk Error")

    # FIX: patch builtins.open, not reviewer.open
    monkeypatch.setattr("builtins.open", fake_open)

    reviewer.save_text_to_file("aaa.txt", "hi")

    out = capsys.readouterr().out
    assert "Error saving file" in out
