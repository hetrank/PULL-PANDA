# reviewer.py
#
# Responsible for:
#  - Fetching PR diff from GitHub
#  - Posting review comments (if permitted)
#  - LLM initialization
#
# Note: posting can fail due to permissions; prompt_tester gracefully handles this.

import requests
from langchain.schema.output_parser import StrOutputParser
from langchain_groq import ChatGroq
from config import GITHUB_TOKEN, OWNER, REPO, PR_NUMBER, GROQ_API_KEY
from typing import Optional

# ------------------------------
# GitHub helpers
# ------------------------------
def fetch_pr_diff(owner: str, repo: str, pr_number: int, token: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.json()}")
    pr_data = response.json()
    diff_url = pr_data.get("diff_url")
    if not diff_url:
        raise Exception("No diff_url found in PR data.")
    diff_resp = requests.get(diff_url, headers=headers)
    if diff_resp.status_code != 200:
        raise Exception(f"Failed to fetch diff from diff_url: {diff_resp.status_code}")
    return diff_resp.text

def post_review_comment(owner: str, repo: str, pr_number: int, token: str, review_body: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in (200, 201):
        raise Exception(f"❌ Failed to post comment: {response.json()}")
    return response.json()

# ------------------------------
# LLM initialization
# ------------------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.25,
    api_key=GROQ_API_KEY,
)

# simple parser that returns string output
parser = StrOutputParser()

# ------------------------------
# Utility: safe save
# ------------------------------
def save_text_to_file(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
