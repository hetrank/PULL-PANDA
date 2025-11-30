"""Main entry point for the automated Pull Request review system.

This script automatically runs the iterative prompt selector for a given PR number
from the .env file, validates it, and posts the generated AI review to GitHub.
"""

from selector_runner import run_selector
from config import PR_NUMBER


def main():
    """Main function to run the PR review automation."""
    # --- Safely convert PR_NUMBER to an integer ---
    try:
        pr_number = int(PR_NUMBER)
    except (TypeError, ValueError):
        pr_number = 0  # Default to 0 if PR_NUMBER is None or not a number

    if pr_number <= 0:
        print("Error: PR_NUMBER is not set or invalid in .env")
    else:
        print(f"Processing PR #{pr_number} using iterative selector...")
        run_selector([pr_number], post_to_github=True)
        print("Done! Review generated and selector state updated.")


if __name__ == "__main__":
    main()
