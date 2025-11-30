"""Module to run the Iterative Prompt Selector for processing multiple pull requests.

This module coordinates running the IterativePromptSelector for a list of PR numbers,
optionally loads and saves selector state, and can print or post AI-generated reviews
to GitHub.
"""

from selector import IterativePromptSelector, process_pr_with_selector


def run_selector(pr_numbers, load_previous: bool = True, post_to_github: bool = False):
    """
    Runs the iterative prompt selector on a list of pull requests.

    Args:
        pr_numbers (list[int]): List of pull request numbers to process.
        load_previous (bool, optional): Whether to load a previous selector state.
            Defaults to True.
        post_to_github (bool, optional): If True, posts AI reviews back to GitHub.
            Defaults to False.

    Returns:
        tuple: A tuple containing:
            - results (list[dict]): List of PR processing results.
            - selector (IterativePromptSelector): The selector instance with updated state.
    """
    selector = IterativePromptSelector()
    if load_previous:
        selector.load_state()

    results = []

    for pr in pr_numbers:
        try:
            res = process_pr_with_selector(selector, pr, post_to_github=post_to_github)
            results.append(res)

            print("\n" + "=" * 60)
            print(f"🤖 AI REVIEW FOR PR #{pr} (Prompt: {res['chosen_prompt']})")
            print("=" * 60 + "\n")
            print(res["review"])  # This prints the full review text
            print("\n" + "=" * 60 + "\n")

        except (ValueError, RuntimeError, OSError) as err:
            print(f"Failed to process PR #{pr}: {err}")
            continue

    print("\nFINAL ITERATIVE SELECTOR REPORT")
    for r in results:
        print(f"PR #{r['pr_number']}: {r['chosen_prompt']} -> Score: {r['score']}")

    selector.save_state()
    return results, selector
