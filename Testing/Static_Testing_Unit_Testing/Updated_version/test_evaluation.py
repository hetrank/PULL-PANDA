"""Pytest tests for `evaluation.py`.

Covers heuristic helpers, meta_evaluate parsing and error handling, and scoring functions.
All external dependencies (LLM chain, safe_truncate) are mocked so there are no network or file I/O calls.

Each test follows Arrange-Act-Assert (AAA) and has a descriptive function name.
"""

import os
import sys
import types
import importlib.util
import re
import pytest


def _load_evaluation_module_with_dummy_deps():
    """Import `evaluation.py` from the same directory, injecting dummy dependencies.

    We inject a dummy `utils.safe_truncate` if needed and ensure a fresh import each time.
    """
    sys.modules.pop("evaluation", None)

    # Provide a dummy utils module with safe_truncate
    utils = types.ModuleType("utils")
    utils.safe_truncate = lambda s, n: (s if len(s) <= n else s[:n])
    sys.modules["utils"] = utils

    # Provide a dummy langchain_core.prompts and output_parsers to avoid import errors
    lc_prompts = types.ModuleType("langchain_core.prompts")
    lc_prompts.ChatPromptTemplate = types.SimpleNamespace(from_messages=lambda msgs: None)
    sys.modules["langchain_core.prompts"] = lc_prompts
    lc_parsers = types.ModuleType("langchain_core.output_parsers")
    lc_parsers.StrOutputParser = lambda: None
    sys.modules["langchain_core.output_parsers"] = lc_parsers

    # Provide a dummy core.llm (not used because we'll mock evaluator_prompt chaining)
    core = types.ModuleType("core")
    core.llm = object()
    sys.modules["core"] = core

    here = os.path.dirname(__file__)
    path = os.path.join(here, "evaluation.py")
    spec = importlib.util.spec_from_file_location("evaluation", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== Tests for count_bullets() =====


def test_count_bullets_counts_various_bullet_characters_and_spacing():
    # Arrange
    mod = _load_evaluation_module_with_dummy_deps()
    text = "- first\n  * second\n• third\n not a bullet\n    - indented"

    # Act
    cnt = mod.count_bullets(text)

    # Assert (should count 4 bullet lines)
    assert cnt == 4


def test_count_bullets_empty_string_returns_zero():
    mod = _load_evaluation_module_with_dummy_deps()
    assert mod.count_bullets("") == 0


# ===== Tests for has_sections() =====


def test_has_sections_detects_sections_case_insensitively():
    mod = _load_evaluation_module_with_dummy_deps()
    text = "Summary:\nThis is good.\nBUGS: none\nImprovements suggested"
    sections = ["summary", "bugs", "improvements", "missing"]

    res = mod.has_sections(text, sections)

    assert res["summary"] is True
    assert res["bugs"] is True
    assert res["improvements"] is True
    assert res["missing"] is False


# ===== Tests for heuristic_metrics() =====


def test_heuristic_metrics_populates_expected_fields_and_section_presence():
    mod = _load_evaluation_module_with_dummy_deps()
    review = "Summary:\n- fix bug\nI suggest we consider tests.\nThis may be an issue."

    heur = mod.heuristic_metrics(review)

    # Basic numeric fields
    assert heur["length_chars"] == len(review)
    assert heur["length_words"] == len(review.split())
    assert heur["bullet_points"] == 1

    # keyword detections
    assert heur["mentions_bug"] is True
    assert heur["mentions_suggest"] is True

    # sections_presence contains expected keys
    assert isinstance(heur["sections_presence"], dict)
    assert heur["sections_presence"].get("summary") is True


def test_heuristic_metrics_empty_review_returns_zero_like_values():
    mod = _load_evaluation_module_with_dummy_deps()
    heur = mod.heuristic_metrics("")
    assert heur["length_chars"] == 0
    assert heur["length_words"] == 0
    assert heur["bullet_points"] == 0
    assert heur["mentions_bug"] is False


# ===== Tests for meta_evaluate() =====


def _make_chain_stub(return_text=None, raise_exc=False):
    """Helper to create a stub that simulates evaluator_prompt | llm | parser chain."""

    class FinalChain:
        def invoke(self, kwargs):
            if raise_exc:
                raise RuntimeError("invoke failed")
            return return_text

    class Mid:
        def __init__(self):
            self.final = FinalChain()
        def __or__(self, other):
            return self.final

    class PromptStub:
        def __or__(self, other):
            return Mid()

    return PromptStub()


def test_meta_evaluate_returns_parsed_json_when_chain_returns_valid_json(monkeypatch):
    mod = _load_evaluation_module_with_dummy_deps()

    raw = '{"clarity":8, "usefulness":7, "depth":6, "actionability":5, "positivity":4, "explain":"ok"}'
    chain_stub = _make_chain_stub(return_text=raw)
    # Monkeypatch evaluator_prompt to our stub that supports | operations
    monkeypatch.setattr(mod, "evaluator_prompt", chain_stub)

    parsed, out = mod.meta_evaluate("D", "R", "S", "C")
    assert parsed["clarity"] == 8
    assert out.strip() == raw


def test_meta_evaluate_extracts_json_inside_text_with_noise(monkeypatch):
    mod = _load_evaluation_module_with_dummy_deps()
    raw = "Some heading\nRESULT:\n{" + '"clarity":9, "usefulness":9, "depth":9, "actionability":9, "positivity":9, "explain":"x"}'
    # put JSON inside extra text
    noisy = "foo before\n" + raw + "\ntrailing"
    chain_stub = _make_chain_stub(return_text=noisy)
    monkeypatch.setattr(mod, "evaluator_prompt", chain_stub)

    parsed, out = mod.meta_evaluate("d", "r", "s", "c")
    assert isinstance(parsed, dict)
    assert parsed.get("clarity") == 9


def test_meta_evaluate_handles_malformed_json_inside_braces(monkeypatch):
    mod = _load_evaluation_module_with_dummy_deps()
    raw = "prefix { not: json, } suffix"
    chain_stub = _make_chain_stub(return_text=raw)
    monkeypatch.setattr(mod, "evaluator_prompt", chain_stub)

    parsed, out = mod.meta_evaluate("d", "r", "s", "c")
    assert isinstance(parsed, dict)
    assert parsed.get("error") == "could not parse JSON"
    assert parsed.get("raw") == raw


def test_meta_evaluate_handles_no_json_in_output(monkeypatch):
    mod = _load_evaluation_module_with_dummy_deps()
    chain_stub = _make_chain_stub(return_text="no json here")
    monkeypatch.setattr(mod, "evaluator_prompt", chain_stub)

    parsed, out = mod.meta_evaluate("d", "r", "s", "c")
    assert parsed.get("error") == "no JSON in evaluator output"
    assert parsed.get("raw") == "no json here"


def test_meta_evaluate_handles_chain_invoke_exception(monkeypatch):
    mod = _load_evaluation_module_with_dummy_deps()
    chain_stub = _make_chain_stub(return_text=None, raise_exc=True)
    monkeypatch.setattr(mod, "evaluator_prompt", chain_stub)

    parsed, out = mod.meta_evaluate("d", "r", "s", "c")
    assert "error" in parsed and out is None


# ===== Tests for meta_to_score() =====


def test_meta_to_score_computes_weighted_average_and_handles_missing_keys():
    mod = _load_evaluation_module_with_dummy_deps()
    meta = {"clarity": 8, "usefulness": 6, "depth": 7, "actionability": 9, "positivity": 5}
    score = mod.meta_to_score(meta)
    assert isinstance(score, float)
    # manual compute sanity check (between 1 and 10)
    assert 0 <= score <= 10

    # missing keys treated as neutral 5
    partial = {"clarity": 10}
    s2 = mod.meta_to_score(partial)
    assert isinstance(s2, float)

    # error or non-dict returns None
    assert mod.meta_to_score({"error":"x"}) is None
    assert mod.meta_to_score("not a dict") is None


# ===== Tests for heuristics_to_score() =====


def test_heuristics_to_score_short_text_low_scores_and_bonuses():
    mod = _load_evaluation_module_with_dummy_deps()
    heur = {
        "sections_presence": {"a": False, "b": False},
        "bullet_points": 1,
        "length_words": 40,
        "mentions_bug": True,
        "mentions_suggest": False,
    }
    score = mod.heuristics_to_score(heur)
    assert isinstance(score, float)
    # ensure bug bonus applied increases score slightly
    heur_no_bug = dict(heur)
    heur_no_bug["mentions_bug"] = False
    score_nb = mod.heuristics_to_score(heur_no_bug)
    assert score >= score_nb


def test_heuristics_to_score_ideal_length_sections_and_bullets_gives_high_score():
    mod = _load_evaluation_module_with_dummy_deps()
    heur = {
        "sections_presence": {f"s{i}": True for i in range(10)},
        "bullet_points": 10,
        "length_words": 200,
        "mentions_bug": True,
        "mentions_suggest": True,
    }
    score = mod.heuristics_to_score(heur)
    assert score > 7.0


def test_heuristics_to_score_very_large_length_clamps_to_zero_contribution():
    mod = _load_evaluation_module_with_dummy_deps()
    heur = {"sections_presence": {}, "bullet_points": 0, "length_words": 5000, "mentions_bug": False, "mentions_suggest": False}
    score = mod.heuristics_to_score(heur)
    assert score >= 0.0


# ===== Tests for combine_final_score() =====


def test_combine_final_score_uses_meta_when_available_else_heuristics_only():
    mod = _load_evaluation_module_with_dummy_deps()
    meta = {"clarity": 8, "usefulness": 8, "depth": 8, "actionability": 8, "positivity": 8}
    heur = {"sections_presence": {}, "bullet_points": 0, "length_words": 100}
    final, meta_score, heur_score = mod.combine_final_score(meta, heur)
    assert isinstance(final, float)
    assert isinstance(meta_score, float)
    assert isinstance(heur_score, float)

    # When meta parsing failed -> meta_score None -> final equals heur_score
    final2, meta2, heur2 = mod.combine_final_score({"error":"x"}, heur)
    assert meta2 is None
    assert final2 == heur2
