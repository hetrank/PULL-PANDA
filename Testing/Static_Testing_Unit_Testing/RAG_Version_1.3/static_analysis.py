"""
Static analysis module.

Detects changed files from a PR diff and runs matching static analysis tools
locally. Only formatting and linting fixes have been applied; no logic changed.
"""

import re
import subprocess
from typing import Dict, List

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

# Static Analyzer Commands Map
# NOTE: Tools must be installed locally and in PATH.
ANALYZERS = {
    "python": [
        ("🧩 Pylint", ["pylint", "--exit-zero"]),
        ("🎯 Flake8", ["flake8", "--exit-zero"]),
        ("🔒 Bandit", ["bandit", "-r"]),
        ("🧠 Mypy", ["mypy", "--ignore-missing-imports"]),
    ],
    "javascript": [
        ("ESLint", ["eslint", "--max-warnings=0"]),
    ],
    "java": [
        ("Checkstyle", ["checkstyle", "-c", "/google_checks.xml"]),
    ],
    "cpp": [
        ("Cppcheck", ["cppcheck", "--enable=all", "--quiet"]),
    ],
    "go": [
        ("Staticcheck", ["staticcheck"]),
    ],
    "rust": [
        ("Clippy", ["cargo", "clippy", "--", "-D", "warnings"]),
    ],
}


def get_changed_files_and_languages(diff_text: str) -> Dict[str, List[str]]:
    """
    Infers file types/languages and extracts file paths from the PR diff.

    Returns:
        dict mapping language -> list of changed file paths.
    """
    file_paths = re.findall(r"\+\+\+ b/(.*)", diff_text)
    changed_files: Dict[str, List[str]] = {}

    for path in file_paths:
        ext = path.split(".")[-1].lower()
        lang = FILE_LANG_MAP.get(ext)
        if lang:
            changed_files.setdefault(lang, []).append(path.lower())

    return changed_files


def run_static_analysis(diff_text: str) -> str:
    """
    Runs static analyzers on ONLY the changed files based on language.

    Returns:
        Aggregated string of analyzer outputs.
    """
    changed_files_map = get_changed_files_and_languages(diff_text)

    if not changed_files_map:
        return (
            "⚠️ No recognizable programming language files found "
            "in PR diff to analyze."
        )

    results: List[str] = []

    for lang, files in changed_files_map.items():
        results.append(
            f"=== 🔍 Targeted Static Analysis for "
            f"{lang.upper()} ({len(files)} files changed) ==="
        )

        analyzer_list = ANALYZERS.get(lang, [])
        if not analyzer_list:
            results.append(f"No analyzer configured for {lang}")
            continue

        for name, base_cmd in analyzer_list:
            full_cmd = base_cmd + files

            try:
                process = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )

                output = process.stdout.strip()
                error_output = process.stderr.strip()

                if output or error_output:
                    results.append(
                        f"| {name}:\n```\n"
                        f"{output if output else error_output}\n```"
                    )
                else:
                    results.append(f"| {name}: No issues found.")

            except FileNotFoundError:
                results.append(
                    f"| {name}: ❌ Command not found. "
                    "Is the tool installed locally and in PATH?"
                )
            except subprocess.TimeoutExpired:
                results.append(
                    f"| {name}: ❌ Execution timed out after 120 seconds."
                )
            except Exception as e:  # pylint: disable=broad-except
                results.append(f"| {name}: ❌ Error running analyzer: {e}")

    return "\n\n".join(results)
