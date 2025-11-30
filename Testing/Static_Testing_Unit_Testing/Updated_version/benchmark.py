"""
Benchmark module for comparing PR review prompts.

This module runs all available prompts on a PR, evaluates their quality,
and generates comparison reports in CSV and Markdown formats.
"""

import time
import csv
from datetime import datetime

from core import fetch_pr_diff, run_prompt, save_text_to_file
from prompts import get_prompts
from evaluation import (heuristic_metrics, meta_evaluate, combine_final_score,)
from config import OWNER, REPO, GITHUB_TOKEN


def benchmark_all_prompts(pr_number: int, post_to_github: bool = False):
    """
    Benchmark all available prompts on a given PR.

    Args:
        pr_number: Pull request number to review
        post_to_github: Whether to post results to GitHub (not implemented)

    Returns:
        list: Sorted list of benchmark results
    """
    # Note: post_to_github parameter reserved for future use
    _ = post_to_github

    prompts = get_prompts()
    diff = fetch_pr_diff(OWNER, REPO, pr_number, GITHUB_TOKEN)
    print(f"Fetched diff ({len(diff)} chars). "
          f"Running {len(prompts)} prompts...")

    results = []
    for name, prompt in prompts.items():
        print(f"-> Running prompt: {name}")
        start = time.time()
        try:
            # run_prompt now returns review, static_output, and context
            review, static_output, context = run_prompt(prompt, diff)
        except (RuntimeError, ValueError, ConnectionError) as error:
            review = f"ERROR: prompt invoke failed: {error}"
            static_output = "N/A"  # Default for failed run
            context = "N/A"  # Default for failed run
        elapsed = time.time() - start

        heur = heuristic_metrics(review)

        # meta_evaluate now also takes context
        meta_parsed, meta_raw = meta_evaluate(
            diff, review, static_output=static_output, context=context
        )

        final_score, _, heur_score = combine_final_score(meta_parsed, heur)
        meta_score = (None if (not isinstance(meta_parsed, dict) or
                               "error" in meta_parsed) else meta_parsed)

        results.append({
            "prompt": name,
            "review": review,
            "time_s": round(elapsed, 2),
            "heur_score": heur_score,
            "meta_score": meta_score if meta_score else "N/A",
            "final_score": final_score,
            "meta_raw": meta_raw if meta_raw else "",
            "static_output": static_output,  # Store for debugging
            "retrieved_context": context  # Store for debugging
        })
        time.sleep(0.2)

    # Sort results by final_score
    results_sorted = sorted(
        results,
        key=lambda r: (r["final_score"]
                       if isinstance(r["final_score"], (int, float)) else 0)
    )

    # Save CSV
    csv_file = f"review_reports_all_prompts_PR{pr_number}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["prompt", "time_s", "heur_score", "meta_score",
                        "final_score"])
        for result in results_sorted:
            writer.writerow([
                result["prompt"],
                result["time_s"],
                result["heur_score"],
                result["meta_score"],
                result["final_score"]
            ])

    # Save Markdown summary
    md_file = f"review_reports_all_prompts_PR{pr_number}.md"
    md_lines = [
        f"# Prompt Comparison Report — PR {pr_number}\n"
        f"Generated: {datetime.now().isoformat()}\n"
    ]
    md_lines.append("| Prompt | Time (s) | Heur. Score | Meta Score | "
                    "Final Score |")
    md_lines.append("|---|---:|---:|---:|---:|")
    for result in results_sorted:
        md_lines.append(
            f"| {result['prompt']} | {result['time_s']} | "
            f"{result['heur_score']} | {result['meta_score']} | "
            f"{result['final_score']} |"
        )
    save_text_to_file(md_file, "\n".join(md_lines))

    # Save individual reviews
    for result in results:
        safe_name = result["prompt"].replace("/", "_")
        fname = f"review_{safe_name}_PR{pr_number}.md"
        # Include static analysis AND context in individual review file
        content = (
            f"# Review by prompt: {result['prompt']}\n\n"
            f"{result['review']}\n\n"
            f"---\n## Static Analysis Output:\n{result['static_output']}\n\n"
            f"---\n## Retrieved Context:\n{result['retrieved_context']}\n\n"
            f"---\n## Meta Raw:\n{result['meta_raw']}"
        )
        save_text_to_file(fname, content)

    print(f"\nSaved summary to {md_file} and CSV to {csv_file}")
    return results_sorted
