# accuracy_checker.py

import re
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from reviewer import llm # Import the shared LLM instance
from utils import safe_truncate # Import the truncater

# --- NEW: RAG-aware evaluator prompt ---
evaluator_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an objective senior software engineer who judges review quality."),
    ("human",
     "You will evaluate a Pull Request review based on the diff, static analysis, and retrieved context provided.\n"
     "Judge if the review properly used the static analysis and context.\n"
     "Produce ONLY a JSON object (no extra commentary).\n\n"
     "Fields (1-10 integers): clarity, usefulness, depth, actionability, positivity.\n"
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

# --- MODIFIED: Signature updated to accept static_output and context ---
def meta_evaluate(diff: str, review: str, static_output: str, context: str):
    """
    Calls the evaluator LLM chain and returns parsed JSON (dict) and raw output.
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
    except Exception as e:
        return {"error": f"evaluator invoke failed: {e}"}, None

    # Robust JSON parsing
    parsed = None
    try:
        parsed = json.loads(raw.strip())
    except Exception:
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                parsed = {"error": "could not parse JSON", "raw": raw}
        else:
            parsed = {"error": "no JSON in evaluator output", "raw": raw}
    return parsed, raw

# --- Heuristic functions (copied from your V1 code) ---
def heuristic_metrics(review: str):
    """Evaluate the generated review"""
    heur = {}
    heur["length_chars"] = len(review)
    heur["length_words"] = len(review.split())
    heur["bullet_points"] = len(re.findall(r"^\s*[-•*]\s+", review, flags=re.MULTILINE))
    heur["mentions_bug"] = bool(re.search(r"\bbug\b|\berror\b|\bfail\b|\bissue\b", review, flags=re.I))
    heur["mentions_suggest"] = bool(re.search(r"\bsuggest\b|\brecommend\b|\bconsider\b|\bfix\b|\baction\b", review, flags=re.I))
    sections = ["summary", "bugs", "errors", "code quality", "suggestions", "improvements", "tests", "positive", "final review"]
    lowered = review.lower()
    heur["sections_presence"] = {s: (s.lower() in lowered) for s in sections}
    return heur