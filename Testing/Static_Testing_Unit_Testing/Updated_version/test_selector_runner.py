import sys
import types
from pathlib import Path
from typing import List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))


def _bootstrap_selector_module_stub():
	if "selector" in sys.modules:
		return

	stub = types.ModuleType("selector")

	class _PlaceholderSelector:
		def load_state(self):
			pass

		def save_state(self):
			pass

	def _placeholder_process(*_, **__):
		return {}

	stub.IterativePromptSelector = _PlaceholderSelector
	stub.process_pr_with_selector = _placeholder_process
	sys.modules.setdefault("selector", stub)


_bootstrap_selector_module_stub()

import selector_runner

# Remove placeholder module to allow other tests to import the real selector module.
sys.modules.pop("selector", None)


def _install_selector_stub(monkeypatch) -> List[object]:
	instances = []

	class SelectorStub:
		def __init__(self):
			self.load_state_called = False
			self.save_state_called = False
			instances.append(self)

		def load_state(self):
			self.load_state_called = True

		def save_state(self):
			self.save_state_called = True

	monkeypatch.setattr(selector_runner, "IterativePromptSelector", SelectorStub)
	return instances


def _install_process_stub(monkeypatch, handler):
	monkeypatch.setattr(selector_runner, "process_pr_with_selector", handler)


# ===== Tests for run_selector() =====
def test_run_selector_with_load_previous_invokes_load_state_and_returns_all_results(monkeypatch, capsys):
	# Arrange
	selector_instances = _install_selector_stub(monkeypatch)
	process_calls = []

	def fake_process(selector_obj, pr_number, owner=None, repo=None, token=None, post_to_github=True):
		process_calls.append((selector_obj, pr_number, post_to_github))
		return {
			"pr_number": pr_number,
			"chosen_prompt": f"prompt-{pr_number}",
			"review": f"review content {pr_number}",
			"score": float(pr_number) / 10.0,
			"features": {"sample": pr_number},
		}

	_install_process_stub(monkeypatch, fake_process)

	# Act
	results, selector = selector_runner.run_selector([11, 12], load_previous=True, post_to_github=True)

	# Assert
	assert selector_instances[0].load_state_called is True
	assert selector_instances[0].save_state_called is True
	assert selector is selector_instances[0]
	assert results == [
		{
			"pr_number": 11,
			"chosen_prompt": "prompt-11",
			"review": "review content 11",
			"score": 1.1,
			"features": {"sample": 11},
		},
		{
			"pr_number": 12,
			"chosen_prompt": "prompt-12",
			"review": "review content 12",
			"score": 1.2,
			"features": {"sample": 12},
		},
	]
	assert process_calls == [
		(selector, 11, True),
		(selector, 12, True),
	]
	out = capsys.readouterr().out
	assert "🤖 AI REVIEW FOR PR #11 (Prompt: prompt-11)" in out
	assert "PR #12: prompt-12 -> Score: 1.2" in out
	assert "FINAL ITERATIVE SELECTOR REPORT" in out


def test_run_selector_without_load_previous_skips_loading_state(monkeypatch):
	# Arrange
	selector_instances = _install_selector_stub(monkeypatch)

	def fake_process(selector_obj, pr_number, owner=None, repo=None, token=None, post_to_github=True):
		return {
			"pr_number": pr_number,
			"chosen_prompt": "prompt",
			"review": "review",
			"score": 7.0,
			"features": {},
		}

	_install_process_stub(monkeypatch, fake_process)

	# Act
	results, selector = selector_runner.run_selector([21], load_previous=False)

	# Assert
	assert selector_instances[0].load_state_called is False
	assert selector_instances[0].save_state_called is True
	assert selector is selector_instances[0]
	assert results == [
		{
			"pr_number": 21,
			"chosen_prompt": "prompt",
			"review": "review",
			"score": 7.0,
			"features": {},
		}
	]


def test_run_selector_continues_after_processing_failure(monkeypatch, capsys):
	# Arrange
	selector_instances = _install_selector_stub(monkeypatch)

	def flaky_process(selector_obj, pr_number, owner=None, repo=None, token=None, post_to_github=True):
		if pr_number == 7:
			raise RuntimeError("simulated failure")
		return {
			"pr_number": pr_number,
			"chosen_prompt": f"prompt-{pr_number}",
			"review": f"review content {pr_number}",
			"score": 9.5,
			"features": {"sample": pr_number},
		}

	_install_process_stub(monkeypatch, flaky_process)

	# Act
	results, selector = selector_runner.run_selector([7, 8], load_previous=True)

	# Assert
	assert selector_instances[0].load_state_called is True
	assert selector_instances[0].save_state_called is True
	assert selector is selector_instances[0]
	assert results == [
		{
			"pr_number": 8,
			"chosen_prompt": "prompt-8",
			"review": "review content 8",
			"score": 9.5,
			"features": {"sample": 8},
		}
	]
	out = capsys.readouterr().out
	assert "Failed to process PR #7: simulated failure" in out
	assert "PR #8: prompt-8 -> Score: 9.5" in out


def test_run_selector_with_no_prs_returns_empty_results(monkeypatch):
	# Arrange
	selector_instances = _install_selector_stub(monkeypatch)
	calls = []

	def counting_process(selector_obj, pr_number, owner=None, repo=None, token=None, post_to_github=True):
		calls.append(pr_number)
		return {}

	_install_process_stub(monkeypatch, counting_process)

	# Act
	results, selector = selector_runner.run_selector([], load_previous=False)

	# Assert
	assert selector_instances[0].load_state_called is False
	assert selector_instances[0].save_state_called is True
	assert selector is selector_instances[0]
	assert calls == []
	assert results == []


def test_run_selector_raises_when_save_state_fails(monkeypatch):
	# Arrange
	failure_message = "unable to persist state"

	class FailingSelector:
		def __init__(self):
			self.load_state_called = False

		def load_state(self):
			self.load_state_called = True

		def save_state(self):
			raise IOError(failure_message)

	monkeypatch.setattr(selector_runner, "IterativePromptSelector", FailingSelector)

	def simple_process(selector_obj, pr_number, owner=None, repo=None, token=None, post_to_github=True):
		return {
			"pr_number": pr_number,
			"chosen_prompt": "prompt",
			"review": "review",
			"score": 1.0,
			"features": {},
		}

	_install_process_stub(monkeypatch, simple_process)

	# Act / Assert
	with pytest.raises(IOError, match=failure_message):
		selector_runner.run_selector([1], load_previous=False)
