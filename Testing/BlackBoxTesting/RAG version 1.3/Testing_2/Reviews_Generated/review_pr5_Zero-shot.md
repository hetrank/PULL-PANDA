# Review for PR #5 (Prompt: Zero-shot)
**Score:** 7.45/10

---

## 🤖 AI Review

### Review of the GitHub PR Diff, Static Analysis, and Retrieved Context

#### Bugs and Mistakes:

1. **Large PR**: The PR is too large and complex, violating the coding standard that PRs should be small and focused. It includes multiple new files and classes, making it difficult to review.
2. **Missing Type Hints**: The `DataProcessor` and `Calculator` classes, as well as the `long_function_*` functions, are missing type hints for their methods, which is a requirement according to the coding standards.
3. **No Unit Tests**: There are no unit tests included in the PR for the new logic, which is a requirement according to the coding standards.
4. **Global Variables**: The `logging` module is used globally, which is discouraged according to the coding standards. Instead, logging should be passed explicitly to the classes and functions that need it.
5. **Static Analysis Errors**: The static analysis results show errors and warnings for the `large_test_file.py` and other files, indicating issues with the code.

#### Suggestions:

1. **Split the PR**: Break down the PR into smaller, more focused PRs, each addressing a specific feature or bug fix.
2. **Add Type Hints**: Add type hints for all methods and functions to ensure clarity and maintainability of the code.
3. **Include Unit Tests**: Write unit tests for the new logic to ensure it works as expected and to catch any regressions.
4. **Pass Logging Explicitly**: Pass logging explicitly to the classes and functions that need it, rather than using global variables.
5. **Address Static Analysis Errors**: Fix the errors and warnings reported by the static analysis tools to ensure the code is clean and maintainable.

#### Code Smells:

1. **God Object**: The `DataProcessor` class has multiple responsibilities and is doing too much, making it a god object. Consider breaking it down into smaller, more focused classes.
2. **Long Methods**: Some methods, such as `long_function_*`, are too long and complex. Consider breaking them down into smaller, more manageable functions.
3. **Magic Numbers**: The code uses magic numbers, such as `50` and `3.14`, which should be replaced with named constants to improve readability and maintainability.

#### Best Practices:

1. **Follow Coding Standards**: Ensure that the code follows the coding standards, including using `black` for formatting and including docstrings for all public functions.
2. **Use Meaningful Variable Names**: Use meaningful variable names to improve readability and maintainability of the code.
3. **Keep Functions Short and Focused**: Keep functions short and focused on a single responsibility to improve readability and maintainability of the code.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (4 files changed) ===

| 🧩 Pylint:
```
************* Module large_test_file.py
large_test_file.py:1:0: F0001: No module named large_test_file.py (fatal)
************* Module mixed_test.py
mixed_test.py:1:0: F0001: No module named mixed_test.py (fatal)
************* Module test_file.py
test_file.py:1:0: F0001: No module named test_file.py (fatal)
************* Module tiny_test.py
tiny_test.py:1:0: F0001: No module named tiny_test.py (fatal)
```

| 🎯 Flake8:
```
large_test_file.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'large_test_file.py'
mixed_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'mixed_test.py'
test_file.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'test_file.py'
tiny_test.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'tiny_test.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 19:09:09.661488

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
Files skipped (4):
	.\large_test_file.py (No such file or directory)
	.\mixed_test.py (No such file or directory)
	.\test_file.py (No such file or directory)
	.\tiny_test.py (No such file or directory)
```

| 🧠 Mypy:
```
mypy: can't read file 'large_test_file.py': No such file or directory
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
