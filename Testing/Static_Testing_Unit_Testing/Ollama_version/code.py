"""
Ollama-powered GitHub PR reviewer.

This script fetches PR diffs from GitHub and uses a local Ollama instance
to generate AI-powered code reviews.
"""

import os
import json

import requests
from dotenv import load_dotenv

# --- Load .env file ---
load_dotenv()  # <-- THIS loads environment variables

# --- GitHub PR details ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found. Check your .env file.")

OWNER = "prince-chovatiya01"
REPO = "nutrition-diet-planner"
PR_NUMBER = 2

# --- Step 1: Fetch PR diff ---
URL = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff",
}
diff = requests.get(URL, headers=HEADERS, timeout=10).text

print("=== PR DIFF FETCHED ===")
print(diff[:500], "...")  # preview

# --- Step 2: Send to Ollama with formatting prompt ---
PROMPT = f"""
You are a strict GitHub code reviewer. Review the following pull request diff.

Return your feedback **in Markdown format** with the following sections:

## Summary
- Briefly explain what the code does.

## Strengths
- List positive aspects in bullet points.

## Issues / Suggestions
- List code issues, potential bugs, or improvements.

## Final Verdict
- Give a short overall statement (e.g., LGTM ✅ or Needs Work ❌).

Here is the diff:
{diff}
"""

response = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "codellama", "prompt": PROMPT},
    stream=True,
    timeout=30,
)

print("\n=== AI REVIEW ===")
REVIEW_TEXT = ""
for line in response.iter_lines():
    if line:
        try:
            obj = json.loads(line.decode("utf-8"))
            if "response" in obj:
                REVIEW_TEXT += obj["response"]
        except json.JSONDecodeError:
            continue

print(REVIEW_TEXT.strip())
