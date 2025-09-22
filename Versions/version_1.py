import requests
import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
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
owner = os.getenv("OWNER")
repo = os.getenv("REPO")
pr_number = os.getenv("PR_NUMBER")

# 3. Fetch PR Diff from GitHub
def fetch_pr_diff(owner, repo, pr_number, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.json()}")

    pr_data = response.json()
    diff_url = pr_data["diff_url"]
    diff = requests.get(diff_url, headers=headers).text
    return diff

# 4. Post Review Comment to GitHub
def post_review_comment(owner, repo, pr_number, token, review_body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [200, 201]:
        raise Exception(f"❌ Failed to post comment: {response.json()}")

    return response.json()

# 5. Initialize Groq AI Reviewer
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=GROQ_API_KEY,
)

parser = StrOutputParser()

review_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior software engineer reviewing a GitHub Pull Request. "
               "Point out bugs, bad practices, improvements, and give constructive suggestions."),
    ("human", "Here is the diff of the PR:\n\n{diff}\n\nPlease provide a review.")
])

review_chain = review_prompt | llm | parser

# 6. Main Logic
if __name__ == "__main__":
    try:
        # Fetch PR diff
        diff_text = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
        print("✅ Diff fetched successfully. Sending to AI reviewer...\n")

        # AI Review
        review = review_chain.invoke({"diff": diff_text[:4000]})
        print("=== AI REVIEW RESULT ===")
        print(review)
        print("========================")

        # Post review back to GitHub PR
        print("📌 Posting review comment to GitHub...")
        comment = post_review_comment(owner, repo, pr_number, GITHUB_TOKEN, review)
        print(f"✅ Review posted at: {comment['html_url']}")

    except Exception as e:
        print("Error:", str(e))
