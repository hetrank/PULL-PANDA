import requests
import os
import json
from dotenv import load_dotenv

# --- Load .env file ---
load_dotenv()   # <-- THIS loads environment variables

# --- GitHub PR details ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found. Check your .env file.")

owner = "prince-chovatiya01"
repo = "nutrition-diet-planner"
pr_number = 2

# --- Step 1: Fetch PR diff ---
url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff"
}
diff = requests.get(url, headers=headers).text

print("=== PR DIFF FETCHED ===")
print(diff[:500], "...")  # preview

# --- Step 2: Send to Ollama with formatting prompt ---
prompt = f"""
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
    json={"model": "codellama", "prompt": prompt},
    stream=True
)

print("\n=== AI REVIEW ===")
review_text = ""
for line in response.iter_lines():
    if line:
        try:
            obj = json.loads(line.decode("utf-8"))
            if "response" in obj:
                review_text += obj["response"]
        except json.JSONDecodeError:
            continue

print(review_text.strip())
