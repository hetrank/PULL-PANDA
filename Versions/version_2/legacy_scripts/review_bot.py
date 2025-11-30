import os
import requests
from groq import Groq  # 👈 use groq client instead of openai

# === Environment setup ===
repo = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("PR_NUMBER")
token = os.getenv("GITHUB_TOKEN")
groq_key = os.getenv("GROQ_API_KEY")  # 👈 change variable name

if not all([repo, pr_number, token, groq_key]):
    raise SystemExit("❌ Missing required environment variables")

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "ai-pr-bot"
}

# === Groq client ===
client = Groq(api_key=groq_key)

# === GitHub API helpers ===
def fetch_diff():
    """Fetch PR diff text"""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    diff_url = r.json()["diff_url"]

    r2 = requests.get(diff_url, headers=headers)
    r2.raise_for_status()
    return r2.text

def post_comment(body: str):
    """Post a comment on the PR"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    r = requests.post(url, headers=headers, json={"body": body})
    r.raise_for_status()
    print("✅ Comment posted successfully")

# === Review logic ===
def chunk_text(text, max_chars=3500):
    """Split text into safe chunks"""
    lines = text.splitlines()
    chunks, current = [], []
    length = 0

    for line in lines:
        if length + len(line) > max_chars:
            chunks.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks

def generate_review(diff_chunk: str) -> str:
    """Send one chunk to Groq LLM for review"""
    prompt = f"""
You are an AI pull request reviewer.
Here is a code diff chunk from a PR:

{diff_chunk}

Write a structured review:
- Briefly summarize what this chunk changes
- Give at least 2 improvement suggestions
- Note any risks (bugs, performance, security)
Respond in markdown format.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # 👈 Groq’s most powerful free model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500
    )
    return response.choices[0].message.content

def main():
    print(f"🔍 Reviewing PR #{pr_number} in {repo} ...")
    diff = fetch_diff()

    chunks = chunk_text(diff)
    print(f"📦 Split diff into {len(chunks)} chunks")

    for i, chunk in enumerate(chunks, start=1):
        review = generate_review(chunk)
        post_comment(f"### 🤖 AI Review (Part {i}/{len(chunks)})\n\n{review}")

    print("🎉 Review completed!")

if __name__ == "__main__":
    main()
