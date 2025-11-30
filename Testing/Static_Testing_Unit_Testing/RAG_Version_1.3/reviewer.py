"""
Reviewer module.

Responsible for:
 - Fetching PR diffs from GitHub
 - Posting review comments
 - Initializing the LLM used for review generation
"""

# pylint: disable=W0611
from typing import Optional
import requests

from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from config import GITHUB_TOKEN, OWNER, REPO, GROQ_API_KEY
# pylint: enable=W0611


# ------------------------------
# GitHub helpers
# ------------------------------
def fetch_pr_diff(owner: str, repo: str, pr_number: int, token: str) -> str:
    """Fetch the Pull Request diff from GitHub as text."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text

    except requests.exceptions.HTTPError as err_http:
        print(
            f"❌ GitHub API Error: {err_http.response.status_code} - "
            f"{err_http.response.text}"
        )
        if err_http.response.status_code == 404:
            print(f"  (Could not find PR #{pr_number}. Check OWNER/REPO settings.)")
        elif err_http.response.status_code == 401:
            print("  (Invalid GitHub Token. Check GITHUB_TOKEN configuration.)")

    except requests.exceptions.RequestException as err_req:
        print(f"❌ Unexpected network error fetching diff: {err_req}")

    return ""


def post_review_comment(
    owner: str, repo: str, pr_number: int, token: str, review_body: str
) -> dict:
    """Post a GitHub review comment on a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {"body": review_body}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"❌ Failed to post comment: {response.json()}")
        return response.json()

    except requests.exceptions.RequestException as err_req:
        raise RuntimeError(f"❌ Network error posting comment: {err_req}") from err_req


# ------------------------------
# LLM initialization
# ------------------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.25,
    api_key=GROQ_API_KEY,
)

parser = StrOutputParser()


# ------------------------------
# Utility: safe save
# ------------------------------
def save_text_to_file(path: str, text: str):
    """Safely write text to a file with UTF-8 encoding."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    except OSError as err_os:
        print(f"❌ Error saving file {path}: {err_os}")
