import sys
import types
import json
from unittest.mock import MagicMock, patch
import pytest

# ================================================================
# PREVENT REAL IMPORT OF reviewer.py and utils.py
# ================================================================

fake_reviewer = types.ModuleType("reviewer")
fake_reviewer.llm = MagicMock()
sys.modules["reviewer"] = fake_reviewer

fake_utils = types.ModuleType("utils")
fake_utils.safe_truncate = lambda x, n: x[:n]   # simple predictable truncation
sys.modules["utils"] = fake_utils

# ================================================================
# NOW import module-under-test
# ================================================================
from accuracy_checker import meta_evaluate, heuristic_metrics


# ================================================================
# FIXTURES FOR meta_evaluate
# ================================================================

@pytest.fixture
def mock_chain():
    """Patch the evaluator chain completely."""
    with patch("accuracy_checker.evaluator_prompt") as mock_prompt:
        chain = MagicMock()
        # evaluator_prompt | llm
        mock_prompt.__or__.return_value = chain
        # chain | StrOutputParser
        chain.__or__.return_value = chain
        yield chain


# ================================================================
# meta_evaluate tests
# ================================================================

def test_meta_evaluate_valid_json(mock_chain):
    """Full valid JSON → parsed directly."""
    mock_chain.invoke.return_value = json.dumps({
        "clarity": 7,
        "usefulness": 8,
        "depth": 6,
        "actionability": 9,
        "positivity": 8,
        "explain": "ok"
    })

    parsed, raw = meta_evaluate("d", "r", "s", "c")

    assert isinstance(parsed, dict)
    assert parsed["clarity"] == 7
    assert "ok" in parsed["explain"]


def test_meta_evaluate_json_wrapped_in_noise(mock_chain):
    """JSON inside text → regex fallback path."""
    mock_chain.invoke.return_value = "spam {\"clarity\":5,\"usefulness\":6,\"depth\":7,\"actionability\":8,\"positivity\":9,\"explain\":\"fine\"} eggs"

    parsed, raw = meta_evaluate("d", "r", "s", "c")
    assert parsed["clarity"] == 5
    assert parsed["positivity"] == 9


def test_meta_evaluate_invalid_json_inside_braces(mock_chain):
    """JSON-like braces but invalid → second parsing fails."""
    mock_chain.invoke.return_value = "{invalid json}"

    parsed, raw = meta_evaluate("d", "r", "s", "c")
    assert "could not parse JSON" in parsed["error"]


def test_meta_evaluate_no_json_anywhere(mock_chain):
    """No braces → final fallback."""
    mock_chain.invoke.return_value = "completely useless text"

    parsed, raw = meta_evaluate("d", "r", "s", "c")
    assert parsed["error"] == "no JSON in evaluator output"


def test_meta_evaluate_llm_exception(mock_chain):
    """Exception in chain.invoke → caught by first try/except."""
    mock_chain.invoke.side_effect = RuntimeError("fail")

    parsed, raw = meta_evaluate("D", "R", "S", "C")
    assert parsed["error"].startswith("evaluator invoke failed")
    assert raw is None


def test_meta_evaluate_truncation_called_properly():
    """Ensure safe_truncate is used with correct limits."""
    with patch("accuracy_checker.safe_truncate", side_effect=lambda x, n: x[:n]) as trunc, \
         patch("accuracy_checker.evaluator_prompt") as mock_prompt:

        chain = MagicMock()
        mock_prompt.__or__.return_value = chain
        chain.__or__.return_value = chain
        chain.invoke.return_value = "{\"clarity\":1,\"usefulness\":1,\"depth\":1,\"actionability\":1,\"positivity\":1,\"explain\":\"x\"}"

        meta_evaluate("A"*5000, "B"*5000, "C"*3000, "D"*3000)

        assert trunc.call_count == 4
        trunc.assert_any_call("A"*5000, 4000)
        trunc.assert_any_call("B"*5000, 4000)
        trunc.assert_any_call("C"*3000, 2000)
        trunc.assert_any_call("D"*3000, 2000)


# ================================================================
# heuristic_metrics tests
# ================================================================

def test_heuristic_basic_counts():
    text = "Hello\n- item\nAnother line"
    h = heuristic_metrics(text)
    assert h["length_chars"] == len(text)
    assert h["length_words"] == len(text.split())
    assert h["bullet_points"] == 1


def test_heuristic_bug_detection():
    h = heuristic_metrics("This has a bug, error, and issue.")
    assert h["mentions_bug"] is True


def test_heuristic_suggest_detection():
    h = heuristic_metrics("I suggest you consider fixing this.")
    assert h["mentions_suggest"] is True


def test_heuristic_no_keywords():
    h = heuristic_metrics("This contains nothing special.")
    assert not h["mentions_bug"]
    assert not h["mentions_suggest"]


def test_heuristic_section_presence_all():
    text = (
        "Summary section\n"
        "Bugs found\n"
        "Errors listed\n"
        "Code Quality improved\n"
        "Suggestions here\n"
        "Improvements made\n"
        "Tests added\n"
        "Positive note\n"
        "Final Review done\n"
    )
    h = heuristic_metrics(text)
    assert all(h["sections_presence"].values())


def test_heuristic_section_presence_none():
    h = heuristic_metrics("No sections here.")
    assert all(v is False for v in h["sections_presence"].values())


def test_heuristic_empty_text():
    h = heuristic_metrics("")
    assert h["length_chars"] == 0
    assert h["length_words"] == 0
    assert h["bullet_points"] == 0
    assert all(v is False for v in h["sections_presence"].values())


def test_heuristic_multiple_bullet_styles():
    h = heuristic_metrics("- a\n* b\n• c")
    assert h["bullet_points"] == 3
