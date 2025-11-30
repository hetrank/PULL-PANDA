# Review for PR #5 (Prompt: Few-shot)
**Score:** 8.39/10

---

## 🤖 AI Review

- Code style: Missing type hints for function `add`, no docstring, and inconsistent formatting.
- Suggestion: Add type hints for `a` and `b`, include a docstring explaining the function's purpose, and run `black` for formatting.

- Code quality: No unit test added for the `add` function.
- Suggestion: Include a unit test for the `add` function to ensure its correctness.

- Code organization: Global print statement in the code.
- Suggestion: Remove the global print statement and consider using a main function or a testing framework for example usage. 

- Code style: Inconsistent naming convention in comments.
- Suggestion: Follow project lint rules for comments and naming conventions. 

- Best practice: The added comment does not follow standard documentation practices.
- Suggestion: Use standard Python docstring formatting for documentation comments.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (1 files changed) ===

| 🧩 Pylint:
```
************* Module example.py
example.py:1:0: F0001: No module named example.py (fatal)
```

| 🎯 Flake8:
```
example.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'example.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 13:53:56.761426

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 0
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
Files skipped (1):
	.\example.py (No such file or directory)
```

| 🧠 Mypy:
```
mypy: can't read file 'example.py': No such file or directory
```
```

---

## 🧠 Retrieved RAG Context

# Our Engineering Coding Standards

## Python
- All functions must have type hints.
- Use `black` for formatting.
- All public functions must have a docstring explaining args, returns, and raises.
- Avoid global variables. Pass state explicitly.

## General
- PRs should be small and focused.
- Always include unit tests for new logic.
- Do not commit secrets. Use .env files.
