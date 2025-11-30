# V1.3 Black-Box Testing Report: RAG & Static Analysis

**Tester:** Yaksh Patel
**Date:** 2025-11-17
**Version:** 1.3 (RAG + Static Analysis Engine)\
**Test Repo Link:** [Link To Repo Made For Testing](https://github.com/Yaksh04/blackbox_test_v1.3_RAG)

## Summary of Findings

This report validates the successful integration and operation of the RAG (Retrieval-Augmented Generation) feature. The test also identified a consistent configuration flaw in the Static Analysis module. They main finding at the end of the test was that after running (`corrected_ingest`), it was evident that RAG used both the data from repo and from the knowlegde base, before only data from repo was used.

The test was conducted against a custom repository (`blackbox_test_v1.3_RAG`) with a batch of PRs. The AI agent's knowledge base was intentionally limited to the `coding_standards.md` file.

The **RAG system is FUNCTIONAL**. The AI successfully ingested `coding_standards.md` and `repo files` and correctly identified violations of those rules in the test PRs.

The **Static Analysis feature is NON-FUNCTIONAL** in its current configuration, consistently reporting "File Not Found" errors. After this test was conducted, the error was reported and fixed by correcting `static_analysis.py` and `iterative_prompt_selector.py`, no the static analysis works.

| Feature                             | Status   | Notes                                                                                                                                     |
| :---------------------------------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| **1. RAG: Knowledge Ingestion**     | **PASS** | `python ingest.py` and `corrected_ingest_V_1.3.py` successfully processed and uploaded `coding_standards.md` and subsequently repo files. |
| **2. RAG: Context Retrieval**       | **PASS** | AI reviews successfully cited rules from the knowledge base (see Finding #1).                                                             |
| **3. Static Analysis Integration**  | **FAIL** | The agent correctly reported that all static analysis tools failed with a "File Not Found" error on every PR.                             |
| **4. System Stability (Load Test)** | **PASS** | The system successfully processed all test PRs without crashing.                                                                          |
| **5. AI Learning (Persistence)**    | **PASS** | `selector_state.json` was successfully updated with new data from the test runs.                                                          |

## Key Findings & Analysis

### Finding #1: RAG is Fully Functional and Accurate

The test confirms the RAG pipeline (Ingest -> Retrieve -> Prompt) is working correctly. The AI agent successfully used the `coding_standards.md` file to find specific, valid bugs in the pull requests.

**Evidence from Test Reviews:**

- **Rule:** "All functions must have type hints."

  - **AI Finding:** `Critical Bugs: 2. Missing type hints: Multiple functions ('get_full_name', 'validate_email', 'format_user_for_display') are missing type hints...` (from `review_pr4_Meta.md`)

- **Rule:** "All public functions must have a docstring."

  - **AI Finding:** `Critical Bugs: 2. Incomplete function implementations: ... 'get_initials' lacks a docstring.` (from `review_pr5_Meta.md`)

- **Rule:** "Use `black` for formatting."

  - **AI Finding:** `Code Quality & Maintainability: 1. Run 'black' for formatting: The code does not conform to the specified formatting standards.` (from `review_pr1_Meta.md`)

- **Rule:** "Do not hardcode user roles."
  - **AI Finding:** `Code Quality & Maintainability: 2. Avoid hardcoded values: The 'is_admin' function hardcodes the 'admin' string.` (from `review_pr5_Meta.md`)

### Finding #2: RAG Context is Correctly Ingested

This test also confirmed that the AI's knowledge is properly limited to its ingested knowledge base and repo files.

- **Test Case:** The "Violates Timeout Rule" PRs (e.g., `review_pr3_Meta.md`).
- **Evidence:** The AI reviews for these PRs **did not** mention the missing timeout.
- **Diagnosis:** This is a **successful test** as no rule for API timeouts were included in the `knowledge_base` for this test. This proves the AI is not hallucinating rules and is correctly bound to the context it is fed.

### Finding #3: Static Analysis Module is Misconfigured

The test consistently demonstrates a flaw in the static analysis implementation.

- **Test Case:** All PRs in the test batch.
- **Evidence:** Every review file contains a "Critical Bug" related to static analysis.
  - (from `review_pr1_Meta.md`): `Static analysis errors: The PR causes fatal errors in Pylint, Flake8, Bandit, and Mypy due to a missing file.`
  - (from `review_pr4_Meta.md`): `File not found errors: The static analysis tools are reporting that user_utils.py cannot be found.`
- **Diagnosis:** The `static_analysis.py` script is attempting to run linters on file paths relative to its _own_ execution environment, not on the code within the context of the GitHub PR. This is a design flaw that prevents the feature from working. **Note:** This error was later fixed due to the findings of this test.
