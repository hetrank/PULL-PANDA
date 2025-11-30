"""
Agentic RAG-based PR review system using LangChain.

This module implements an AI-powered code review system that uses RAG
(Retrieval Augmented Generation) to analyze pull requests with full
repository context.
"""

import os
import sys
import time

import requests
from dotenv import load_dotenv

# LangChain Agent and Core Imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool

# Import local RAG loader
from rag_loader_agentic import (
    build_index_for_repo,
    assemble_context,
    REPO_DOWNLOAD_DIR
)


# ------------------------------
# 1. Load API Keys & Config
# ------------------------------
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")

if not GITHUB_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Missing API keys in .env file")


# ------------------------------
# 2. GitHub Utilities
# ------------------------------

def get_pr_number_from_args(repo_owner, repo_name, token, pr_argument=None):
    """
    Fetch the latest open PR if no number is provided, or use provided number.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        token: GitHub authentication token
        pr_argument: Optional PR number as string

    Returns:
        Tuple of (pr_number, pr_url)

    Raises:
        ValueError: If PR not found or no open PRs exist
    """
    if pr_argument and pr_argument.isdigit():
        pr_num = int(pr_argument)
        # Check if the specific PR exists and is open
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_num}"
        headers = {"Authorization": f"token {token}"}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return pr_num, response.json()["html_url"]
        raise ValueError(f"PR #{pr_num} not found or is closed.")

    # Fetch the latest open PR
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
        "Accept": "application/vnd.github.v3.diff"
    }
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print("❌ Error fetching diff:", response.status_code, response.text)
        return ""
    return response.text


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
# 3. Agent Tools Implementation
# ------------------------------

def get_full_file_content(file_path: str) -> str:
    """
    Read the full content of a file from the downloaded repository.

    Input path must be relative to the repository root (e.g., 'src/config.py').

    Args:
        file_path: Relative path to the file from repository root

    Returns:
        File content (truncated to 4000 chars) or error message
    """
    # Find the single top-level directory created by the zip extraction
    repo_root = next(
        (p for p in REPO_DOWNLOAD_DIR.iterdir() if p.is_dir()),
        REPO_DOWNLOAD_DIR
    )

    # Clean the path and resolve relative to the repo root
    target_path = repo_root / file_path.lstrip('/')

    if not target_path.exists():
        # Check if the path might be in the root directory (no subdirectory)
        if repo_root != REPO_DOWNLOAD_DIR:
            target_path = REPO_DOWNLOAD_DIR / file_path.lstrip('/')

        if not target_path.exists():
            return (f"ERROR: File not found at local path: {file_path}. "
                    f"The path must be relative to the repository root.")

    try:
        # Limit the output size to prevent overwhelming the LLM
        content = target_path.read_text(encoding="utf-8", errors="ignore")
        return (f"CONTENT OF {file_path} (Truncated at 4000 chars):\n"
                f"{content[:4000]}")
    except (IOError, OSError) as e:
        return f"ERROR: Could not read file {file_path}. Reason: {str(e)}"


def setup_agent_tools(vectorstore):
    """
    Set up the tools available to the agent.

    Args:
        vectorstore: The FAISS vectorstore for RAG retrieval

    Returns:
        List of LangChain Tool objects
    """
    # 1. The RAG Retriever Tool
    rag_retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    def retrieve_and_format_context(query: str) -> str:
        """Retrieve and format context from the vectorstore."""
        retrieved_documents = rag_retriever.get_relevant_documents(query)
        return assemble_context(retrieved_documents, char_limit=4000)

    rag_tool = Tool(
        name="project_context_search",
        func=retrieve_and_format_context,
        description=(
            "Useful for finding relevant code snippets from the existing "
            "codebase (e.g., related functions, configuration values, or "
            "file structure) based on a semantic query related to the DIFF."
        )
    )

    # 2. The Full File Lookup Tool
    file_reader_tool = Tool(
        name="full_file_reader",
        func=get_full_file_content,
        description=(
            "Useful for reading the entire contents of a known file path "
            "(e.g., 'config.json', 'src/db.py') that is mentioned in the "
            "PR diff or suggested by the project_context_search tool. "
            "Input MUST be the exact relative file path string "
            "(e.g., 'path/to/file.ext')."
        )
    )

    return [rag_tool, file_reader_tool]


# ------------------------------
# 4. Main Logic
# ------------------------------
def main():
    """Main execution function for the PR review system."""
    try:
        start_time = time.time()

        if len(sys.argv) < 3:
            print("Usage: python version_1_agentic.py <owner> <repo> [pr_number]")
            sys.exit(1)

        owner, repo = sys.argv[1], sys.argv[2]
        pr_arg = sys.argv[3] if len(sys.argv) > 3 else None

        # 1. Load RAG index and ensure local repo files are available
        print("📦 Building/loading RAG index and preparing local files...")
        rag_vectorstore = build_index_for_repo(
            owner, repo, GITHUB_TOKEN,
            force_rebuild=False,
            download_if_missing=True
        )

        # 2. Setup Agent & Tools
        tools = setup_agent_tools(rag_vectorstore)
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            api_key=GROQ_API_KEY
        )

        # 3. Create the Agent Prompt
        agent_system_message = (
            "You are PULL-PANDA, a highly experienced senior software "
            "engineer specialized in code review. Your primary mission is to "
            "identify **bugs, security issues, and architectural "
            "inconsistencies**. Provide a detailed, professional review. "
            "**Crucially, for every issue or suggestion, you MUST include:**\n"
            "1. The original faulty code line/snippet from the DIFF.\n"
            "2. A suggested corrected code snippet.\n"
            "Ensure there is absolutely **NO REPETITION** of suggestions or "
            "summary points. Your final output MUST be structured EXACTLY as "
            "three non-redundant sections:\n"
            "### CRITICAL ISSUES (Bugs/Security)\n"
            "List severe bugs, providing original and suggested code. "
            "If none, state 'None found.'\n\n"
            "### SUGGESTIONS (Style/Efficiency)\n"
            "List stylistic or efficiency improvements, providing original "
            "and suggested code where applicable. If none, state "
            "'None found.'\n\n"
            "### CONCISE SUMMARY\n"
            "Provide a final, one-paragraph evaluation of the PR's overall "
            "quality and acceptance status (e.g., 'Approved with minor fixes')."
        )

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", agent_system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "Please review the following PR diff:\n\n{diff}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, agent_prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )

        # 4. Get target PR and diff
        pr_number, pr_url = get_pr_number_from_args(
            owner, repo, GITHUB_TOKEN, pr_arg
        )
        print(f"🔸 Found target PR: {pr_url}")

        diff_text = fetch_pr_diff(owner, repo, pr_number, GITHUB_TOKEN)
        if not diff_text:
            raise ValueError("No diff fetched.")

        # 5. Run the Agent
        print("=== 🧠 AGENTIC AI REVIEW (Using Tools) ===")

        review_result = agent_executor.invoke({
            "diff": diff_text,
            "chat_history": []
        })

        review_text = review_result["output"]
        end_time = time.time()

        print("\n====================================")
        print("FINAL PULL-PANDA REVIEW")
        print("====================================")
        print(f"Review Generated in {end_time - start_time:.2f} seconds.")
        print("------------------------------------")
        print(review_text)
        print("------------------------------------")

        # 6. Post review comment on PR
        comment = post_review_comment(
            owner, repo, pr_number, GITHUB_TOKEN, review_text
        )
        if "html_url" in comment:
            print(f"✅ Review posted: {comment['html_url']}")
        else:
            print(f"⚠️ Failed to post review: {comment}")

    except (ValueError, KeyError, requests.RequestException) as e:
        print(f"❌ Critical Error: {e}")


if __name__ == "__main__":
    main()
