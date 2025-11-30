# Review for PR #13 (Prompt: Zero-shot)
**Score:** 8.52/10

---

## 🤖 AI Review

# Step-by-step analysis of the problem:
1. **Invalid Python syntax**: The `corrupt_code.py` file contains invalid Python syntax, including a function definition with a `print` statement inside the function definition, and a class definition with invalid syntax.
2. **Missing files**: The static analysis results indicate that several files (`corrupt_code.py`, `delete_test2.py`, `huge_test_file.py`, `missing_import_test.py`) do not exist or cannot be read.
3. **Trailing whitespace**: The `delete_test.py` file has a trailing whitespace on line 1, which is reported by Flake8.
4. **Large PR**: The PR diff is truncated, but it appears to include a large number of files and lines of code, which may indicate that the PR is too large and should be split into smaller, more focused PRs.
5. **No type hints**: The `corrupt_code.py` file does not include type hints for the function definition, which is required by the engineering coding standards.
6. **No docstring**: The `corrupt_code.py` file does not include a docstring for the function definition, which is required by the engineering coding standards.
7. **No unit tests**: There is no indication that unit tests have been added for the new logic in the PR.

# Fixed solution:
To fix the issues in the PR, the following steps should be taken:
* Remove the invalid Python syntax from the `corrupt_code.py` file and replace it with valid syntax.
* Ensure that all files included in the PR exist and can be read.
* Remove the trailing whitespace from the `delete_test.py` file.
* Split the PR into smaller, more focused PRs if necessary.
* Add type hints to the function definition in the `corrupt_code.py` file.
* Add a docstring to the function definition in the `corrupt_code.py` file.
* Add unit tests for the new logic in the PR.

Here is an example of how the `corrupt_code.py` file could be rewritten to fix the issues:
```python
def this_is_broken() -> None:
    """Prints a message to the console."""
    print("Hello")

class MyClass:
    """A simple class."""
    def __init__(self) -> None:
        pass
```
# Explanation of changes:
* **Removed invalid syntax**: The invalid Python syntax was removed from the `corrupt_code.py` file and replaced with valid syntax.
* **Added type hints**: Type hints were added to the function definition in the `corrupt_code.py` file.
* **Added docstring**: A docstring was added to the function definition in the `corrupt_code.py` file.
* **Removed trailing whitespace**: The trailing whitespace was removed from the `delete_test.py` file.

# Tests and example uses:
To test the changes, the following steps can be taken:
* Run the unit tests for the new logic in the PR.
* Verify that the `corrupt_code.py` file can be imported and used without errors.
* Verify that the `delete_test.py` file can be imported and used without errors.

Example use cases:
```python
from corrupt_code import this_is_broken

this_is_broken()  # prints "Hello"

from corrupt_code import MyClass

obj = MyClass()
```

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (5 files changed) ===

| 🧩 Pylint:
```
************* Module corrupt_code.py
corrupt_code.py:1:0: F0001: No module named corrupt_code.py (fatal)
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
************* Module huge_test_file.py
huge_test_file.py:1:0: F0001: No module named huge_test_file.py (fatal)
************* Module missing_import_test.py
missing_import_test.py:1:0: F0001: No module named missing_import_test.py (fatal)
```

| 🎯 Flake8:
```
corrupt_code.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'corrupt_code.py'
delete_test.py:1:22: W291 trailing whitespace
delete_test2.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'delete_test2.py'
huge_test_file.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'huge_test_file.py'
missing_import_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'missing_import_test.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 18:50:56.828392

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
Files skipped (4):
	.\corrupt_code.py (No such file or directory)
	.\delete_test2.py (No such file or directory)
	.\huge_test_file.py (No such file or directory)
	.\missing_import_test.py (No such file or directory)
```

| 🧠 Mypy:
```
mypy: can't read file 'corrupt_code.py': No such file or directory
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
