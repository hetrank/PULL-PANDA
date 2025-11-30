"""
Static analysis module for Pull Request code review.

This module provides functionality to detect changed files in a PR diff,
identify their programming languages, and run appropriate static analyzers
on only the modified files.
"""

import re
import subprocess
from typing import Dict, List

# =====================================================
# 1. Static Analysis Configuration
# =====================================================

# Language-to-File-Extension Map
FILE_LANG_MAP = {
    "py": "python",
    "js": "javascript", "jsx": "javascript", "ts": "javascript",
    "tsx": "javascript",
    "java": "java",
    "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "h": "cpp", "hpp": "cpp",
    "go": "go",
    "kt": "kotlin",
    "rs": "rust"
}

# Static Analyzer Commands Map (Tool Name, Base Command List)
# NOTE: Tools must be installed locally and in PATH for this to work.
# The file paths will be appended to the base command list before execution.
ANALYZERS = {
    "python": [
        ("🧩 Pylint", ["pylint", "--exit-zero"]),
        ("🎯 Flake8", ["flake8", "--exit-zero"]),
        ("🔒 Bandit", ["bandit", "-r"]),
        ("🧠 Mypy", ["mypy", "--ignore-missing-imports"]),
    ],
    "javascript": [
        ("ESLint", ["eslint", "--max-warnings=0"]),
        # Add TypeScript analysis here if needed
    ],
    "java": [("Checkstyle", ["checkstyle", "-c", "/google_checks.xml"])],
    "cpp": [("Cppcheck", ["cppcheck", "--enable=all", "--quiet"])],
    "go": [("Staticcheck", ["staticcheck"])],
    "rust": [("Clippy", ["cargo", "clippy", "--", "-D", "warnings"])]
}

# =====================================================
# 2. Optimized Static Analysis Functions
# =====================================================


def get_changed_files_and_languages(diff_text: str) -> Dict[str, List[str]]:
    """
    Infers file types/languages and gets paths from the PR diff.
    Returns a dict: { 'language': [list of file paths] }
    """
    # Finds lines that start with '+++ b/' and captures the file path
    file_paths = re.findall(r'\+\+\+ b/(.*)', diff_text)

    changed_files: Dict[str, List[str]] = {}

    for path in file_paths:
        ext = path.split('.')[-1].lower()
        lang = FILE_LANG_MAP.get(ext)
        if lang:
            # Add file path to the list for its detected language
            changed_files.setdefault(lang, []).append(path)

    return changed_files


def run_static_analysis(diff_text: str) -> str:
    """
    Runs appropriate static analyzers on ONLY the changed files and
    compiles results. Returns a single string containing all analyzer outputs.
    """
    changed_files_map = get_changed_files_and_languages(diff_text)

    if not changed_files_map:
        return ("⚠️ No recognizable programming language files found in "
                "PR diff to analyze.")

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

            try:
                # Run the command
                process = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    check=False,  # Do not raise exception on non-zero exit
                    timeout=120  # Increased timeout for safety
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
            except (OSError, RuntimeError) as error:
                results.append(
                    f"| {name}: ❌ Error running analyzer: {error}"
                )

    return "\n\n".join(results)
