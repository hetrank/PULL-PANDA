"""
AI-powered GitHub Pull Request reviewer with targeted static analysis.

This script fetches PR diffs from GitHub, runs static analyzers on changed files,
and generates comprehensive AI-powered reviews using LLM.
"""

import os
import subprocess
import re
from typing import Dict, List

import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_groq import ChatGroq

# =====================================================
# 1. Configuration & Setup (Manual Testing Maintained)
# =====================================================
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("API_KEY")  # Kept original name for consistency
GITHUB_OWNER = os.getenv("OWNER")
GITHUB_REPO = os.getenv("REPO")
GITHUB_PR_NUMBER = os.getenv("PR_NUMBER")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found. Please set it in .env file.")
if not (GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO and GITHUB_PR_NUMBER):
    print(
        "⚠️ WARNING: GitHub configuration (TOKEN, OWNER, REPO, PR_NUMBER) "
        "must be set in .env for full script execution."
    )
    # Allow code execution to proceed for analysis testing if diff is available

# Language-to-File-Extension Map
FILE_LANG_MAP = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "javascript",
    "tsx": "javascript",
    "java": "java",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "h": "cpp",
    "hpp": "cpp",
    "go": "go",
    "kt": "kotlin",
    "rs": "rust",
}

# Static Analyzer Commands Map (Targeted, requiring file paths as arguments)
ANALYZERS = {
    # Pylint, Flake8, Mypy, ESLint, etc. can accept file paths as arguments.
    "python": [
        ("🧩 Pylint", ["pylint", "--exit-zero"]),
        ("🎯 Flake8", ["flake8", "--exit-zero"]),
        (
            "🔒 Bandit",
            ["bandit", "-r"],
        ),  # Note: Bandit -r scans recursively from dir
        ("🧠 Mypy", ["mypy", "--ignore-missing-imports"]),
    ],
    "javascript": [
        ("ESLint", ["eslint", "--max-warnings=0"]),
        # Add TypeScript analysis here if needed, e.g., ["tsc", "--noEmit"]
    ],
    # Other examples (you must ensure these tools are installed locally)
    "java": [("Checkstyle", ["checkstyle", "-c", "/google_checks.xml"])],
    "cpp": [("Cppcheck", ["cppcheck", "--enable=all", "--quiet"])],
    "go": [("Staticcheck", ["staticcheck"])],
    "rust": [("Clippy", ["cargo", "clippy", "--", "-D", "warnings"])],
}


# =====================================================
# 2. Fetch PR Diff from GitHub (Unchanged for Manual Testing)
# =====================================================
def fetch_pr_diff(owner_name: str, repo_name: str, pr_num: int, token: str):
    """
    Fetch PR diff from GitHub API.

    Args:
        owner_name: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub personal access token

    Returns:
        str: The PR diff text

    Raises:
        requests.exceptions.HTTPError: If API request fails
    """
    url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pulls/{pr_num}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"GitHub API Error: {response.json()}"
        )
    diff_url = response.json()["diff_url"]
    diff = requests.get(diff_url, headers=headers, timeout=10).text
    return diff


# =====================================================
# 3. Optimized Static Analysis Functions
# =====================================================


def get_changed_files_and_languages(pr_diff_text: str) -> Dict[str, List[str]]:
    """
    Infer file types/languages and get paths from PR diff.

    Args:
        pr_diff_text: The PR diff text

    Returns:
        Dict mapping language names to lists of changed file paths
    """
    # Finds lines that start with '+++ b/' and captures the file path
    # Ignores files in .git, node_modules, etc. by common practice,
    # but not explicitly filtered here.
    file_paths = re.findall(r"\+\+\+ b/(.*)", pr_diff_text)

    changed_files: Dict[str, List[str]] = {}

    for path in file_paths:
        ext = path.split(".")[-1].lower()
        lang = FILE_LANG_MAP.get(ext)
        if lang:
            # Add file path to the list for its detected language
            changed_files.setdefault(lang, []).append(path)

    return changed_files


def run_static_analysis(pr_diff_text: str) -> str:
    """
    Run appropriate static analyzers on ONLY the changed files.

    Args:
        pr_diff_text: The PR diff text

    Returns:
        str: Formatted static analysis results
    """
    changed_files_map = get_changed_files_and_languages(pr_diff_text)

    if not changed_files_map:
        return (
            "⚠️ No recognizable programming language files found in "
            "PR diff to analyze."
        )

    results: List[str] = []

    # Loop through each detected language and its files
    for lang, files in changed_files_map.items():
        results.append(
            f"=== 🔍 Targeted Static Analysis for {lang.upper()} "
            f"({len(files)} files changed) ==="
        )

        analyzer_list = ANALYZERS.get(lang, [])

        if not analyzer_list:
            results.append(f"No analyzer configured for {lang}")
            continue

        for name, base_cmd in analyzer_list:
            # Concatenate base command with file list
            full_cmd = base_cmd + files

            # Use subprocess.run for reliable error handling
            try:
                # Run the command
                process = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    check=False,  # Do not raise exception on non-zero exit code
                    timeout=120,  # Increased timeout for safety during testing
                )

                output = process.stdout.strip()
                error_output = process.stderr.strip()

                # Check for output or errors
                if output or error_output:
                    results.append(
                        f"| {name}:\n```\n"
                        f"{output if output else error_output}\n```"
                    )
                else:
                    results.append(f"| {name}: No issues found.")

            except FileNotFoundError:
                results.append(
                    f"| {name}: ❌ Command not found. Is the tool "
                    f"installed locally and in PATH?"
                )
            except subprocess.TimeoutExpired:
                results.append(
                    f"| {name}: ❌ Execution timed out after 120 seconds."
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                results.append(f"| {name}: ❌ Error running analyzer: {exc}")

    return "\n\n".join(results)


# =====================================================
# 4. Post Review Comment to GitHub (Unchanged for Manual Testing)
# =====================================================
def post_review_comment(
    owner_name: str, repo_name: str, pr_num: int, token: str, review_body: str
):
    """
    Post a review comment to a GitHub PR.

    Args:
        owner_name: Repository owner username
        repo_name: Repository name
        pr_num: Pull request number
        token: GitHub personal access token
        review_body: The review comment text

    Returns:
        dict: GitHub API response with comment details

    Raises:
        requests.exceptions.HTTPError: If posting comment fails
    """
    url = (
        f"https://api.github.com/repos/{owner_name}/{repo_name}"
        f"/issues/{pr_num}/comments"
    )
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-PR-Reviewer-Script",
    }
    payload = {"body": review_body}
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code not in [200, 201]:
        raise requests.exceptions.HTTPError(
            f"❌ Failed to post comment: {response.json()}"
        )
    return response.json()


# =====================================================
# 5. Initialize Groq LLM (AI Reviewer)
# =====================================================
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=GROQ_API_KEY,
)
parser = StrOutputParser()

review_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior software engineer reviewing a GitHub Pull "
            "Request. "
            "You will receive the PR diff and static analysis results. "
            "The static analysis was run only on the files changed in the PR. "
            "Provide clear, concise, and technically correct review comments. "
            "Focus on correctness, maintainability, security, and readability. "
            "Use Markdown for clear formatting.",
        ),
        (
            "human",
            "Here is the PR diff:\n\n{diff}\n\n"
            "And here are static analysis results:\n\n{static}\n\n"
            "Now provide a professional GitHub PR review. Include actionable "
            "feedback, specific file references, and improvement suggestions.",
        ),
    ]
)

review_chain = review_prompt | llm | parser


# Helper to truncate cleanly for the LLM context limit
def safe_truncate(text: str, max_len: int = 4000) -> str:
    """
    Truncate text to fit within LLM context limit.

    Args:
        text: Text to truncate
        max_len: Maximum length in characters

    Returns:
        str: Truncated text with indicator if truncated
    """
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")
    if last_newline != -1:
        return truncated[:last_newline] + "\n\n... (Output truncated)"
    return truncated + " ... (Output truncated)"


# =====================================================
# 6. Main Logic
# =====================================================
if __name__ == "__main__":
    try:
        if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_PR_NUMBER]):
            raise ValueError(
                "Cannot proceed. Missing GitHub configuration for manual "
                "testing. Please check .env."
            )

        diff_text = fetch_pr_diff(
            GITHUB_OWNER, GITHUB_REPO, int(GITHUB_PR_NUMBER), GITHUB_TOKEN
        )
        print("✅ Diff fetched successfully.\n")

        print("🔍 Detecting language and running *targeted* static analysis...")
        # The key change: static analysis now targets specific files
        STATIC_OUTPUT = run_static_analysis(diff_text)

        print("🤖 Sending diff + analyzer results to AI reviewer...\n")

        truncated_diff = safe_truncate(
            diff_text, 8000
        )  # Increased limit for better context
        truncated_static = safe_truncate(STATIC_OUTPUT, 8000)

        review = review_chain.invoke(
            {"diff": truncated_diff, "static": truncated_static}
        )

        print("=== 🧠 AI REVIEW RESULT ===")
        print(review)
        print("===========================")

        print("📌 Posting review comment to GitHub...")
        comment = post_review_comment(
            GITHUB_OWNER, GITHUB_REPO, int(GITHUB_PR_NUMBER), GITHUB_TOKEN, review
        )
        print(f"✅ Review posted at: {comment['html_url']}")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print("Error:", str(exc))
