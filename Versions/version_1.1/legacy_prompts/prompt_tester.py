# prompt_tester.py
#
# Usage:
#  - In prompts.py uncomment exactly one ACTIVE_PROMPT line.
#  - Run: python prompt_tester.py
#
# The script will:
#  - fetch the PR diff,
#  - run the active prompt through the LLM,
#  - compute heuristics (readability, presence of sections, keywords),
#  - ask the LLM to meta-evaluate the produced review (scored 1-10),
#  - produce a human-friendly Markdown report saved to review_report_<PR_NUMBER>.md

import time
import json
import re
import os
from datetime import datetime
from reviewer import fetch_pr_diff, save_text_to_file, post_review_comment, llm, parser
from config import OWNER, REPO, PR_NUMBER, GITHUB_TOKEN
from prompts import ACTIVE_PROMPT  # user must uncomment one ACTIVE_PROMPT in prompts.py
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate

# Fallback check
if "ACTIVE_PROMPT" not in globals() and ACTIVE_PROMPT is None:
    raise RuntimeError("Please uncomment one ACTIVE_PROMPT in prompts.py before running the tester.")

# ------------------------------
# Heuristic scoring functions
# ------------------------------
def count_bullets(text: str) -> int:
    return len(re.findall(r"^\s*[-•*]\s+", text, flags=re.MULTILINE))

def has_sections(text: str, section_titles):
    found = {}
    lowered = text.lower()
    for s in section_titles:
        found[s] = (s.lower() in lowered)
    return found

def heuristic_metrics(review: str):
    metrics = {}
    metrics["length_chars"] = len(review)
    metrics["length_words"] = len(review.split())
    metrics["bullet_points"] = count_bullets(review)
    metrics["mentions_bug"] = bool(re.search(r"\bbug\b|\berror\b|\bfail\b", review, flags=re.I))
    metrics["mentions_suggest"] = bool(re.search(r"\bsuggest\b|\brecommend\b|\bconsider\b|\bfix\b", review, flags=re.I))
    # detect structured headings
    sections = ["summary", "bugs", "errors", "code quality", "suggestions", "improvements", "tests", "positive", "positive notes"]
    metrics["sections_presence"] = has_sections(review, sections)
    return metrics

# ------------------------------
# Meta-evaluator: ask LLM to score the review
# ------------------------------
evaluator_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an objective senior software engineer and a reviewer-judge. Score the quality of a PR review."),
    ("human",
     "Given the PR diff and the review, score the review on the following dimensions from 1 (worst) to 10 (best):\n"
     " - Clarity (is it easy to understand)\n"
     " - Usefulness (are the findings useful)\n"
     " - Depth (technical depth)\n"
     " - Actionability (clear steps to fix)\n"
     " - Positivity (balance and constructive tone)\n\n"
     "Output a JSON object exactly in this format (no extra text):\n"
     "{{\n"
     "  \"clarity\": <int 1-10>,\n"
     "  \"usefulness\": <int 1-10>,\n"
     "  \"depth\": <int 1-10>,\n"
     "  \"actionability\": <int 1-10>,\n"
     "  \"positivity\": <int 1-10>,\n"
     "  \"explain\": \"short explanation (1-2 sentences)\"\n"
     "}}\n\n"
     "PR Diff:\n{diff}\n\n"
     "Review:\n{review}\n")
])

def meta_evaluate(diff: str, review: str):
    chain = evaluator_prompt_template | llm | StrOutputParser()
    # pass both diff and review as input
    out = chain.invoke({"diff": diff[:4000], "review": review})
    # try to parse JSON from LLM output robustly
    try:
        parsed = json.loads(out.strip())
    except Exception:
        # attempt to extract JSON-like substring
        m = re.search(r"\{.*\}", out, flags=re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                parsed = {"error": "Could not parse JSON from evaluator output", "raw": out}
        else:
            parsed = {"error": "No JSON found", "raw": out}
    return parsed, out

# ------------------------------
# Runner
# ------------------------------
def run_test(post_to_github: bool = False, save_report: bool = True):
    print("Fetching PR diff...")
    diff_text = fetch_pr_diff(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN)
    print("Diff fetched (length: {} chars)".format(len(diff_text)))

    print("\nRunning active prompt through LLM...")
    chain = ACTIVE_PROMPT | llm | parser
    start = time.time()
    review_text = chain.invoke({"diff": diff_text[:4000]})
    elapsed = time.time() - start
    print(f"Review generated in {elapsed:.2f}s\n")

    # heuristic metrics
    heur = heuristic_metrics(review_text)

    # meta-evaluation by LLM
    print("Requesting meta-evaluation (LLM judge)...")
    meta_parsed, meta_raw = meta_evaluate(diff_text, review_text)

    # combined overall score (weighted)
    overall = None
    if isinstance(meta_parsed, dict) and all(k in meta_parsed for k in ["clarity", "usefulness", "depth", "actionability", "positivity"]):
        weights = {"clarity": 0.18, "usefulness": 0.28, "depth": 0.2, "actionability": 0.24, "positivity": 0.1}
        score = sum(meta_parsed[k] * w for k, w in weights.items())
        overall = round(score, 2)
    else:
        overall = "N/A"

    # prepare human-friendly report
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_md = []
    report_md.append(f"# PR Review Report\nGenerated: {now}\n")
    report_md.append(f"**Repository:** {OWNER}/{REPO}\n")
    report_md.append(f"**PR Number:** {PR_NUMBER}\n")
    report_md.append(f"**Prompt Name:** {ACTIVE_PROMPT}\n\n")
    report_md.append("## Quick Summary\n")
    report_md.append(f"- Review generation time: {elapsed:.2f}s\n")
    report_md.append(f"- Heuristic length (chars): {heur['length_chars']}\n")
    report_md.append(f"- Bullet points detected: {heur['bullet_points']}\n")
    report_md.append(f"- Mentions 'bug' or 'error': {heur['mentions_bug']}\n")
    report_md.append(f"- Mentions suggestions/recommendations: {heur['mentions_suggest']}\n")
    report_md.append(f"- Sections presence (sample):\n```\n{json.dumps(heur['sections_presence'], indent=2)}\n```\n")
    report_md.append("## LLM Meta-Evaluation (judge)\n")
    report_md.append("Raw evaluator output:\n```\n" + (meta_raw if isinstance(meta_raw, str) else str(meta_raw)) + "\n```\n")
    if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
        report_md.append("Parsed scores:\n")
        report_md.append("```\n" + json.dumps(meta_parsed, indent=2) + "\n```\n")
        report_md.append(f"**Overall weighted score (0-10): {overall}**\n")
    else:
        report_md.append("Evaluator failed to produce structured scores. See raw output above.\n")

    report_md.append("## Generated Review\n")
    report_md.append("```\n" + review_text + "\n```\n")

    # Save files
    if save_report:
        filename = f"review_report_PR{PR_NUMBER}.md"
        save_text_to_file(filename, "\n".join(report_md))
        print(f"Saved report to {filename}")

    # Optionally post to GitHub (safe: wrapped in try/except)
    if post_to_github:
        try:
            print("Attempting to post comment to GitHub...")
            comment = post_review_comment(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN, review_text)
            print("Posted comment:", comment.get("html_url"))
        except Exception as e:
            print("Failed to post to GitHub:", str(e))
            # also save local file with review only
            save_text_to_file(f"review_PR{PR_NUMBER}_local.md", review_text)
            print("Saved local copy of the review.")

    # Print human-friendly summary
    print("\n===== SUMMARY =====")
    print(f"Prompt: {ACTIVE_PROMPT}\n")
    if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
        print("Meta scores (clarity/usefulness/depth/actionability/positivity):")
        print(f"{meta_parsed.get('clarity')}/{meta_parsed.get('usefulness')}/"
              f"{meta_parsed.get('depth')}/{meta_parsed.get('actionability')}/{meta_parsed.get('positivity')}")
        print("Overall (weighted):", overall)
        print("Judge note:", meta_parsed.get("explain"))
    else:
        print("Meta-evaluation could not be parsed. See report file for raw output.")

    print("===================")
    return {
        "review": review_text,
        "heuristics": heur,
        "meta": meta_parsed,
        "overall": overall
    }

if __name__ == "__main__":
    # default: don't post to GitHub, only save report
    run_test(post_to_github=False, save_report=True)
