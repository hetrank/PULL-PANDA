# Review for PR #999999 (Prompt: Zero-shot)
**Score:** 7.2/10

---

## 🤖 AI Review

### Review of GitHub PR Diff, Static Analysis, and Retrieved Context

#### Retrieved Context Review

The provided coding standards for Python are clear and concise. However, it would be beneficial to include more details on the following:

*   Specific version of Python to be used
*   Any specific libraries or frameworks that should be used or avoided
*   Guidelines for commit messages and branch naming conventions
*   Code review process and expectations

#### Static Analysis Results Review

The static analysis results indicate that no recognizable programming language files were found in the PR diff. This suggests that the PR diff may not contain any code changes, or the code changes are not in a recognizable format. To resolve this issue:

*   Ensure that the PR diff contains code changes in a recognizable format (e.g., Python files with a `.py` extension)
*   Verify that the static analysis tool is configured correctly to analyze the code changes in the PR diff

#### PR Diff Review

Since the PR diff is truncated, it's difficult to provide a thorough review. However, based on the provided context, here are some general suggestions:

*   Ensure that the PR is small and focused, as per the coding standards
*   Include unit tests for any new logic introduced in the PR
*   Verify that all functions have type hints and docstrings explaining args, returns, and raises
*   Check for any global variables and refactor the code to pass state explicitly
*   Use `black` for formatting to ensure consistency with the coding standards

To improve the review process, it would be helpful to have the complete PR diff and more context about the changes being made. Additionally, including a clear description of the changes and the purpose of the PR would facilitate a more effective review. 

Here is an example of how the PR description could be formatted:

```markdown
## PR Description

### Changes

*   Added new function `example_function` to perform example task
*   Updated `existing_function` to include new logic
*   Fixed bug in `buggy_function`

### Tests

*   Added unit tests for `example_function` and `existing_function`
*   Updated existing tests to cover new logic

### Notes

*   This PR is part of the larger effort to refactor the codebase and improve maintainability
*   Please review the changes carefully and provide feedback on any areas of concern
```

---

## 🔍 Static Analysis Output

```
⚠️ No recognizable programming language files found in PR diff to analyze.
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
