# Review for PR #11 (Prompt: Zero-shot)
**Score:** 8.23/10

---

## 🤖 AI Review

### Review of GitHub PR Diff, Static Analysis, and Retrieved Context

The provided PR diff, static analysis, and retrieved context reveal several issues that need to be addressed.

#### Bugs and Mistakes:

1. **Invalid Syntax**: The `corrupt_code.py` file contains invalid Python syntax, including:
	* `print("hello??` is missing a closing parenthesis.
	* `###$%#$%^&* random text ###` is not a valid Python statement.
	* `class ?? invalid syntax ###` is not a valid class definition.
	* `{]]]]]]]` is not a valid Python syntax.
2. **Missing Type Hints**: The `this_is_broken` function in `corrupt_code.py` is missing type hints for its parameters and return type.
3. **No Docstring**: The `this_is_broken` function in `corrupt_code.py` does not have a docstring explaining its purpose, parameters, return value, and any raised exceptions.
4. **Trailing Whitespace**: The `delete_test.py` file has a trailing whitespace on line 1, which is reported by Flake8.
5. **No Unit Tests**: There are no unit tests provided for the new logic in the PR.

#### Suggestions:

1. **Fix Invalid Syntax**: Correct the syntax errors in `corrupt_code.py` to make it a valid Python file.
2. **Add Type Hints**: Add type hints for the `this_is_broken` function parameters and return type.
3. **Add Docstring**: Add a docstring to the `this_is_broken` function to explain its purpose, parameters, return value, and any raised exceptions.
4. **Remove Trailing Whitespace**: Remove the trailing whitespace from `delete_test.py`.
5. **Add Unit Tests**: Provide unit tests for the new logic in the PR to ensure it works as expected.
6. **Use Black for Formatting**: Use the `black` tool to format the code according to the engineering coding standards.
7. **Avoid Global Variables**: Pass state explicitly instead of using global variables.
8. **Keep PRs Small and Focused**: Break down the PR into smaller, more focused changes to make it easier to review and test.

#### Additional Recommendations:

1. **Use a Linter**: Use a linter like Pylint or Flake8 to catch syntax errors and formatting issues before submitting the PR.
2. **Use a Type Checker**: Use a type checker like Mypy to catch type-related errors before submitting the PR.
3. **Test Code Thoroughly**: Test the code thoroughly before submitting the PR to ensure it works as expected.

By addressing these issues and following the engineering coding standards, the PR can be improved to meet the required standards.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (3 files changed) ===

| 🧩 Pylint:
```
************* Module corrupt_code.py
corrupt_code.py:1:0: F0001: No module named corrupt_code.py (fatal)
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
```

| 🎯 Flake8:
```
corrupt_code.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'corrupt_code.py'
delete_test.py:1:22: W291 trailing whitespace
delete_test2.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'delete_test2.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 19:00:35.635493

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
Files skipped (2):
	.\corrupt_code.py (No such file or directory)
	.\delete_test2.py (No such file or directory)
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
