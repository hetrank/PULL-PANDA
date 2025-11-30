# Review for PR #26 (Prompt: Zero-shot)
**Score:** 7.6/10

---

## 🤖 AI Review

### Review of GitHub PR Diff, Static Analysis, and Retrieved Context

#### Bugs and Mistakes:

1. **Static Analysis Errors**: The static analysis results show numerous errors, including `F0001: No module named` and `E902 FileNotFoundError`. These errors indicate that the code is trying to import or access non-existent modules or files. This could be due to incorrect file paths, missing dependencies, or incorrect import statements.
2. **Trailing Whitespace**: The Flake8 analysis reports a `W291 trailing whitespace` error in the `delete_test.py` file. This is a minor issue but should be addressed to maintain code cleanliness.
3. **Large PR Diff**: The PR diff is extremely large, with over 3000 lines changed. This is a clear violation of the engineering coding standards, which state that PRs should be small and focused.
4. **Missing Type Hints**: The retrieved context mentions that all functions must have type hints, but the provided code does not show any type hints. This is a potential bug, as type hints are essential for maintaining code readability and preventing type-related errors.
5. **No Unit Tests**: The engineering coding standards require unit tests for new logic, but the provided code does not show any unit tests. This is a significant mistake, as unit tests are crucial for ensuring code quality and preventing regressions.

#### Suggestions:

1. **Address Static Analysis Errors**: Fix the errors reported by the static analysis tools, including the `F0001` and `E902` errors. This may involve correcting file paths, adding missing dependencies, or fixing import statements.
2. **Refactor Large PR Diff**: Break down the large PR diff into smaller, more focused PRs. This will make it easier to review and test the code, and will help maintain the quality of the codebase.
3. **Add Type Hints**: Add type hints to all functions, as required by the engineering coding standards. This will improve code readability and prevent type-related errors.
4. **Write Unit Tests**: Write unit tests for the new logic, as required by the engineering coding standards. This will ensure that the code is thoroughly tested and will prevent regressions.
5. **Use Black for Formatting**: Use the `black` tool to format the code, as required by the engineering coding standards. This will maintain code consistency and readability.
6. **Avoid Global Variables**: Pass state explicitly, as required by the engineering coding standards. This will prevent global variable-related issues and make the code more maintainable.

#### Example of Corrected Code:

```python
# Example of a function with type hints
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers."""
    return a + b
```

```python
# Example of a unit test
import unittest

class TestAddNumbers(unittest.TestCase):
    def test_add_numbers(self):
        self.assertEqual(add_numbers(2, 3), 5)
```

By addressing the bugs and mistakes, and following the suggestions, the code can be improved to meet the engineering coding standards and maintain a high level of quality.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (15 files changed) ===

| 🧩 Pylint:
```
************* Module conflict_test.py
conflict_test.py:1:0: F0001: No module named conflict_test.py (fatal)
************* Module corrupt_code.py
corrupt_code.py:1:0: F0001: No module named corrupt_code.py (fatal)
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
************* Module dep.py
dep.py:1:0: F0001: No module named dep.py (fatal)
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
dep.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'dep.py'
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
Run started:2025-11-16 20:51:12.653530

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
Files skipped (14):
	.\conflict_test.py (No such file or directory)
	.\corrupt_code.py (No such file or directory)
	.\delete_test2.py (No such file or directory)
	.\dep.py (No such file or directory)
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
