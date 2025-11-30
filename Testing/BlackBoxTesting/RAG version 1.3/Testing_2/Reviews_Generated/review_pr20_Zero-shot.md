# Review for PR #20 (Prompt: Zero-shot)
**Score:** 7.94/10

---

## 🤖 AI Review

## Review of the GitHub PR Diff, Static Analysis, and Retrieved Context

### Bugs and Mistakes

1. **Committing secrets**: The `config.json` file contains a "secrets" key, which is a clear violation of the engineering coding standards. Secrets should never be committed to the repository.
2. **Invalid syntax**: The `corrupt_code.py` file contains invalid syntax, including a `print` statement with a syntax error and a class definition with invalid syntax.
3. **Conflicting changes**: The `conflict_test.py` file contains conflicting changes, indicated by the `<<<<<<< HEAD` and `>>>>>>> incoming-change` markers. This suggests that the changes were not properly merged.
4. **Trailing whitespace**: The `delete_test.py` file contains trailing whitespace, which is reported by Flake8.
5. **Large PR**: The PR contains a large number of changes, including many test files. This makes it difficult to review and understand the changes.

### Suggestions

1. **Remove secrets from the commit**: Remove the "secrets" key from the `config.json` file and use a `.env` file to store sensitive information.
2. **Fix invalid syntax**: Fix the syntax errors in the `corrupt_code.py` file.
3. **Resolve conflicts**: Resolve the conflicts in the `conflict_test.py` file and remove the conflicting changes markers.
4. **Remove trailing whitespace**: Remove the trailing whitespace from the `delete_test.py` file.
5. **Split the PR into smaller PRs**: Split the PR into smaller, more focused PRs that address specific changes. This will make it easier to review and understand the changes.
6. **Add unit tests**: Add unit tests for the new logic introduced in the PR.
7. **Use type hints**: Use type hints for all functions, as required by the engineering coding standards.
8. **Use black for formatting**: Use black to format the code, as required by the engineering coding standards.
9. **Add docstrings**: Add docstrings to all public functions, as required by the engineering coding standards.

### Example of how to fix some of the issues

For example, to fix the invalid syntax in the `corrupt_code.py` file, you could change the code to:
```python
def this_is_broken():
    print("hello")
```
To fix the conflicting changes in the `conflict_test.py` file, you could resolve the conflicts and remove the conflicting changes markers:
```python
def version():
    return "new version"
```
To remove the secrets from the `config.json` file, you could change the code to:
```json
{
    "name": "myapp",
    "version": "1.0"
}
```
And use a `.env` file to store sensitive information:
```makefile
SECRETS=should_not_commit
```
Note: The above examples are just illustrations and may not be the exact solution to the problems.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (13 files changed) ===

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
```

| 🔒 Bandit:
```
Run started:2025-11-16 20:48:20.540274

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
Files skipped (12):
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
