"""
GitHub PR reviewer module.

Responsible for:
 - Fetching PR diff from GitHub
 - Posting review comments (if permitted)
 - LLM initialization

Note: posting can fail due to permissions; prompt_tester gracefully handles this.
"""

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from config import GITHUB_TOKEN, OWNER, REPO, PR_NUMBER, GROQ_API_KEY

# ------------------------------
# GitHub helpers
# ------------------------------


def fetch_pr_diff(owner: str, repo: str, pr_number: int, token: str) -> str:
    """
    Fetch PR diff from GitHub.

    Args:
        owner: Repository owner username
        repo: Repository name
        pr_number: Pull request number
        token: GitHub personal access token

    Returns:
        str: The PR diff text

    Raises:
        Exception: If API request fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"GitHub API Error: {response.json()}"
        )
    pr_data = response.json()
    diff_url = pr_data.get("diff_url")
    if not diff_url:
        raise ValueError("No diff_url found in PR data.")
    diff_resp = requests.get(diff_url, headers=headers, timeout=10)
    if diff_resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Failed to fetch diff from diff_url: {diff_resp.status_code}"
        )
    return diff_resp.text


def post_review_comment(
    owner: str, repo: str, pr_number: int, token: str, review_body: str
) -> dict:
    """
    Post a review comment to a GitHub PR.

    Args:
        owner: Repository owner username
        repo: Repository name
        pr_number: Pull request number
        token: GitHub personal access token
        review_body: The review comment text

    Returns:
        dict: GitHub API response with comment details

    Raises:
        Exception: If posting comment fails
    """
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/"
        f"issues/{pr_number}/comments"
    )
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code not in (200, 201):
        raise requests.exceptions.HTTPError(
            f"❌ Failed to post comment: {response.json()}"
        )
    return response.json()


# ------------------------------
# LLM initialization
# ------------------------------
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing or empty. Cannot initialize LLM.")

try:
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.25,
        api_key=GROQ_API_KEY,
    )
except (ValueError, TypeError, ConnectionError) as e:
    # These are expected initialization errors
    raise RuntimeError(f"Failed to initialize ChatGroq: {e}") from e
except Exception as e:  # pylint: disable=broad-exception-caught
    # Catch any unexpected failure and preserve original traceback
    raise RuntimeError(f"Unexpected error initializing ChatGroq: {e}") from e

parser = StrOutputParser()




# ------------------------------
# Utility: safe save
# ------------------------------


def save_text_to_file(path: str, text: str):
    """
    Save text to a file safely.

    Args:
        path: File path to save to
        text: Text content to write
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# Expose imports for use by other modules
__all__ = [
    "fetch_pr_diff",
    "post_review_comment",
    "save_text_to_file",
    "llm",
    "parser",
    "GITHUB_TOKEN",
    "OWNER",
    "REPO",
    "PR_NUMBER",
]
