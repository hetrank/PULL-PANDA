"""
Agentic RAG-based Pull Request Reviewer.

This module provides tools to clone repositories, checkout PRs,
analyze code diffs, and generate automated code reviews using LangChain and LLMs.
"""

import os
import subprocess
import shutil
from dotenv import load_dotenv

# =====================================================
# 0. IMPORTS (Updated for latest LangChain ecosystem)
# =====================================================
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# =====================================================
# 1. ENVIRONMENT SETUP
# =====================================================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env file")

# =====================================================
# 2. REPO MANAGEMENT UTILITIES
# =====================================================


def clone_or_update_repo(repo_url: str, repo_path: str):
    """Clone the repository or pull the latest changes."""
    if not os.path.exists(repo_path):
        print("Cloning repository...")
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)
    else:
        print("Repository exists — resetting to clean state...")
        subprocess.run(
            ["git", "-C", repo_path, "fetch", "origin"],
            check=True
        )
        subprocess.run(
            ["git", "-C", repo_path, "reset", "--hard", "origin/main"],
            check=True
        )


def checkout_pr(repo_path: str, pr_number: int):
    """Checkout the given PR branch safely."""
    print(f"Checking out PR #{pr_number}...")

    # Reset to main first to avoid conflicts
    subprocess.run(["git", "-C", repo_path, "checkout", "main"], check=True)

    # Check if the PR branch already exists
    result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--verify",
         f"pr_{pr_number}"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode == 0:
        print(f"Deleting existing local branch pr_{pr_number}...")
        subprocess.run(
            ["git", "-C", repo_path, "branch", "-D", f"pr_{pr_number}"],
            check=True
        )

    # Fetch the PR and checkout
    try:
        subprocess.run(
            ["git", "-C", repo_path, "fetch", "origin",
             f"pull/{pr_number}/head:pr_{pr_number}"],
            check=True
        )
        subprocess.run(
            ["git", "-C", repo_path, "checkout", f"pr_{pr_number}"],
            check=True
        )
    except subprocess.CalledProcessError as error:
        print(f"Error checking out PR (it might be merged or closed): {error}")
        subprocess.run(
            ["git", "-C", repo_path, "checkout", "main"],
            check=True
        )


def get_diff(repo_path: str) -> str:
    """Get the code difference for the current PR."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "diff", "main"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        print(f"Error getting diff: {error}")
        return ""


# =====================================================
# 3. RAG PIPELINE (INDEX + RETRIEVAL)
# =====================================================

def build_vectorstore(repo_path: str) -> Chroma:
    """
    Build a vector store from repository files.

    Args:
        repo_path: Path to the repository directory

    Returns:
        Chroma vector store containing indexed documents
    """
    print("Indexing repository files...")

    # Clean up old index
    persist_directory = "chroma_index"
    if os.path.exists(persist_directory):
        print("Removing old index...")
        shutil.rmtree(persist_directory)

    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    for root, _, files in os.walk(repo_path):
        if '.git' in root:
            continue

        for file in files:
            if file.endswith((".py", ".md", ".txt", ".js", ".ts",
                             ".jsx", ".tsx")):
                try:
                    file_path = os.path.join(root, file)
                    loader = TextLoader(file_path, encoding="utf-8")
                    file_docs = loader.load_and_split(text_splitter=splitter)
                    docs.extend(file_docs)
                except (IOError, OSError, UnicodeDecodeError) as error:
                    print(f"Error loading file {file_path}: {error}")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vector_store = Chroma.from_documents(
        docs,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    print("Repository indexed.")
    return vector_store


def retrieve_context(vector_store: Chroma, query: str) -> str:
    """Retrieve most relevant repo context using updated LangChain API."""
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    results = retriever.invoke(query)
    return "\n\n".join([r.page_content for r in results])


# =====================================================
# 4. AGENTIC REVIEW PIPELINE
# =====================================================

def build_agent(language_model, agent_tools):
    """Create a modern LangChain Agent using custom prompt."""
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert AI agent that reviews GitHub Pull Requests. "
         "You analyze diffs, identify potential issues, suggest improvements, "
         "and summarize changes. Be concise and focus on actionable feedback."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent_instance = create_react_agent(
        language_model,
        agent_tools,
        prompt=prompt
    )
    executor = AgentExecutor(
        agent=agent_instance,
        tools=agent_tools,
        verbose=True
    )
    return executor


def analyze_pr(diff_content: str, repo_context: str, agent_executor):
    """Ask the agent to review the PR using RAG context."""

    if not diff_content:
        return ("No code changes found between this branch and 'main'. "
                "Nothing to review.")

    query = f"""
You are a code reviewer. Analyze the following Pull Request diff and \
repository context.

Repository Context:
{repo_context}

---
Pull Request Diff:
{diff_content}
---

Please provide:
1. Summary of what was changed.
2. Potential bugs or issues.
3. Suggestions for improvement (e.g., code style, best practices, logic).
4. Overall review quality (e.g., Good / Needs Work).
"""
    result = agent_executor.invoke({"input": query})
    return result.get("output", str(result))


# =====================================================
# 5. MAIN EXECUTION
# =====================================================

if __name__ == "__main__":
    print("Starting Agentic RAG PR Reviewer...\n")

    OWNER = os.getenv("OWNER")
    REPO = os.getenv("REPO")

    if not OWNER or not REPO:
        raise ValueError("Missing OWNER or REPO in .env file")

    REPO_URL = f"https://github.com/{OWNER}/{REPO}.git"
    REPO_PATH = "./repo"
    PR_NUMBER = int(os.getenv("PR_NUMBER", "0"))

    if PR_NUMBER == 0:
        raise ValueError("Missing PR_NUMBER in .env file")

    clone_or_update_repo(REPO_URL, REPO_PATH)
    checkout_pr(REPO_PATH, PR_NUMBER)

    pr_diff = get_diff(REPO_PATH)
    vectorstore = build_vectorstore(REPO_PATH)
    CONTEXT = retrieve_context(
        vectorstore,
        f"Summarize and review PR #{PR_NUMBER} changes."
    )

    llm = ChatGroq(model="llama3-70b-8192")
    tools = []
    agent = build_agent(llm, tools)

    review = analyze_pr(pr_diff, CONTEXT, agent)

    print("\nPull Request Review Summary:\n")
    print(review)
