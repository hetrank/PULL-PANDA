"""Pytest tests for `prompts.py`.

All external dependencies (LangChain prompt template) are mocked to avoid importing the real package.
Tests follow Arrange-Act-Assert and cover normal flows plus error propagation.
"""

import os
import sys
import types
import importlib.util
import copy
import pytest


def _import_prompts_module(raise_on_from_messages=False):
	"""Import `prompts.py` from this directory with a stubbed ChatPromptTemplate.

	Parameters
	----------
	raise_on_from_messages: bool
		When True, the stub ChatPromptTemplate.from_messages raises RuntimeError.
	"""
	sys.modules.pop("prompts", None)

	class DummyPrompt:
		def __init__(self, messages):
			# store an immutable copy for later assertions
			self.messages = tuple(copy.deepcopy(messages))

	class ChatPromptTemplate:
		@classmethod
		def from_messages(cls, messages):
			if raise_on_from_messages:
				raise RuntimeError("ChatPromptTemplate failure")
			return DummyPrompt(messages)

	lc_prompts = types.ModuleType("langchain_core.prompts")
	lc_prompts.ChatPromptTemplate = ChatPromptTemplate
	sys.modules["langchain_core.prompts"] = lc_prompts

	here = os.path.dirname(__file__)
	path = os.path.join(here, "prompts.py")
	spec = importlib.util.spec_from_file_location("prompts", path)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


# ===== Tests for get_prompts() =====


def test_get_prompts_returns_expected_keys_and_prompt_objects():
	"""Arrange: import module with stub template; Act: call get_prompts; Assert: expected keys and types."""
	# Arrange
	mod = _import_prompts_module()

	# Act
	prompts = mod.get_prompts()

	# Assert
	expected_keys = {"Zero-shot", "Few-shot", "Chain-of-Thought", "Tree-of-Thought", "Self-Consistency", "Reflection", "Meta"}
	assert set(prompts.keys()) == expected_keys
	for key, value in prompts.items():
		assert hasattr(value, "messages"), f"Prompt {key} should expose messages"
		assert isinstance(value.messages, tuple)


def test_get_prompts_every_prompt_includes_context_placeholder_and_prompt_core():
	"""Arrange: load prompts; Act: inspect message text; Assert: PROMPT_CORE fragments present in each human prompt."""
	mod = _import_prompts_module()
	prompts = mod.get_prompts()

	core_fragment = "RETRIEVED CONTEXT"

	for prompt in prompts.values():
		human_messages = [msg for role, msg in prompt.messages if role == "human"]
		assert human_messages, "Each prompt should have at least one human message"
		for msg in human_messages:
			assert core_fragment in msg
			assert "{context}" in msg
			assert "{diff}" in msg
			assert "{static}" in msg


def test_get_prompts_multiple_calls_produce_distinct_prompt_instances():
	"""Arrange: call get_prompts twice; Act: compare identities; Assert: each prompt recreated fresh."""
	mod = _import_prompts_module()
	first = mod.get_prompts()
	second = mod.get_prompts()

	for key in first:
		assert first[key] is not second[key]
		# Ensure messages remain equal but independent
		assert first[key].messages == second[key].messages


def test_get_prompts_propagates_template_errors(monkeypatch):
	"""Arrange: stub template raises RuntimeError; Act+Assert: get_prompts propagates exception."""
	mod = _import_prompts_module(raise_on_from_messages=True)

	with pytest.raises(RuntimeError, match="ChatPromptTemplate failure"):
		mod.get_prompts()
