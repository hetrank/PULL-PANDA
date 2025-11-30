# Review for PR #19 (Prompt: Zero-shot)
**Score:** 8.23/10

---

## 🤖 AI Review

# Step-by-step analysis of the problem:
1. **PR is too large and unfocused**: The PR includes multiple new files, each with different purposes. This goes against the engineering coding standards, which state that PRs should be small and focused.
2. **Committing secrets**: The `config.json` file includes secrets, which should not be committed according to the engineering coding standards. Instead, secrets should be stored in `.env` files.
3. **Invalid syntax in `corrupt_code.py`**: The `corrupt_code.py` file contains invalid Python syntax, which will cause a syntax error when trying to run the code.
4. **Conflicting changes in `conflict_test.py`**: The `conflict_test.py` file contains conflicting changes, which will cause a merge conflict when trying to merge the PR.
5. **Trailing whitespace in `delete_test.py`**: The `delete_test.py` file contains trailing whitespace, which is reported by Flake8.
6. **Missing type hints and docstrings**: None of the new functions in the PR include type hints or docstrings, which is required by the engineering coding standards.
7. **Static analysis errors**: The static analysis results show multiple errors, including `F0001` errors, which indicate that the modules cannot be imported.

# Fixed solution:
To fix these issues, the PR should be broken down into smaller, more focused PRs, each addressing a single issue. The secrets should be removed from the `config.json` file and stored in a `.env` file instead. The invalid syntax in `corrupt_code.py` should be fixed, and the conflicting changes in `conflict_test.py` should be resolved. The trailing whitespace in `delete_test.py` should be removed, and type hints and docstrings should be added to all new functions.

Here is an example of how the `config.json` file could be fixed:
```json
{
    "name": "myapp",
    "version": "1.0"
}
```
And the secrets could be stored in a `.env` file:
```makefile
SECRETS=should_not_commit
```
The `corrupt_code.py` file could be fixed by removing the invalid syntax:
```python
def this_is_broken():
    print("hello")
```
The `conflict_test.py` file could be fixed by resolving the conflicting changes:
```python
def version():
    return "new version"
```
The `delete_test.py` file could be fixed by removing the trailing whitespace:
```python
# test 5.1
```
And type hints and docstrings could be added to all new functions:
```python
def my_function(my_arg: str) -> None:
    """
    This function does something.

    Args:
        my_arg (str): The argument to the function.

    Returns:
        None
    """
    print(my_arg)
```
# Explanation of changes:
* **Broken down PR into smaller PRs**: Each PR should address a single issue to make it easier to review and test.
* **Removed secrets from `config.json`**: Secrets should not be committed and should be stored in a `.env` file instead.
* **Fixed invalid syntax in `corrupt_code.py`**: Invalid syntax will cause a syntax error when trying to run the code.
* **Resolved conflicting changes in `conflict_test.py`**: Conflicting changes will cause a merge conflict when trying to merge the PR.
* **Removed trailing whitespace in `delete_test.py`**: Trailing whitespace is reported by Flake8 and should be removed.
* **Added type hints and docstrings to new functions**: Type hints and docstrings are required by the engineering coding standards and make the code easier to understand.

# Tests and example uses:
To test the changes, you can run the code and verify that it works as expected. You can also use tools like Flake8 and Pylint to check for errors and warnings. For example:
```bash
flake8 my_file.py
pylint my_file.py
```

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (12 files changed) ===

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
standards_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'standards_test.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 20:48:08.289637

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
Files skipped (11):
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
