# Review for PR #22 (Prompt: Zero-shot)
**Score:** 8.38/10

---

## 🤖 AI Review

# Step-by-step analysis of the problem:
1. **The PR diff is too large and unfocused**: The PR includes multiple files with varying changes, which makes it difficult to review and understand the purpose of the PR. According to the engineering coding standards, PRs should be small and focused.
2. **No unit tests are included**: The PR diff does not include any unit tests for the new logic, which is a requirement according to the engineering coding standards.
3. **Secrets are committed**: The `config.json` file includes secrets, which should not be committed according to the engineering coding standards. Instead, `.env` files should be used.
4. **Invalid JSON**: The `broken.json` file contains invalid JSON syntax, which will cause errors when trying to parse the file.
5. **Conflicting code**: The `conflict_test.py` file contains conflicting code, which will cause errors when trying to run the code.
6. **Corrupt code**: The `corrupt_code.py` file contains corrupt code, which will cause errors when trying to run the code.
7. **Trailing whitespace**: The `delete_test.py` file contains trailing whitespace, which is not allowed according to the engineering coding standards.
8. **Huge test file**: The `huge_test_file.py` file is too large and contains repetitive code, which is not necessary.

# Fixed solution:
To fix these issues, the PR should be split into smaller, focused PRs, each with its own unit tests and without secrets. The invalid JSON, conflicting code, and corrupt code should be fixed. The trailing whitespace should be removed, and the huge test file should be refactored to be smaller and more efficient.

Here is an example of how the `broken.json` file could be fixed:
```json
{
    "broken": true
}
```

And here is an example of how the `conflict_test.py` file could be fixed:
```python
def version():
    return "new version"
```

The `corrupt_code.py` file should be completely refactored to contain valid Python code.

The `config.json` file should be removed and replaced with a `.env` file that contains the secrets.

The `huge_test_file.py` file should be refactored to be smaller and more efficient.

# Explanation of changes:
* **Split the PR into smaller, focused PRs**: Each PR should have a single, clear purpose and should include unit tests for the new logic.
* **Fix invalid JSON**: The `broken.json` file should be fixed to contain valid JSON syntax.
* **Fix conflicting code**: The `conflict_test.py` file should be fixed to contain valid Python code.
* **Fix corrupt code**: The `corrupt_code.py` file should be completely refactored to contain valid Python code.
* **Remove secrets**: The `config.json` file should be removed and replaced with a `.env` file that contains the secrets.
* **Remove trailing whitespace**: The `delete_test.py` file should be fixed to remove the trailing whitespace.
* **Refactor huge test file**: The `huge_test_file.py` file should be refactored to be smaller and more efficient.

# Tests and example uses:
To test the changes, the following steps can be taken:
* Run the unit tests for each PR to ensure that the new logic is working correctly.
* Verify that the `broken.json` file contains valid JSON syntax.
* Verify that the `conflict_test.py` file contains valid Python code.
* Verify that the `corrupt_code.py` file contains valid Python code.
* Verify that the secrets are not committed and are instead stored in a `.env` file.
* Verify that the `delete_test.py` file does not contain trailing whitespace.
* Verify that the `huge_test_file.py` file is smaller and more efficient.

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
Run started:2025-11-16 20:49:16.690603

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
