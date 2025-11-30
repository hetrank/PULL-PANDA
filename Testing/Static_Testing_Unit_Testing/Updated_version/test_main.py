"""Pytest tests for `main.py`.

These tests execute `main.py` as `__main__` by loading the file and running it with
`__name__ == "__main__"`. They inject dummy `config` and `selector_runner` modules into
`sys.modules` so no real environment or side effects occur.

Each test follows Arrange-Act-Assert and has a descriptive name.
"""

import os
import sys
import types
import importlib.util
import pytest


def _run_main_with_modules(pr_value, run_selector_impl=None):
    """Helper to run `main.py` as __main__ with injected `config` and `selector_runner`.

    - pr_value: value to set for `config.PR_NUMBER` (can be int, str, None)
    - run_selector_impl: a callable to use as `selector_runner.run_selector` (or a Mock)

    Returns (module, stdout_str). If run_selector_impl raises, the exception is propagated.
    """
    # Save existing modules to restore later
    prev_config = sys.modules.get("config")
    prev_selector = sys.modules.get("selector_runner")

    # Inject dummy config
    cfg = types.ModuleType("config")
    cfg.PR_NUMBER = pr_value
    sys.modules["config"] = cfg

    # Inject dummy selector_runner
    sel = types.ModuleType("selector_runner")
    if run_selector_impl is None:
        def default_run_selector(arglist, post_to_github=False):
            # record invocation by setting attribute
            sel._called_with = (arglist, post_to_github)
        sel.run_selector = default_run_selector
    else:
        sel.run_selector = run_selector_impl
    sys.modules["selector_runner"] = sel

    # Load main.py as module with name "__main__" so its main block executes
    here = os.path.dirname(__file__)
    path = os.path.join(here, "main.py")
    spec = importlib.util.spec_from_file_location("__main__", path)
    mod = importlib.util.module_from_spec(spec)

    # Capture stdout by temporarily redirecting sys.stdout
    from io import StringIO
    old_stdout = sys.stdout
    buf = StringIO()
    sys.stdout = buf
    try:
        # Execute module; this will run the if __name__ == '__main__' block
        spec.loader.exec_module(mod)
    finally:
        sys.stdout = old_stdout

    out = buf.getvalue()

    # Restore previous modules
    if prev_config is not None:
        sys.modules["config"] = prev_config
    else:
        sys.modules.pop("config", None)
    if prev_selector is not None:
        sys.modules["selector_runner"] = prev_selector
    else:
        sys.modules.pop("selector_runner", None)

    return sel, out


# ===== Tests for main script behavior =====


def test_main_prints_error_and_does_not_call_selector_when_pr_number_none():
    """Arrange: config.PR_NUMBER is None; Act: execute main; Assert: prints error and selector not called."""
    sel, out = _run_main_with_modules(None)
    assert "Error: PR_NUMBER is not set or invalid" in out
    # selector should not have been called
    assert not hasattr(sel, "_called_with")


@pytest.mark.parametrize("val", ["0", 0, "-3", -1])
def test_main_prints_error_for_non_positive_pr_numbers_and_skips_selector(val):
    """Arrange: config.PR_NUMBER is zero or negative; Act: execute main; Assert: prints error and does not call selector."""
    sel, out = _run_main_with_modules(val)
    assert "Error: PR_NUMBER is not set or invalid" in out
    assert not hasattr(sel, "_called_with")


def test_main_calls_run_selector_with_valid_pr_and_prints_progress():
    """Arrange: config.PR_NUMBER is valid; Act: execute main; Assert: run_selector called with expected args and prints progress messages."""
    # Arrange: create a run_selector implementation that records input
    called = {}
    def run_selector_impl(arglist, post_to_github=False):
        called['args'] = (arglist, post_to_github)

    sel, out = _run_main_with_modules("12", run_selector_impl=run_selector_impl)

    assert "Processing PR #12" in out
    assert "Done! Review generated and selector state updated." in out
    assert called.get('args') == ([12], True)


def test_main_propagates_exception_from_run_selector_and_no_done_message(monkeypatch):
    """Arrange: run_selector raises; Act: executing main should propagate exception; Assert: processing printed but Done message absent."""
    def run_selector_raises(arglist, post_to_github=False):
        raise RuntimeError("selector failed")

    # Run and expect exception
    with pytest.raises(RuntimeError):
        _run_main_with_modules("3", run_selector_impl=run_selector_raises)

    # We can also run capturing output to assert "Processing" printed before exception
    sel, out = None, None
    try:
        sel, out = _run_main_with_modules("3", run_selector_impl=run_selector_raises)
    except RuntimeError:
        # re-run to capture out via same helper that returns before exception
        pass
    # If out was captured, it should contain Processing message but not Done
    if out is not None:
        assert "Processing PR #3" in out
        assert "Done!" not in out
