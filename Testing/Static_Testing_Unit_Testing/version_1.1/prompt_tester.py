"""
prompt_tester.py

This script:
 - Fetches a PR diff,
 - Applies the currently active prompt to generate an AI review,
 - Computes heuristic metrics,
 - Requests an LLM-based meta-evaluation,
 - Optionally posts the review back to GitHub,
 - Saves a formatted Markdown report.
"""

import time
import json
import re
from datetime import datetime
from reviewer import (
    fetch_pr_diff,
    save_text_to_file,
    post_review_comment,
    llm,
    parser,
)
# Do not modify (ignore import error warning)
from config import (
    OWNER,
    REPO,
    PR_NUMBER,
    GITHUB_TOKEN,
)
from prompts import ACTIVE_PROMPT
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


if "ACTIVE_PROMPT" not in globals() and ACTIVE_PROMPT is None:
    raise RuntimeError(
        "Please uncomment one ACTIVE_PROMPT in prompts.py before running the tester."
    )


# ------------------------------
# Heuristic scoring helpers
# ------------------------------
def count_bullets(text: str) -> int:
    """Count bullet point markers in review text."""
    return len(re.findall(r"^\s*[-•*]\s+", text, flags=re.MULTILINE))


def has_sections(text: str, section_titles):
    """Return dict mapping whether common section headers appear."""
    lowered = text.lower()
    return {s: (s.lower() in lowered) for s in section_titles}


def heuristic_metrics(review: str):
    """
    Compute heuristic indicators for the generated review:
    - Length
    - Presence of bullet points
    - Presence of improvement or bug mentions
    - Presence of common review sections
    """
    metrics = {
        "length_chars": len(review),
        "length_words": len(review.split()),
        "bullet_points": count_bullets(review),
        "mentions_bug": bool(
            re.search(r"\bbug\b|\berror\b|\bfail\b", review, flags=re.I)
        ),
        "mentions_suggest": bool(
            re.search(
                r"\bsuggest\b|\brecommend\b|\bconsider\b|\bfix\b",
                review,
                flags=re.I,
            )
        ),
    }
    sections = [
        "summary",
        "bugs",
        "errors",
        "code quality",
        "suggestions",
        "improvements",
        "tests",
        "positive",
        "positive notes",
    ]
    metrics["sections_presence"] = has_sections(review, sections)
    return metrics


# ------------------------------
# Meta-evaluator
# ------------------------------
evaluator_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an objective senior software engineer and a "
            "reviewer-judge. Score the quality of a PR review.",
        ),
        (
            "human",
            "Given the PR diff and the review, score the review on the "
            "following dimensions from 1 (worst) to 10 (best):\n"
            " - Clarity\n - Usefulness\n - Depth\n - Actionability\n"
            " - Positivity\n\n"
            "Output JSON:\n"
            "{\n"
            '  "clarity": <int>,\n'
            '  "usefulness": <int>,\n'
            '  "depth": <int>,\n'
            '  "actionability": <int>,\n'
            '  "positivity": <int>,\n'
            '  "explain": "short explanation"\n'
            "}\n\n"
            "PR Diff:\n{diff}\n\nReview:\n{review}\n",
        ),
    ]
)


def meta_evaluate(diff: str, review: str):
    """
    Request a meta evaluation from the LLM and return parsed results if possible.
    """
    chain = evaluator_prompt_template | llm | StrOutputParser()
    out = chain.invoke({"diff": diff[:4000], "review": review})

    try:
        return json.loads(out.strip()), out
    except Exception:  # pylint: disable=broad-exception-caught
        match = re.search(r"\{.*\}", out, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0)), out
            except Exception:  # pylint: disable=broad-exception-caught
                return {"error": "Could not parse JSON", "raw": out}, out
        return {"error": "No JSON found", "raw": out}, out


# ------------------------------
# Runner
# ------------------------------
def run_test(post_to_github: bool = False, save_report: bool = True):
    """
    Run the end-to-end PR review process:
      - Fetch diff
      - Generate review
      - Compute heuristics
      - Meta-evaluate
      - Save report
      - Optionally post to GitHub
    """
    print("Fetching PR diff...")
    diff_text = fetch_pr_diff(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN)
    print(f"Diff fetched (length: {len(diff_text)} chars)")

    print("\nRunning active prompt through LLM...")
    chain = ACTIVE_PROMPT | llm | parser
    start = time.time()
    review_text = chain.invoke({"diff": diff_text[:4000]})
    elapsed = time.time() - start
    print(f"Review generated in {elapsed:.2f}s\n")

    heuristics = heuristic_metrics(review_text)

    print("Requesting meta-evaluation (LLM judge)...")
    meta_parsed, meta_raw = meta_evaluate(diff_text, review_text)

    overall = "N/A"
    if isinstance(meta_parsed, dict) and all(
        k in meta_parsed
        for k in [
            "clarity",
            "usefulness",
            "depth",
            "actionability",
            "positivity",
        ]
    ):
        weights = {
            "clarity": 0.18,
            "usefulness": 0.28,
            "depth": 0.2,
            "actionability": 0.24,
            "positivity": 0.1,
        }
        overall = round(sum(meta_parsed[k] * w for k, w in weights.items()), 2)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = [
        f"# PR Review Report\nGenerated: {now}\n",
        f"**Repository:** {OWNER}/{REPO}\n",
        f"**PR Number:** {PR_NUMBER}\n",
        f"**Prompt Name:** {ACTIVE_PROMPT}\n\n",
        "## Quick Summary\n",
        f"- Generation time: {elapsed:.2f}s\n",
        f"- Char length: {heuristics['length_chars']}\n",
        f"- Bullet points: {heuristics['bullet_points']}\n",
        f"- Mentions bug/error: {heuristics['mentions_bug']}\n",
        f"- Mentions suggestions: {heuristics['mentions_suggest']}\n",
        "## Meta Evaluation\n",
        "```\n"
        + (meta_raw if isinstance(meta_raw, str) else str(meta_raw))
        + "\n```\n",
    ]

    if save_report:
        filename = f"review_report_PR{PR_NUMBER}.md"
        save_text_to_file(filename, "\n".join(report))
        print(f"Saved report to {filename}")

    if post_to_github:
        try:
            print("Posting review to GitHub...")
            comment = post_review_comment(
                OWNER, REPO, PR_NUMBER, GITHUB_TOKEN, review_text
            )
            print("Posted comment:", comment.get("html_url"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Failed to post to GitHub: {exc}")
            save_text_to_file(f"review_PR{PR_NUMBER}_local.md", review_text)
            print("Saved local copy.")

    print("\n===== SUMMARY =====")
    print(f"Prompt: {ACTIVE_PROMPT}")
    print("Overall Score:", overall)
    print("===================")

    return {
        "review": review_text,
        "heuristics": heuristics,
        "meta": meta_parsed,
        "overall": overall,
    }


if __name__ == "__main__":
    run_test(post_to_github=False, save_report=True)
