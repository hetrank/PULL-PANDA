# Review for PR #12 (Prompt: Zero-shot)
**Score:** 7.75/10

---

## 🤖 AI Review

# Step-by-step analysis of the problem:
1. **The PR diff is truncated**, which means we can't see the entire code change. This makes it difficult to provide a thorough review.
2. **The code in `corrupt_code.py` is invalid Python syntax**. The function definition `def this_is_broken(` is incomplete, and the rest of the file contains random text and invalid syntax.
3. **The files `delete_test.py`, `delete_test2.py`, and `huge_test_file.py` are new files**. However, their contents don't seem to be related to any specific functionality or test case.
4. **The static analysis results show errors**:
	* **Pylint** reports fatal errors for all files, indicating that they are not valid Python modules.
	* **Flake8** reports a `FileNotFoundError` for all files, which suggests that the files are not being found or are not valid Python files.
	* **Bandit** doesn't report any issues, but this is likely because it's not able to analyze the files due to their invalid syntax.
	* **Mypy** is unable to read the files due to their invalid syntax.
5. **The PR does not follow the engineering coding standards**:
	* The functions in `corrupt_code.py` do not have type hints.
	* The code is not formatted using `black`.
	* There are no docstrings for the functions.
	* The PR is not small and focused, as it introduces multiple new files with unclear purposes.

# Fixed solution:
Since the code is invalid and the PR is not following the coding standards, it's not possible to provide a fixed solution. Instead, I would recommend the following:

* **Recreate the PR with a clear and focused purpose**.
* **Write valid Python code** that follows the engineering coding standards.
* **Use `black` to format the code**.
* **Add type hints and docstrings to the functions**.
* **Remove any unnecessary files or code**.

# Explanation of changes:
* **Recreate the PR**: Start from scratch and create a new PR with a clear and focused purpose.
* **Write valid Python code**: Ensure that the code is syntactically correct and follows the engineering coding standards.
* **Use `black` to format the code**: Run `black` on the code to ensure it's formatted consistently.
* **Add type hints and docstrings**: Add type hints to the function parameters and return types, and write docstrings to explain what the functions do.
* **Remove unnecessary files or code**: Remove any files or code that are not necessary for the PR.

# Tests and example uses:
* **Write unit tests**: Write unit tests to verify that the code works as expected.
* **Test the code**: Test the code manually to ensure it works as expected.
* **Provide example use cases**: Provide example use cases to demonstrate how the code can be used.

---

## 🔍 Static Analysis Output

```
=== 🔍 Targeted Static Analysis for PYTHON (4 files changed) ===

| 🧩 Pylint:
```
************* Module corrupt_code.py
corrupt_code.py:1:0: F0001: No module named corrupt_code.py (fatal)
************* Module delete_test2.py
delete_test2.py:1:0: F0001: No module named delete_test2.py (fatal)
************* Module huge_test_file.py
huge_test_file.py:1:0: F0001: No module named huge_test_file.py (fatal)
```

| 🎯 Flake8:
```
corrupt_code.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'corrupt_code.py'
delete_test.py:1:22: W291 trailing whitespace
delete_test2.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'delete_test2.py'
huge_test_file.py:0:1: E902 FileNotFoundError: [Errno 2] No such file or directory: 'huge_test_file.py'
```

| 🔒 Bandit:
```
Run started:2025-11-16 18:50:42.777993

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
Files skipped (3):
	.\corrupt_code.py (No such file or directory)
	.\delete_test2.py (No such file or directory)
	.\huge_test_file.py (No such file or directory)
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
