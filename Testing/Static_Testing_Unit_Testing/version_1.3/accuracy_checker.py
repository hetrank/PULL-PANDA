# accuracy_checker.py
# Runs all prompts from prompts_v2.get_prompts() on the same PR diff,
# collects deterministic heuristics + LLM meta-evaluation, computes a
# combined 0-10 score per prompt, and produces:
#  - review_reports_all_prompts.csv
#  - review_reports_all_prompts.md
# plus an ASCII bar chart printed to terminal (sorted ascending).

# This file generates different prompting techniques reports so that it could be assessed visually

import time
import json
import re
import csv
import os
from datetime import datetime
from reviewer import fetch_pr_diff, llm, parser, save_text_to_file
from config import OWNER, REPO, PR_NUMBER, GITHUB_TOKEN
from prompts_v2 import get_prompts
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
# -------------------------
# Heuristic helpers
# -------------------------
def count_bullets(text: str) -> int:
    return len(re.findall(r"^\s*[-•*]\s+", text, flags=re.MULTILINE))

def has_sections(text: str, section_titles):
    lowered = text.lower()
    return {s: (s.lower() in lowered) for s in section_titles}

def heuristic_metrics(review: str):
    metrics = {}
    metrics["length_chars"] = len(review)
    metrics["length_words"] = len(review.split())
    metrics["bullet_points"] = count_bullets(review)
    metrics["mentions_bug"] = bool(re.search(r"\bbug\b|\berror\b|\bfail\b|\bissue\b", review, flags=re.I))
    metrics["mentions_suggest"] = bool(re.search(r"\bsuggest\b|\brecommend\b|\bconsider\b|\bfix\b|\baction\b", review, flags=re.I))
    sections = ["summary", "bugs", "errors", "code quality", "suggestions", "improvements", "tests", "positive", "final review"]
    metrics["sections_presence"] = has_sections(review, sections)
    return metrics

# -------------------------
# Meta-evaluator prompt (careful to escape JSON braces)
# -------------------------
evaluator_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an objective senior software engineer who judges review quality."),
    ("human",
     "You will evaluate a Pull Request review. Produce ONLY a JSON object (no extra commentary).\n\n"
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
     "Review to evaluate:\n{review}\n")
])

def meta_evaluate(diff: str, review: str):
    chain = evaluator_prompt | llm | StrOutputParser()
    try:
        out = chain.invoke({"diff": diff[:4000], "review": review})
    except Exception as e:
        return {"error": f"evaluator invoke failed: {e}"}, None

    # parse JSON robustly
    parsed = None
    try:
        parsed = json.loads(out.strip())
    except Exception:
        m = re.search(r"\{.*\}", out, flags=re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                parsed = {"error": "could not parse JSON", "raw": out}
        else:
            parsed = {"error": "no JSON in evaluator output", "raw": out}
    return parsed, out

# -------------------------
# Score combining functions
# -------------------------
def meta_to_score(meta_parsed: dict):
    # Weighted average of meta fields (1-10) -> 0-10
    if not isinstance(meta_parsed, dict) or "error" in meta_parsed:
        return None
    weights = {"clarity": 0.18, "usefulness": 0.28, "depth": 0.2, "actionability": 0.24, "positivity": 0.1}
    score = 0.0
    for k, w in weights.items():
        val = meta_parsed.get(k)
        if isinstance(val, (int, float)):
            score += val * w
        else:
            # If missing, down-weight by giving neutral 5
            score += 5 * w
    return round(score, 2)

def heuristics_to_score(heur: dict):
    # Produce a 0-10 heuristics score from several signals
    # sections presence: fraction of important sections found
    sections = heur.get("sections_presence", {})
    if sections:
        sec_frac = sum(1 for v in sections.values() if v) / max(1, len(sections))
    else:
        sec_frac = 0.0
    # bullets score: clamp at 10 bullets
    bullets = heur.get("bullet_points", 0)
    bullets_score = min(bullets, 10) / 10.0
    # length score: words between 80 and 800 => full score
    words = heur.get("length_words", 0)
    if 80 <= words <= 800:
        length_score = 1.0
    else:
        # decay linearly away from that range
        if words < 80:
            length_score = max(0.0, words / 80.0)
        else:
            # if very long, penalize but not too harsh
            length_score = max(0.0, 1.0 - (words - 800) / 2000.0)
    bug_bonus = 0.1 if heur.get("mentions_bug") else 0.0
    suggest_bonus = 0.1 if heur.get("mentions_suggest") else 0.0

    # weighted mix to 0-1
    mix = (0.45 * sec_frac) + (0.25 * bullets_score) + (0.25 * length_score) + bug_bonus + suggest_bonus
    mix = max(0.0, min(mix, 1.0))
    return round(mix * 10, 2)

# -------------------------
# Runner: run all prompts
# -------------------------
def run_all(post_to_github: bool = False):
    prompts = get_prompts()
    diff_text = fetch_pr_diff(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN)
    print(f"Fetched PR diff ({len(diff_text)} chars). Running {len(prompts)} prompts...\n")

    results = []
    for name, prompt in prompts.items():
        print(f"-> Running prompt: {name}")
        chain = prompt | llm | parser
        start = time.time()
        try:
            review = chain.invoke({"diff": diff_text[:4000]})
        except Exception as e:
            review = f"ERROR: prompt invoke failed: {e}"
        elapsed = time.time() - start

        heur = heuristic_metrics(review)
        meta_parsed, meta_raw = meta_evaluate(diff_text, review)
        meta_score = meta_to_score(meta_parsed) if not (isinstance(meta_parsed, dict) and "error" in meta_parsed) else None
        heur_score = heuristics_to_score(heur)
        # final combined score: prefer meta if available
        if meta_score is not None:
            final_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
        else:
            final_score = round(heur_score, 2)

        results.append({
            "prompt": name,
            "review": review,
            "time_s": round(elapsed, 2),
            "heur_score": heur_score,
            "meta_score": meta_score if meta_score is not None else "N/A",
            "final_score": final_score,
            "meta_raw": meta_raw if meta_raw else ""
        })

        # small delay safety (optional)
        time.sleep(0.2)

    # Sort results by final_score ascending (so you can see improvement visually)
    results_sorted = sorted(results, key=lambda r: (r["final_score"] if isinstance(r["final_score"], (int, float)) else 0))

    # Output files: CSV and Markdown
    csv_file = f"review_reports_all_prompts_PR{PR_NUMBER}.csv"
    md_file = f"review_reports_all_prompts_PR{PR_NUMBER}.md"

    with open(csv_file, "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["prompt", "time_s", "heur_score", "meta_score", "final_score"])
        for r in results_sorted:
            writer.writerow([r["prompt"], r["time_s"], r["heur_score"], r["meta_score"], r["final_score"]])

    md_lines = []
    md_lines.append(f"# Prompt Comparison Report — PR {PR_NUMBER}\nGenerated: {datetime.now().isoformat()}\n")
    md_lines.append("| Prompt | Time (s) | Heur. Score (0-10) | Meta Score (0-10) | Final Score (0-10) |")
    md_lines.append("|---|---:|---:|---:|---:|")
    for r in results_sorted:
        md_lines.append(f"| {r['prompt']} | {r['time_s']} | {r['heur_score']} | {r['meta_score']} | {r['final_score']} |")

    md_lines.append("\n\n## ASCII bar chart (Final Score)\n")
    for r in results_sorted:
        bars = int(round((r["final_score"] if isinstance(r["final_score"], (int, float)) else 0) * 4))  # scale to 40 chars
        md_lines.append(f"- {r['prompt']}: {'█' * bars} {r['final_score']}")

    # Save MD and also individual review files
    save_text_to_file(md_file, "\n".join(md_lines))
    print(f"\nSaved summary to {md_file} and CSV to {csv_file}")

    # Save each raw review to files
    for r in results:
        safe_name = r["prompt"].replace("/", "_")
        fname = f"review_{safe_name}_PR{PR_NUMBER}.md"
        save_text_to_file(fname, f"# Review by prompt: {r['prompt']}\n\n{r['review']}\n\n-- meta_raw:\n{r['meta_raw']}")
    print("Saved individual reviews for each prompt.")

    # Print ASCII chart to terminal
    print("\n=== Final Scores (ascending) ===")
    for r in results_sorted:
        bars = int(round((r["final_score"] if isinstance(r["final_score"], (int, float)) else 0) * 4))
        print(f"{r['prompt']:20} | {'█' * bars} {r['final_score']}")
    print("===============================\n")

    return results_sorted

if __name__ == "__main__":
    run_all(post_to_github=False)