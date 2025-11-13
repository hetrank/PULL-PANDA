# reviewer.py
#
# Responsible for:
#  - Fetching PR diff from GitHub
#  - Posting review comments (if permitted)
#  - LLM initialization

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from config import GITHUB_TOKEN, OWNER, REPO, GROQ_API_KEY
from typing import Optional

# ------------------------------
# GitHub helpers
# ------------------------------
def fetch_pr_diff(owner: str, repo: str, pr_number: int, token: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    
    # Use the token from config.py
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.text
    except requests.exceptions.HTTPError as e:
        print(f"❌ GitHub API Error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            print(f"  (Could not find PR #{pr_number}. Check OWNER/REPO in .env)")
        elif e.response.status_code == 401:
            print(f"  (Invalid GitHub Token. Check GITHUB_TOKEN in .env)")
    except Exception as e:
        print(f"❌ Unexpected error fetching diff: {e}")
        
    return "" # Return empty string on failure

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
    model="llama-3.3-70b-versatile", # <--- THIS IS THE NEW MODEL
    temperature=0.25,
    api_key=GROQ_API_KEY,
)

# simple parser that returns string output
parser = StrOutputParser()

# ------------------------------
# Utility: safe save
# ------------------------------
def save_text_to_file(path: str, text: str):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"❌ Error saving file {path}: {e}")