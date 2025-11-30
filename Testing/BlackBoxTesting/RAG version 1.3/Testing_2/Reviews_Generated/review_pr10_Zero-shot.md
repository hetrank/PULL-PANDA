# Review for PR #10 (Prompt: Zero-shot)
**Score:** 7.45/10

---

## 🤖 AI Review

### Review of GitHub PR Diff, Static Analysis, and Retrieved Context

#### Bugs and Mistakes:

1. **Missing files**: The static analysis results indicate that `delete_test2.py` does not exist. This is confirmed by the `FileNotFoundError` in the Flake8 results and the "No such file or directory" error in the Mypy results.
2. **Trailing whitespace**: The Flake8 results show a trailing whitespace warning in `delete_test.py`.
3. **No type hints**: The retrieved context specifies that all functions must have type hints, but there are no functions in the provided diff.
4. **No docstrings**: The retrieved context requires public functions to have docstrings, but there are no functions in the provided diff.
5. **No unit tests**: The retrieved context states that PRs should include unit tests for new logic, but there are no tests in the provided diff.
6. **PR size**: The retrieved context recommends small and focused PRs, but the purpose of this PR is unclear due to the lack of context.

#### Suggestions:

1. **Verify file existence**: Ensure that `delete_test2.py` exists and is correctly referenced in the PR.
2. **Remove trailing whitespace**: Remove the trailing whitespace in `delete_test.py` to fix the Flake8 warning.
3. **Add type hints and docstrings**: Once functions are added, include type hints and docstrings to comply with the coding standards.
4. **Include unit tests**: Add unit tests for any new logic introduced in the PR.
5. **Refine PR purpose**: Clarify the purpose of the PR and ensure it is small and focused.
6. **Use `black` for formatting**: Run `black` on the code to ensure it is formatted according to the coding standards.
7. **Avoid global variables**: Pass state explicitly instead of using global variables, if applicable.

#### Additional Recommendations:

1. **Provide more context**: Include a clear description of the changes made in the PR and their purpose.
2. **Review coding standards**: Familiarize yourself with the coding standards and ensure that all requirements are met.
3. **Run static analysis locally**: Run static analysis tools locally before submitting a PR to catch errors and warnings early.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (2 files changed) ===

| 🧩 Pylint:
```
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
```

| 🎯 Flake8:
```
delete_test.py:1:22: W291 trailing whitespace
delete_test2.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'delete_test2.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 18:32:51.691729

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 1
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
	.\delete_test2.py (No such file or directory)
```

| 🧠 Mypy:
```
mypy: can't read file 'delete_test2.py': No such file or directory
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
