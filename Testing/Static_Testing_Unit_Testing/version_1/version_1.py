"""
GitHub Pull Request Review Tool.

This script fetches pull request diffs from GitHub and sends them to a local
Ollama instance for AI-powered code review.
"""

import os
import requests
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq


# 1. Load API Keys
load_dotenv()

# GitHub Personal Access Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Groq API Key
GROQ_API_KEY = os.getenv("API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found. Please set it in .env file.")

# 2. GitHub PR Config
OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")


def fetch_pr_diff(owner_name, repo_name, pr_id, token):
    """Fetch the diff of a Pull Request from GitHub."""
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pulls/{pr_id}"
    headers = {"Authorization": f"token {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        pr_data = response.json()
        diff_url = pr_data["diff_url"]

        diff_response = requests.get(diff_url, headers=headers, timeout=10)
        diff_response.raise_for_status()
        return diff_response.text

    except requests.exceptions.RequestException as err:
        raise RuntimeError(f"GitHub API Error: {err}") from err


def post_review_comment(owner_name, repo_name, pr_id, token, review_body):
    """Post a review comment on a GitHub Pull Request."""
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/issues/{pr_id}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {"body": review_body}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        raise RuntimeError(f"❌ Failed to post comment: {err}") from err


# 5. Initialize Groq AI Reviewer
LLM = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=GROQ_API_KEY,
)

PARSER = StrOutputParser()

REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior software engineer reviewing a GitHub Pull Request. "
        "Point out bugs, bad practices, improvements, and give constructive suggestions."
    ),
    ("human", "Here is the diff of the PR:\n\n{diff}\n\nPlease provide a review.")
])

REVIEW_CHAIN = REVIEW_PROMPT | LLM | PARSER


def main():
    """Main execution logic for fetching PR diff, reviewing, and posting comments."""
    try:
        # Fetch PR diff
        diff_text = fetch_pr_diff(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN)
        print("✅ Diff fetched successfully. Sending to AI reviewer...\n")

        # AI Review
        review = REVIEW_CHAIN.invoke({"diff": diff_text[:4000]})
        print("=== AI REVIEW RESULT ===")
        print(review)
        print("========================")

        # Post review back to GitHub PR
        print("📌 Posting review comment to GitHub...")
        comment = post_review_comment(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN, review)
        print(f"✅ Review posted at: {comment['html_url']}")

    except (requests.exceptions.RequestException, ValueError, RuntimeError) as err:
        print("Error:", str(err))


if __name__ == "__main__":
    main()
