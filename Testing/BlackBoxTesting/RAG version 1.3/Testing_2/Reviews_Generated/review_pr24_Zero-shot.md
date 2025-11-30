# Review for PR #24 (Prompt: Zero-shot)
**Score:** 7.45/10

---

## 🤖 AI Review

### Review of the GitHub PR Diff, Static Analysis, and Retrieved Context

#### Bugs and Mistakes:

1. **Committing secrets**: The `config.json` file contains secrets that should not be committed to the repository. This is a serious security issue.
2. **Invalid JSON**: The `broken.json` file contains invalid JSON syntax, which will cause errors when trying to parse it.
3. **Corrupt code**: The `corrupt_code.py` file contains invalid Python syntax, which will cause errors when trying to run it.
4. **Conflicting code**: The `conflict_test.py` file contains conflicting code, which will cause errors when trying to run it.
5. **Trailing whitespace**: The `delete_test.py` file contains trailing whitespace, which is not allowed according to the coding standards.
6. **Large PR**: The PR is too large and contains many unrelated changes, which makes it difficult to review and test.
7. **Missing type hints**: The code does not contain type hints, which is required by the coding standards.
8. **Missing docstrings**: The code does not contain docstrings, which is required by the coding standards for public functions.
9. **Invalid file names**: Some file names, such as `conflict_test.py` and `corrupt_code.py`, do not follow the coding standards.

#### Suggestions:

1. **Remove secrets from the repository**: Remove the `config.json` file and use a `.env` file to store secrets instead.
2. **Fix invalid JSON**: Fix the invalid JSON syntax in the `broken.json` file.
3. **Fix corrupt code**: Fix the invalid Python syntax in the `corrupt_code.py` file.
4. **Resolve conflicts**: Resolve the conflicts in the `conflict_test.py` file.
5. **Remove trailing whitespace**: Remove the trailing whitespace from the `delete_test.py` file.
6. **Split the PR into smaller PRs**: Split the PR into smaller PRs that contain related changes only.
7. **Add type hints**: Add type hints to the code to make it more readable and maintainable.
8. **Add docstrings**: Add docstrings to the code to make it more readable and maintainable.
9. **Follow coding standards**: Follow the coding standards for file names, formatting, and other aspects of the code.

#### Best Practices:

1. **Use a linter**: Use a linter, such as `pylint` or `flake8`, to catch errors and enforce coding standards.
2. **Use a formatter**: Use a formatter, such as `black`, to format the code consistently.
3. **Write unit tests**: Write unit tests to ensure that the code works as expected.
4. **Use a version control system**: Use a version control system, such as Git, to track changes and collaborate with others.
5. **Follow security best practices**: Follow security best practices, such as not committing secrets, to ensure the security of the code and data.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (14 files changed) ===

| 🧩 Pylint:
```
************* Module conflict_test.py
conflict_test.py:1:0: F0001: No module named conflict_test.py (fatal)
************* Module corrupt_code.py
corrupt_code.py:1:0: F0001: No module named corrupt_code.py (fatal)
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
************* Module huge_test_file.py
huge_test_file.py:1:0: F0001: No module named huge_test_file.py (fatal)
************* Module missing_import_test.py
missing_import_test.py:1:0: F0001: No module named missing_import_test.py (fatal)
************* Module module_a.py
module_a.py:1:0: F0001: No module named module_a.py (fatal)
************* Module module_b.py
module_b.py:1:0: F0001: No module named module_b.py (fatal)
************* Module multi.py
multi.py:1:0: F0001: No module named multi.py (fatal)
************* Module perf_test.py
perf_test.py:1:0: F0001: No module named perf_test.py (fatal)
************* Module security_test.py
security_test.py:1:0: F0001: No module named security_test.py (fatal)
************* Module spam.py
spam.py:1:0: F0001: No module named spam.py (fatal)
************* Module standards_test.py
standards_test.py:1:0: F0001: No module named standards_test.py (fatal)
************* Module u.py
u.py:1:0: F0001: No module named u.py (fatal)
```

| 🎯 Flake8:
```
conflict_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'conflict_test.py'
corrupt_code.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'corrupt_code.py'
delete_test.py:1:22: W291 trailing whitespace
delete_test2.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'delete_test2.py'
huge_test_file.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'huge_test_file.py'
missing_import_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'missing_import_test.py'
module_a.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'module_a.py'
module_b.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'module_b.py'
multi.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'multi.py'
perf_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'perf_test.py'
security_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'security_test.py'
spam.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'spam.py'
standards_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'standards_test.py'
u.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'u.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 20:50:14.243039

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
Files skipped (13):
	.\conflict_test.py (No such file or directory)
	.\corrupt_code.py (No such file or directory)
	.\delete_test2.py (No such file or directory)
	.\huge_test_file.py (No such file or directory)
	.\missing_import_test.py (No such file or directory)
	.\module_a.py (No such file or directory)
	.\module_b.py (No such file or directory)
	.\multi.py (No such file or directory)
	.\perf_test.py (No such file or directory)
	.\security_test.py (No such file or directory)
	.\spam.py (No such file or directory)
	.\standards_test.py (No such file or directory)
	.\u.py (No such file or directory)
```

| 🧠 Mypy:
```
mypy: can't read file 'conflict_test.py': No such file or directory
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
