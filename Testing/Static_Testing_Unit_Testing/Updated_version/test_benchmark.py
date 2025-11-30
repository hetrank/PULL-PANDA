

"""Pytest unit tests for `benchmark.py`.

All external dependencies are mocked so tests do not perform real I/O or network calls.
Each test follows Arrange-Act-Assert and has a descriptive name.
"""

import io
import os
import sys
import types
import builtins
import importlib.util
import pytest
from unittest.mock import mock_open


def _load_benchmark_module_with_dummy_deps():
    """Load the `benchmark.py` module from the same directory as this test file,
    injecting lightweight dummy modules for imports so import-time side effects are avoided.
    """
    dirpath = os.path.dirname(__file__)
    path = os.path.join(dirpath, "benchmark.py")

    # Prepare dummy modules that `benchmark.py` imports from
    dummy_core = types.ModuleType("core")
    dummy_core.fetch_pr_diff = lambda *a, **k: ""
    dummy_core.run_prompt = lambda *a, **k: ("", "", "")
    dummy_core.save_text_to_file = lambda *a, **k: None
    sys.modules.setdefault("core", dummy_core)

    dummy_prompts = types.ModuleType("prompts")
    dummy_prompts.get_prompts = lambda: {}
    sys.modules.setdefault("prompts", dummy_prompts)

    dummy_eval = types.ModuleType("evaluation")
    dummy_eval.heuristic_metrics = lambda *a, **k: {}
    dummy_eval.meta_evaluate = lambda *a, **k: ({}, "")
    dummy_eval.combine_final_score = lambda *a, **k: 0
    dummy_eval.heuristics_to_score = lambda *a, **k: 0
    sys.modules.setdefault("evaluation", dummy_eval)

    dummy_config = types.ModuleType("config")
    dummy_config.OWNER = "owner"
    dummy_config.REPO = "repo"
    dummy_config.GITHUB_TOKEN = "token"
    sys.modules.setdefault("config", dummy_config)

    spec = importlib.util.spec_from_file_location("benchmark", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===== Tests for benchmark_all_prompts() =====


def test_benchmark_single_prompt_successful_run_returns_expected_result_and_writes_files(monkeypatch):
    """Arrange: one prompt; act: run benchmark_all_prompts; assert: result fields are filled and md saved.

    AAA: Uses monkeypatch to stub all external functions and time values.
    """
    # Arrange
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"promptA": "do something"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda owner, repo, pr, token: "DIFF_CONTENT")
    monkeypatch.setattr(mod, "run_prompt", lambda prompt, diff: ("REVIEW_TEXT", "STATIC_OUT", "CTX"))
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {"h1": 1})
    monkeypatch.setattr(mod, "meta_evaluate", lambda diff, review, static_output=None, context=None: ({"meta": 10}, "raw_meta"))
    monkeypatch.setattr(
        mod,
        "combine_final_score",
        lambda meta_parsed, heur: (10, meta_parsed, 5)
    )

    # deterministic times
    times = [100.0, 100.42]
    monkeypatch.setattr(mod.time, "time", lambda: times.pop(0))
    sleep_calls = []
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleep_calls.append(s))

    # capture markdown saves
    saved_md = {}
    monkeypatch.setattr(mod, "save_text_to_file", lambda fname, content: saved_md.setdefault(fname, content))

    # capture CSV writing via mock_open (no real FS calls)
    m = mock_open()
    monkeypatch.setattr(builtins, "open", m, raising=False)

    # Act
    results = mod.benchmark_all_prompts(pr_number=7, post_to_github=False)

    # Assert
    assert isinstance(results, list) and len(results) == 1
    r = results[0]
    assert r["prompt"] == "promptA"
    assert r["review"] == "REVIEW_TEXT"
    assert r["static_output"] == "STATIC_OUT"
    assert r["retrieved_context"] == "CTX"
    assert r["final_score"] == 10
    assert r["heur_score"] == 5
    # md file saved and mentions PR number
    md_name = f"review_reports_all_prompts_PR7.md"
    assert md_name in saved_md
    assert ("PR 7" in saved_md[md_name]) or ("PR7" in saved_md[md_name])
    # sleep called with the pause used by the runner
    assert 0.2 in sleep_calls


def test_benchmark_run_prompt_exception_is_caught_and_reported(monkeypatch):
    """Arrange: run_prompt raises; Act: run benchmark; Assert: returned review contains error and defaults used.

    This ensures exceptions from prompt invocation do not crash the runner.
    """
    # Arrange
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"p_raise": "will fail"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda owner, repo, pr, token: "DD")

    def run_prompt_fail(prompt, diff):
        raise ValueError("boom")

    monkeypatch.setattr(mod, "run_prompt", run_prompt_fail)
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {})

    def meta_eval_check(diff, review, static_output=None, context=None):
        # When run_prompt fails, runner substitutes "N/A" for static_output and context
        assert static_output == "N/A"
        assert context == "N/A"
        return ({"error": "meta failed"}, "rawerr")

    monkeypatch.setattr(mod, "meta_evaluate", meta_eval_check)
    monkeypatch.setattr(
        mod,
        "combine_final_score",
        lambda meta_parsed, heur: (0, None, 0)
    )

    monkeypatch.setattr(mod.time, "time", lambda: 1.0)
    monkeypatch.setattr(mod.time, "sleep", lambda _x: None)

    monkeypatch.setattr(builtins, "open", mock_open(), raising=False)
    monkeypatch.setattr(mod, "save_text_to_file", lambda f, c: None)

    # Act
    results = mod.benchmark_all_prompts(pr_number=99)

    # Assert
    assert len(results) == 1
    r = results[0]
    assert r["review"].startswith("ERROR: prompt invoke failed")
    assert r["static_output"] == "N/A"
    assert r["retrieved_context"] == "N/A"
    assert r["meta_score"] == "N/A"


def test_benchmark_multiple_prompts_results_include_all_and_sorted_by_final_score(monkeypatch):
    """Arrange: three prompts; Act: run benchmark; Assert: all prompts present and sorted by numeric final_score.

    Also checks final_score values are taken from combine_final_score mapping.
    """
    # Arrange
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"A": "a", "B": "b", "C": "c"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda owner, repo, pr, token: "X")
    monkeypatch.setattr(mod, "run_prompt", lambda p, d: (f"rev_{p}", f"stat_{p}", f"ctx_{p}"))
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {})

    # Record the review string when meta_evaluate is called so combine_final_score
    # can deterministically return a score based on that recorded value.
    def meta_eval_and_record(diff, review, static_output=None, context=None):
        mod._last_review = review
        return ({}, "raw")

    monkeypatch.setattr(mod, "meta_evaluate", meta_eval_and_record)

    def combine_scores(meta_parsed, heur):
        rev = getattr(mod, "_last_review", "")
        score = {"rev_A": 30, "rev_B": 10, "rev_C": 20}.get(rev, 0)
        return (score, None, score / 10)

    monkeypatch.setattr(mod, "combine_final_score", combine_scores)

    # deterministic time values
    tvals = [0.0] * 6
    monkeypatch.setattr(mod.time, "time", lambda: tvals.pop(0))
    monkeypatch.setattr(mod.time, "sleep", lambda _x: None)

    monkeypatch.setattr(builtins, "open", mock_open(), raising=False)
    monkeypatch.setattr(mod, "save_text_to_file", lambda f, c: None)

    # Act
    results = mod.benchmark_all_prompts(pr_number=3)

    # Assert: all prompts present
    mapping = {r["prompt"]: r["final_score"] for r in results}
    assert set(mapping.keys()) == {"A", "B", "C"}

    # And ensure the list is sorted by numeric final_score ascending (treat non-numeric as 0)
    final_scores = [r["final_score"] if isinstance(r["final_score"], (int, float)) else 0 for r in results]
    assert final_scores == sorted(final_scores)


def test_benchmark_handles_non_dict_meta_parsed_treated_as_no_meta(monkeypatch):
    """Arrange: meta_evaluate returns a non-dict; Act: run benchmark; Assert: meta_score becomes 'N/A'.
    """
    # Arrange
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"P": "p"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda *a, **k: "D")
    monkeypatch.setattr(mod, "run_prompt", lambda p, d: ("rev", "stat", "ctx"))
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {})

    # meta_evaluate returns a string rather than dict
    monkeypatch.setattr(mod, "meta_evaluate", lambda diff, review, static_output=None, context=None: ("not-a-dict", "raw"))
    monkeypatch.setattr(
        mod,
        "combine_final_score",
        lambda meta_parsed, heur: (5, None, 1)
    )

    monkeypatch.setattr(mod.time, "time", lambda: 0.0)
    monkeypatch.setattr(mod.time, "sleep", lambda _x: None)
    monkeypatch.setattr(builtins, "open", mock_open(), raising=False)
    monkeypatch.setattr(mod, "save_text_to_file", lambda f, c: None)

    # Act
    results = mod.benchmark_all_prompts(pr_number=4)

    # Assert
    assert len(results) == 1
    r = results[0]
    assert r["meta_score"] == "N/A"
    assert r["final_score"] == 5


def test_benchmark_non_numeric_final_scores_are_sorted_as_zero(monkeypatch):
    """Arrange: combine_final_score returns non-numeric values for some prompts; Act: run; Assert: sorting treats non-numeric as 0.
    """
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"p1": "a", "p2": "b"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda *a, **k: "D")
    monkeypatch.setattr(mod, "run_prompt", lambda p, d: (f"rev_{p}", "s", "c"))
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {})

    def meta_eval(diff, review, static_output=None, context=None):
        return ({"id": review}, "")

    monkeypatch.setattr(mod, "meta_evaluate", meta_eval)

    # produce non-numeric for p1 and numeric for p2
    def combine(meta_parsed, heur):
        if meta_parsed.get("id") == "rev_a":
            return ("NaN", None, 0)
        return (5, None, 0)

    monkeypatch.setattr(mod, "combine_final_score", combine)

    tvals = [0.0] * 4
    monkeypatch.setattr(mod.time, "time", lambda: tvals.pop(0))
    monkeypatch.setattr(mod.time, "sleep", lambda _x: None)
    monkeypatch.setattr(builtins, "open", mock_open(), raising=False)
    monkeypatch.setattr(mod, "save_text_to_file", lambda f, c: None)

    # Act
    results = mod.benchmark_all_prompts(pr_number=5)

    # Assert: non-numeric treated as 0 when sorting; so it should come before numeric values
    finals = [r["final_score"] for r in results]
    # At least one non-numeric present
    assert any(not isinstance(x, (int, float)) for x in finals)
    # Sorting uses numeric when possible; ensure list is non-decreasing when mapping non-numeric to 0
    numeric_equiv = [x if isinstance(x, (int, float)) else 0 for x in finals]
    assert numeric_equiv == sorted(numeric_equiv)


def test_benchmark_save_text_to_file_raising_propagates_exception(monkeypatch):
    """Arrange: make save_text_to_file raise; Act+Assert: ensure the exception propagates from the runner.
    """
    mod = _load_benchmark_module_with_dummy_deps()
    monkeypatch.setattr(mod, "get_prompts", lambda: {"p": "x"})
    monkeypatch.setattr(mod, "fetch_pr_diff", lambda *a, **k: "D")
    monkeypatch.setattr(mod, "run_prompt", lambda p, d: ("r", "s", "c"))
    monkeypatch.setattr(mod, "heuristic_metrics", lambda review: {})
    monkeypatch.setattr(mod, "meta_evaluate", lambda diff, review, static_output=None, context=None: ({}, ""))
    monkeypatch.setattr(
        mod,
        "combine_final_score",
        lambda meta_parsed, heur: (1, None, 0)
    )

    monkeypatch.setattr(mod.time, "time", lambda: 0.0)
    monkeypatch.setattr(mod.time, "sleep", lambda _x: None)

    # Make save_text_to_file raise so the runner fails when trying to save md summary
    def raise_on_save(fname, content):
        raise RuntimeError("disk full")
    monkeypatch.setattr(mod, "save_text_to_file", raise_on_save)

    monkeypatch.setattr(builtins, "open", mock_open(), raising=False)

    with pytest.raises(RuntimeError):
        # Act: this should raise when save_text_to_file is invoked
        mod.benchmark_all_prompts(pr_number=11)
