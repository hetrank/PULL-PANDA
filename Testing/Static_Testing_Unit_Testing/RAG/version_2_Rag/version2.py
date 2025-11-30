"""
AI-powered PR reviewer with RAG context and static analysis.

This module provides comprehensive code review capabilities by combining:
- GitHub PR diff analysis
- Repository-wide RAG (Retrieval Augmented Generation) context
- Static analysis tool integration
- Automated review posting to GitHub
"""

import os
import re
import subprocess
from typing import Dict, List

import requests
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# =====================================================
# 1. ENV & CONFIG
# =====================================================
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")
OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
PR_NUMBER = os.getenv("PR_NUMBER")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

if not (GITHUB_TOKEN and OWNER and REPO and PR_NUMBER):
    print("GitHub configuration incomplete. Some steps may be skipped.")

# Map extensions to languages
FILE_LANG_MAP = {
    "py": "python",
    "js": "javascript", "jsx": "javascript",
    "ts": "javascript", "tsx": "javascript",
    "java": "java",
    "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "h": "cpp", "hpp": "cpp",
    "go": "go",
    "kt": "kotlin",
    "rs": "rust"
}

# Static analyzers for each language
ANALYZERS = {
    "python": [
        ("Pylint", ["pylint", "--exit-zero"]),
        ("Flake8", ["flake8", "--exit-zero"]),
        ("Bandit", ["bandit", "-r"]),
        ("Mypy", ["mypy", "--ignore-missing-imports"]),
    ],
    "javascript": [("ESLint", ["eslint", "--max-warnings=0"])],
    "cpp": [("Cppcheck", ["cppcheck", "--enable=all", "--quiet"])],
    "java": [("Checkstyle", ["checkstyle", "-c", "/google_checks.xml"])],
}


# =====================================================
# 2. GITHUB HELPERS
# =====================================================
def fetch_pr_data(repo_owner, repo_name, pr_num, token):
    """
    Fetch PR data from GitHub API.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub authentication token

    Returns:
        Dictionary containing PR data

    Raises:
        ValueError: If GitHub API returns an error
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_num}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"GitHub API Error: {response.json()}")
    return response.json()


def fetch_pr_diff(repo_owner, repo_name, pr_num, token):
    """
    Fetch PR diff and title from GitHub.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub authentication token

    Returns:
        Tuple of (diff_text, pr_title)
    """
    pr_data = fetch_pr_data(repo_owner, repo_name, pr_num, token)
    diff_url = pr_data["diff_url"]
    diff_text = requests.get(
        diff_url,
        headers={"Authorization": f"token {token}"},
        timeout=30
    ).text
    return diff_text, pr_data["title"]


def post_review_comment(repo_owner, repo_name, pr_num, token, review_body):
    """
    Post AI-generated review as a comment on the GitHub Pull Request.

    Args:
        repo_owner: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub authentication token
        review_body: The review comment text

    Returns:
        API response dictionary or None if failed
    """
    url = (f"https://api.github.com/repos/{repo_owner}/{repo_name}/"
           f"issues/{pr_num}/comments")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-PR-Reviewer"
    }
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Review posted: {data.get('html_url', 'URL not found')}")
        return data

    print(f"Failed to post review. GitHub response: {response.status_code}")
    print(response.text)
    return None


# =====================================================
# 3. STATIC ANALYSIS
# =====================================================
def get_changed_files_and_languages(diff_text: str) -> Dict[str, List[str]]:
    """
    Extract changed files and their languages from diff.

    Args:
        diff_text: Git diff text

    Returns:
        Dictionary mapping language names to lists of file paths
    """
    file_paths = re.findall(r'\+\+\+ b/(.*)', diff_text)
    changed = {}
    for path in file_paths:
        ext = path.split('.')[-1].lower()
        lang = FILE_LANG_MAP.get(ext)
        if lang:
            changed.setdefault(lang, []).append(path)
    return changed


def run_static_analysis(diff_text: str) -> str:
    """
    Run static analysis tools on changed files.

    Args:
        diff_text: Git diff text

    Returns:
        String containing formatted analysis results
    """
    changed = get_changed_files_and_languages(diff_text)
    if not changed:
        return "No supported language files detected."

    results = []
    for lang, files in changed.items():
        results.append(f"=== Static Analysis for {lang.upper()} ===")
        analyzers = ANALYZERS.get(lang, [])
        if not analyzers:
            results.append(f"No analyzer configured for {lang}")
            continue

        for name, base_cmd in analyzers:
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                results.append(f"| {name}: Skipped (files not found locally).")
                continue

            cmd = base_cmd + existing_files
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False
                )
                out = proc.stdout.strip()
                err = proc.stderr.strip()
                if out or err:
                    results.append(f"| {name} Output:\n```\n{out or err}\n```")
                else:
                    results.append(f"| {name}: No issues found.")
            except FileNotFoundError:
                results.append(f"| {name}: Tool not installed.")
            except subprocess.TimeoutExpired:
                results.append(f"| {name}: Timed out.")
            except (OSError, ValueError) as e:
                results.append(f"| {name}: Error - {e}")

    return "\n\n".join(results)


# =====================================================
# 4. RAG INDEXING + RETRIEVAL
# =====================================================
def index_repository(repo_path: str = ".",
                     persist_dir: str = "./repo_index") -> None:
    """
    Build vector index for repository files.

    Args:
        repo_path: Path to repository root
        persist_dir: Directory to persist the vector index
    """
    print("Building vector index for repository...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    documents = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".js", ".cpp", ".java", ".md")):
                try:
                    path = os.path.join(root, file)
                    loader = TextLoader(path, encoding="utf-8")
                    documents.extend(loader.load())
                except (IOError, OSError, UnicodeDecodeError) as e:
                    print(f"Skipped {file}: {e}")

    if not documents:
        print("No documents found to index.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    texts = splitter.split_documents(documents)
    Chroma.from_documents(texts, embeddings, persist_directory=persist_dir)

    print(f"Repository indexed and saved at: {persist_dir}")


def load_vector_index(persist_dir: str = "./repo_index") -> Chroma:
    """
    Load existing vector index from disk.

    Args:
        persist_dir: Directory containing the persisted index

    Returns:
        Chroma vectorstore instance

    Raises:
        FileNotFoundError: If index doesn't exist
    """
    if not os.path.exists(persist_dir):
        raise FileNotFoundError(
            f"Vector index not found at {persist_dir}. "
            f"Please run index_repository() first."
        )
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)


def query_repo_context(query: str, k: int = 4,
                       persist_dir: str = "./repo_index",
                       max_unique_chunks: int = 3) -> str:
    """
    Query repository context using RAG.

    Args:
        query: Search query
        k: Number of results to retrieve
        persist_dir: Directory containing the persisted index
        max_unique_chunks: Maximum unique chunks to return

    Returns:
        Concatenated text from retrieved documents
    """
    vectordb = load_vector_index(persist_dir)
    docs = vectordb.similarity_search(query, k=k)
    seen = set()
    unique_texts = []
    for doc in docs:
        content = getattr(doc, "page_content", None) or str(doc)
        normalized = content.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_texts.append(normalized)
        if len(unique_texts) >= max_unique_chunks:
            break
    return "\n\n".join(unique_texts)


# =====================================================
# 5. GROQ + STRUCTURED REVIEW FORMAT
# =====================================================
try:
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        api_key=GROQ_API_KEY
    )
except (ValueError, RuntimeError):
    print("llama-3.3-70b-versatile not available, "
          "switching to llama-3.1-8b-instant.")
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.3,
        api_key=GROQ_API_KEY
    )

parser = StrOutputParser()

structured_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a senior software engineer reviewing a GitHub Pull Request. "
     "Write the output ONLY in this format:\n\n"
     "Code Review: <PR Title>\n\n"
     "Issues\n"
     "<bullet or numbered list of key problems found in code>\n\n"
     "Suggestions\n"
     "<bullet or numbered list of improvements or refactorings>\n\n"
     "Verdict\n"
     "<final evaluation with summary and optionally improved code "
     "snippets>\n\n"
     "Be precise, detailed, and professional."),
    ("human",
     "Repository context:\n{context}\n\n"
     "Pull Request Diff:\n{diff}\n\n"
     "Static Analysis Results:\n{static}\n\n"
     "PR Title: {pr_title}\n\n"
     "Generate the structured review now.")
])

review_chain = structured_prompt | llm | parser


def safe_truncate(text: str, max_len: int = 8000) -> str:
    """
    Truncate text to maximum length if needed.

    Args:
        text: Text to truncate
        max_len: Maximum length

    Returns:
        Truncated text with indication if truncated
    """
    return text if len(text) <= max_len else text[:max_len] + "\n... (truncated)"


# =====================================================
# 6. MAIN EXECUTION
# =====================================================
def main():
    """Main execution function for the PR reviewer."""
    try:
        if not all([GITHUB_TOKEN, OWNER, REPO, PR_NUMBER]):
            raise ValueError("Missing GitHub config in .env")

        print("Fetching PR diff and title from GitHub...")
        diff, pr_title = fetch_pr_diff(OWNER, REPO, PR_NUMBER, GITHUB_TOKEN)
        print(f"PR Title: {pr_title}\n")

        print("Running targeted static analysis...")
        analysis_results = run_static_analysis(diff)
        print("Static analysis complete.\n")

        print("Checking repository index...")
        if not os.path.exists("./repo_index"):
            index_repository(".", "./repo_index")
        else:
            print("Existing index found.\n")

        print("Retrieving repository context (RAG)...")
        context = query_repo_context(
            "code structure and utilities",
            k=8,
            persist_dir="./repo_index",
            max_unique_chunks=3
        )
        print("Context retrieved.\n")

        print("Generating AI structured PR review...")
        review = review_chain.invoke({
            "context": safe_truncate(context, 3000),
            "diff": safe_truncate(diff, 3000),
            "static": safe_truncate(analysis_results, 2000),
            "pr_title": pr_title
        })

        print("\n==============================")
        print("AI STRUCTURED CODE REVIEW")
        print("==============================\n")
        print(review)
        print("\n==============================\n")

        print("Posting structured review to GitHub...")
        comment_text = (f"{review}\n\n"
                        f"(Generated via AI Code Reviewer with RAG Context)")
        comment = post_review_comment(
            OWNER, REPO, PR_NUMBER, GITHUB_TOKEN, comment_text
        )

        if comment:
            print("Successfully commented on the PR.")
        else:
            print("Review generated but failed to post to GitHub.")

    except (ValueError, KeyError, requests.RequestException) as e:
        print("Error:", str(e))


if __name__ == "__main__":
    main()
