"""
Evaluation module for PR review quality assessment.

This module provides heuristics-based metrics, meta-evaluation via LLM,
and scoring utilities to assess the quality of generated code reviews.
"""

import re
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core import llm
from utils import safe_truncate


# -------------------------
# Heuristic helpers
# -------------------------
def count_bullets(text: str) -> int:
    """Count bullet points in text."""
    return len(re.findall(r"^\s*[-•*]\s+", text, flags=re.MULTILINE))


def has_sections(text: str, section_titles):
    """Check which section titles are present in text."""
    lowered = text.lower()
    return {s: (s.lower() in lowered) for s in section_titles}


def heuristic_metrics(review: str):
    """Calculate heuristic metrics for a review."""
    metrics = {}
    metrics["length_chars"] = len(review)
    metrics["length_words"] = len(review.split())
    metrics["bullet_points"] = count_bullets(review)
    metrics["mentions_bug"] = bool(
        re.search(r"\bbug\b|\berror\b|\bfail\b|\bissue\b", review, flags=re.I)
    )
    metrics["mentions_suggest"] = bool(
        re.search(
            r"\bsuggest\b|\brecommend\b|\bconsider\b|\bfix\b|\baction\b",
            review, flags=re.I
        )
    )
    sections = ["summary", "bugs", "errors", "code quality", "suggestions",
                "improvements", "tests", "positive", "final review"]
    metrics["sections_presence"] = has_sections(review, sections)
    return metrics


# -------------------------
# Meta-evaluator prompt
# Added {static} (bug fix) and {context} (RAG)
# -------------------------
evaluator_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an objective senior software engineer who judges review "
     "quality."),
    ("human",
     "You will evaluate a Pull Request review based on the diff, static "
     "analysis, and retrieved context provided.\n"
     "Judge if the review properly used the static analysis and context.\n"
     "Produce ONLY a JSON object (no extra commentary).\n\n"
     "Fields (1-10 integers): clarity, usefulness, depth, actionability, "
     "positivity.\n"
     "Also include a short `explain` string (1-2 sentences).\n\n"
     "Output JSON (exact format):\n"
     "{{\n"
     '  "clarity": <int 1-10>,\n'
     '  "usefulness": <int 1-10>,\n'
     '  "depth": <int 1-10>,\n'
     '  "actionability": <int 1-10>,\n'
     '  "positivity": <int 1-10>,\n'
     '  "explain": "short explanation"\n'
     "}}\n\n"
     "PR Diff (truncated):\n{diff}\n\n"
     "Static Analysis Results:\n{static}\n\n"
     "Retrieved Context:\n{context}\n\n"
     "Review to evaluate:\n{review}\n")
])


def meta_evaluate(diff: str, review: str, static_output: str, context: str):
    """
    Call the evaluator LLM chain and return parsed JSON and raw output.

    Args:
        diff: PR diff text
        review: Generated review text
        static_output: Static analysis results
        context: Retrieved RAG context

    Returns:
        tuple: (parsed_dict, raw_text) where parsed_dict may contain
               'error' key on problems
    """
    chain = evaluator_prompt | llm | StrOutputParser()
    try:
        # Truncate inputs for the evaluator
        truncated_diff = safe_truncate(diff, 4000)
        truncated_review = safe_truncate(review, 4000)
        truncated_static = safe_truncate(static_output, 2000)
        truncated_context = safe_truncate(context, 2000)

        raw = chain.invoke({
            "diff": truncated_diff,
            "review": truncated_review,
            "static": truncated_static,
            "context": truncated_context
        })
    except (RuntimeError, ValueError, ConnectionError) as error:
        return {"error": f"evaluator invoke failed: {error}"}, None

    # parse JSON robustly
    parsed = None
    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {"error": "could not parse JSON", "raw": raw}
        else:
            parsed = {"error": "no JSON in evaluator output", "raw": raw}
    return parsed, raw


# -------------------------
# Score combining functions
# -------------------------
def meta_to_score(meta_parsed: dict):
    """
    Convert meta-evaluation fields to a score (0-10).

    Args:
        meta_parsed: Dictionary containing evaluation metrics

    Returns:
        float: Weighted score from 0-10, or None if invalid
    """
    # Weighted average of meta fields (1-10) -> 0-10
    if not isinstance(meta_parsed, dict) or "error" in meta_parsed:
        return None
    weights = {
        "clarity": 0.18,
        "usefulness": 0.28,
        "depth": 0.2,
        "actionability": 0.24,
        "positivity": 0.1
    }
    score = 0.0
    for key, weight in weights.items():
        val = meta_parsed.get(key)
        if isinstance(val, (int, float)):
            score += val * weight
        else:
            # If missing, treat as neutral 5
            score += 5 * weight
    return round(score, 2)


def heuristics_to_score(heur: dict):
    """
    Produce a 0-10 heuristics score from several signals.

    Args:
        heur: Dictionary containing heuristic metrics

    Returns:
        float: Score from 0-10 based on heuristics
    """
    sections = heur.get("sections_presence", {})
    if sections:
        sec_frac = (sum(1 for v in sections.values() if v) /
                    max(1, len(sections)))
    else:
        sec_frac = 0.0
    bullets = heur.get("bullet_points", 0)
    bullets_score = min(bullets, 10) / 10.0
    words = heur.get("length_words", 0)
    if 80 <= words <= 800:
        length_score = 1.0
    else:
        if words < 80:
            length_score = max(0.0, words / 80.0)
        else:
            length_score = max(0.0, 1.0 - (words - 800) / 2000.0)
    bug_bonus = 0.1 if heur.get("mentions_bug") else 0.0
    suggest_bonus = 0.1 if heur.get("mentions_suggest") else 0.0

    mix = ((0.45 * sec_frac) + (0.25 * bullets_score) +
           (0.25 * length_score) + bug_bonus + suggest_bonus)
    mix = max(0.0, min(mix, 1.0))
    return round(mix * 10, 2)


def combine_final_score(meta_parsed: dict, heur: dict):
    """
    Combine meta-evaluation and heuristics into final score.

    Args:
        meta_parsed: Meta-evaluation dictionary
        heur: Heuristics dictionary

    Returns:
        tuple: (final_score, meta_score, heur_score)
    """
    meta_score = meta_to_score(meta_parsed)
    heur_score = heuristics_to_score(heur)
    if meta_score is not None:
        final_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
    else:
        final_score = round(heur_score, 2)
    return final_score, meta_score, heur_score
