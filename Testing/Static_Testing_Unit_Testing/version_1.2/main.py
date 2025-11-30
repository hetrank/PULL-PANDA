"""
main.py – Runs the iterative prompt selector on multiple pull requests.
"""

from iterative_prompt_selector import run_iterative_selector

# Process multiple PRs
pr_list = [6, 7]  # Example: you can pass any PR IDs here
results, selector = run_iterative_selector(pr_list)
