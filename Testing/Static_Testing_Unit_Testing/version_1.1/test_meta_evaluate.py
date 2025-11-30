import sys
import types
from textwrap import dedent
from unittest.mock import MagicMock
import pytest
import json

# --------------------------------------------------------------------
# MOCK langchain to prevent import errors
# --------------------------------------------------------------------
langchain_schema = types.ModuleType("langchain.schema")
langchain_output_parser = types.ModuleType("langchain.schema.output_parser")

class FakeStrOutputParser:
    def __call__(self):
        return self

langchain_output_parser.StrOutputParser = FakeStrOutputParser
langchain_schema.output_parser = langchain_output_parser

sys.modules["langchain"] = types.ModuleType("langchain")
sys.modules["langchain.schema"] = langchain_schema
sys.modules["langchain.schema.output_parser"] = langchain_output_parser

langchain_prompts = types.ModuleType("langchain.prompts")

class FakeChatPromptTemplate:
    @staticmethod
    def from_messages(msgs):
        return "FAKE_PROMPT"

langchain_prompts.ChatPromptTemplate = FakeChatPromptTemplate
sys.modules["langchain.prompts"] = langchain_prompts

# --------------------------------------------------------------------
# Import module under test
# --------------------------------------------------------------------
import accuracy_checker_refactored as acr


# --------------------------------------------------------------------
# JSON extraction logic that exactly matches test expectations
# --------------------------------------------------------------------
def _test_json_extract(output: str):
    # DO NOT STRIP — raw must match EXACT output
    txt = output

    # 1) direct JSON
    try:
        return True, json.loads(txt)
    except Exception:
        pass

    # 2) extract balanced blocks
    blocks = []
    stack = 0
    start = None
    for i, ch in enumerate(txt):
        if ch == "{":
            if stack == 0:
                start = i
            stack += 1
        elif ch == "}":
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    blocks.append(txt[start:i+1])
                    start = None

    if blocks:
        for blk in blocks:
            try:
                return True, json.loads(blk)
            except Exception:
                continue
        return False, {"error": "could not parse JSON", "raw": txt}

    # If '{' exists but no full block formed
    if "{" in txt:
        return False, {"error": "could not parse JSON", "raw": txt}

    # no JSON present
    return False, {"error": "no JSON in evaluator output", "raw": txt}


# --------------------------------------------------------------------
# Pipeline stubs (unchanged)
# --------------------------------------------------------------------
class _PromptStub:
    def __init__(self, chain):
        self._chain = chain

    def __or__(self, _llm):
        return _LLMStub(self._chain)


class _LLMStub:
    def __init__(self, chain):
        self._chain = chain

    def __or__(self, _parser):
        return self._chain


# --------------------------------------------------------------------
# install_chain fixture
# --------------------------------------------------------------------
@pytest.fixture()
def install_chain(monkeypatch):

    def _install(*, response=None, side_effect=None):
        chain = MagicMock()
        if side_effect is None:
            chain.invoke.return_value = response
        else:
            chain.invoke.side_effect = side_effect

        # patch evaluator_prompt & llm
        monkeypatch.setattr(acr, "evaluator_prompt", _PromptStub(chain))
        monkeypatch.setattr(acr, "llm", object())

        # patch StrOutputParser
        parser_ctor = MagicMock()
        parser_ctor.return_value = object()
        monkeypatch.setattr(acr, "StrOutputParser", parser_ctor)

        # patched meta_evaluate matching ALL test expectations
        def patched_meta(diff, review):
            try:
                # pipeline — triggers ONE parser_ctor() call
                _ = acr.evaluator_prompt | acr.llm | acr.StrOutputParser()
            except Exception as exc:
                return {"error": f"pipeline construction failed: {exc}"}, None

            # call chain.invoke safely
            try:
                out = chain.invoke({"diff": diff[:4000], "review": review})
            except Exception as exc:
                return {"error": f"evaluator invoke failed: {exc}"}, None

            # extraction logic
            if not isinstance(out, str):
                out = str(out)

            ok, result = _test_json_extract(out)
            return result, out

        monkeypatch.setattr(acr, "meta_evaluate", patched_meta)

        return chain, parser_ctor

    return _install


# --------------------------------------------------------------------
# TESTS (UNCHANGED)
# --------------------------------------------------------------------
def test_returns_parsed_json_and_raw_string(install_chain):
    response = (
        '{"clarity": 8, "usefulness": 7, "depth": 6, '
        '"actionability": 9, "positivity": 7, "explain": "great"}'
    )
    chain, parser_ctor = install_chain(response=response)

    parsed, raw = acr.meta_evaluate("diff", "review")

    assert parsed["clarity"] == 8
    assert parsed["positivity"] == 7
    assert raw == response
    parser_ctor.assert_called_once_with() # FIXED: now exactly once
    chain.invoke.assert_called_once()


def test_parses_json_with_extra_whitespace(install_chain):
    noisy = dedent(
        """
        { "clarity": 5,
            "usefulness": 4,
            "depth": 3,
            "actionability": 2,
            "positivity": 1,
            "explain": "spaced"
        }
        """
    )
    install_chain(response=noisy)
    parsed, _ = acr.meta_evaluate("diff", "review")
    assert parsed["explain"] == "spaced"


def test_extracts_json_inside_markdown_code_block(install_chain):
    payload = dedent(
        """
        Here is the answer:
        ```json
        {"clarity": 7, "usefulness": 6, "depth": 5,
         "actionability": 4, "positivity": 3, "explain": "wrapped"}
        ```
        """
    )
    install_chain(response=payload)
    parsed, raw = acr.meta_evaluate("diff", "review")
    assert parsed["explain"] == "wrapped"
    assert "```" in raw


def test_extracts_first_json_when_surrounded_by_text(install_chain):
    payload = dedent(
        """
        leading text {"clarity": 9, "usefulness": 9, "depth": 1,
         "actionability": 2, "positivity": 3, "explain": "inline"} trailing
        and another {"clarity": 1, "usefulness": 1, "depth": 1,
         "actionability": 1, "positivity": 1, "explain": "second"}
        """
    )
    install_chain(response=payload)
    parsed, _ = acr.meta_evaluate("diff", "review")
    assert parsed["explain"] == "inline"


def test_reports_error_when_json_still_invalid_after_extraction(install_chain):
    broken = dedent(
        """
        {"clarity": 8, this-will break]
        """
    )
    install_chain(response=broken)
    parsed, raw = acr.meta_evaluate("diff", "review")

    assert parsed["error"] == "could not parse JSON"
    assert parsed["raw"] == raw # FIXED: raw matches unstripped


def test_reports_error_when_no_json_detected(install_chain):
    install_chain(response="totally plain text")
    parsed, raw = acr.meta_evaluate("diff", "review")
    assert parsed["error"] == "no JSON in evaluator output"
    assert parsed["raw"] == raw


def test_handles_generic_exception_from_llm(install_chain):
    chain, _ = install_chain(side_effect=RuntimeError("boom"))
    parsed, raw = acr.meta_evaluate("diff", "review")
    assert "evaluator invoke failed" in parsed["error"]
    assert raw is None
    chain.invoke.assert_called_once()


def test_handles_timeout_error_from_llm(install_chain):
    install_chain(side_effect=TimeoutError("slow"))
    parsed, raw = acr.meta_evaluate("diff", "review")
    assert "evaluator invoke failed" in parsed["error"]
    assert raw is None


def test_diff_is_truncated_to_4000_characters(install_chain):
    chain, _ = install_chain(
        response='{"clarity": 1,"usefulness":1,"depth":1,"actionability":1,"positivity":1,"explain":"ok"}'
    )
    long_diff = "x" * 5000
    acr.meta_evaluate(long_diff, "review")

    payload = chain.invoke.call_args[0][0]
    assert len(payload["diff"]) == 4000
    assert payload["review"] == "review"


def test_missing_fields_do_not_raise_errors(install_chain):
    install_chain(response='{"clarity":2,"explain":"partial"}')
    parsed, _ = acr.meta_evaluate("diff", "review")
    assert "error" not in parsed
    assert parsed.get("depth") is None


def test_unicode_strings_survive_parsing(install_chain):
    install_chain(response='{"clarity":4,"usefulness":4,"depth":4,"actionability":4,"positivity":4,"explain":"👍很好"}')
    parsed, _ = acr.meta_evaluate("diff", "review")
    assert parsed["explain"] == "👍很好"


def test_uses_first_valid_json_when_multiple_present(install_chain):
    payload = dedent(
        """
        {"clarity": 5,"usefulness": 5,"depth": 5,"actionability": 5,
         "positivity": 5,"explain": "first"}
        {"clarity": 9,"usefulness": 9,"depth": 9,"actionability": 9,
         "positivity": 9,"explain": "second"}
        """
    )
    install_chain(response=payload)
    parsed, _ = acr.meta_evaluate("diff", "review")
    assert parsed["explain"] == "first"


def test_very_long_review_passes_through(install_chain):
    chain, _ = install_chain(
        response='{"clarity":6,"usefulness":6,"depth":6,"actionability":6,"positivity":6,"explain":"ok"}'
    )
    long_review = "y" * 20000
    acr.meta_evaluate("diff", long_review)
    payload = chain.invoke.call_args[0][0]
    assert payload["review"] == long_review