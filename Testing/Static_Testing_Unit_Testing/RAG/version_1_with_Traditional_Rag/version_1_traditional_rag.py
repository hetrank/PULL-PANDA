"""
Traditional RAG-based PR review system using LangChain.

This module implements an AI-powered code review system that uses RAG
(Retrieval Augmented Generation) to analyze pull requests with repository
context from a FAISS vector index.
"""

import os
import sys

import requests
from dotenv import load_dotenv

# LangChain imports for v0.2+
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

# Import local RAG loader
from rag_loader import build_index_for_repo, assemble_context


# ------------------------------
# 1. Load API Keys
# ------------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")

if not GITHUB_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Missing API keys in .env file")


# ------------------------------
# 2. Fetch Latest PR Number
# ------------------------------
def get_latest_pr(repo_owner, repo_name, token):
    """
    Fetch the latest open pull request from a GitHub repository.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        token: GitHub authentication token

    Returns:
        Tuple of (pr_number, pr_url)

    Raises:
        ValueError: If GitHub API returns an error or no open PRs exist
    """
    url = (f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls?"
           f"state=open&sort=created&direction=desc")
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"GitHub API Error: {response.json()}")

    prs = response.json()
    if not prs:
        raise ValueError("⚠️ No open PRs found in this repository.")

    latest_pr = prs[0]
    return latest_pr["number"], latest_pr["html_url"]


# ------------------------------
# 3. Fetch PR Diff
# ------------------------------
def fetch_pr_diff(repo_owner, repo_name, pr_num, token):
    """
    Fetch the diff for a specific pull request.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub authentication token

    Returns:
        String containing the PR diff
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_num}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"  # Return unified diff
    }

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print("❌ Error fetching diff:", response.status_code, response.text)
        return ""

    diff = response.text
    print("📏 Diff length:", len(diff))
    if len(diff) < 50:
        print("⚠️ Warning: Diff seems too small, "
              "check if PR actually has changes.")

    with open("latest_pr.diff", "w", encoding="utf-8") as f:
        f.write(diff)

    return diff


# ------------------------------
# 4. Post Review Comment
# ------------------------------
def post_review_comment(repo_owner, repo_name, pr_num, token, review_body):
    """
    Post a review comment to a pull request.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub authentication token
        review_body: The review comment text

    Returns:
        JSON response from GitHub API
    """
    url = (f"https://api.github.com/repos/{repo_owner}/{repo_name}/"
           f"issues/{pr_num}/comments")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    return response.json()


# ------------------------------
# 5. Groq AI Reviewer Setup
# ------------------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=GROQ_API_KEY
)
parser = StrOutputParser()

# System instruction for the AI reviewer
SYSTEM_INSTRUCTION = (
    "You are PULL-PANDA, a senior software engineer specialized in code "
    "review. Your primary goal is to review the code changes contained ONLY "
    "in the provided PR diff. Use the 'Project Context' only to ensure the "
    "changes align with existing project logic, naming conventions, and "
    "style. If the PR diff is in a different language than the context, "
    "ignore the context completely and focus only on the quality, "
    "correctness, and style of the new code in the diff. Structure your "
    "response clearly with specific findings (Issues, Suggestions) and a "
    "final verdict."
)

review_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_INSTRUCTION),
    ("human", "Project Context:\n{context}\n\nPR Diff:\n\n{diff}\n\n"
              "Please provide a detailed, actionable code review.")
])

# Compose chain
review_chain = review_prompt | llm | parser


# ------------------------------
# 6. Main Logic
# ------------------------------
def main():
    """Main execution function for the PR review system."""
    try:
        if len(sys.argv) < 3:
            print("Usage: python version_1_traditional_rag.py <owner> <repo>")
            sys.exit(1)

        owner, repo = sys.argv[1], sys.argv[2]

        # 1. Build or load RAG index for repo
        print("📦 Building/loading RAG index for repo "
              "(this may take a minute)...")
        rag = build_index_for_repo(owner, repo, GITHUB_TOKEN,
                                    force_rebuild=False)

        # 2. Get latest PR from GitHub
        pr_number, pr_url = get_latest_pr(owner, repo, GITHUB_TOKEN)
        print(f"🔸 Found latest PR: {pr_url}")

        # 3. Fetch PR diff
        diff_text = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
        if not diff_text:
            raise ValueError("No diff fetched.")

        # 4. Create retriever and get context
        retriever = rag.as_retriever(search_kwargs={"k": 6})

        # Retrieve relevant Document objects
        retrieved_documents = retriever.get_relevant_documents(diff_text)
        print("Retrieved", len(retrieved_documents), "context chunks.")

        # Assemble context (expects Document objects from LangChain)
        context_text = assemble_context(retrieved_documents, char_limit=3000)

        # 5. Generate AI review
        prompt_vars = {"context": context_text, "diff": diff_text[:80_000]}
        review_text = review_chain.invoke(prompt_vars)
        print("=== 🧠 AI REVIEW ===")
        print(review_text)
        print("====================")

        # 6. Post review comment on PR
        comment = post_review_comment(
            owner, repo, pr_number, GITHUB_TOKEN, review_text
        )
        if "html_url" in comment:
            print(f"✅ Review posted: {comment['html_url']}")
        else:
            print(f"⚠️ Failed to post review: {comment}")

    except (ValueError, KeyError, requests.RequestException) as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    main()
