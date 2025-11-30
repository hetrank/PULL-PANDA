# V1.3 Black-Box Testing Report

**Tester:** Ritul Patel  
**Date:** 17 Nov 2025  
**Version Tested:** 1.3 (RAG-Automated PR Reviewer)  
**Test Repository:** blackbox_test_v1.3_RAG  
**Test Repo Link:** [Link To Repo Made For Testing](https://github.com/ritul-patel/RAG_Version-1.3-Black-box-testing/pulls)


## Summary

This report covers the Black-Box testing of the RAG-based pull-request review system (v1.3).  
The goal was to check how well it handles different types of PRs, including small edits, big diffs, missing files, corrupted code, Unicode input, binary files, and mixed-language projects.

Overall, the system performed well. It consistently pulled the right rules from the knowledge base and applied them correctly.  
The only major issue found is that the PR-404 case doesn’t stop the workflow and the system continues running unnecessary steps.

Static Analysis wasn’t part of this test cycle, but a few minor path-related issues were visible. They’re mentioned briefly at the end.



## Feature Status

| Feature | Status | Notes |
|--------|--------|-------|
| Knowledge Ingestion | PASS | Ingestion worked smoothly through the updated pipeline |
| Context Retrieval | PASS | Pulled accurate rules without adding anything extra |
| System Stability | PASS | No crashes, even under load |
| Learning (selector updates) | PASS | `selector_state.json` updated correctly |
| Security Checks | PASS | All injected secrets were flagged |
| Performance | PASS | Large PRs handled without slowdown |
| PR-404 Handling | **FAIL** | System continues processing instead of stopping |
| Static Analysis (observation) | Not tested | A few small path issues seen during runs |



## Key Observations

### 1. RAG Accuracy  
The full workflow ran correctly for every PR tested.  
It caught issues like missing type hints, missing docstrings, hardcoded values, formatting problems, missing validation, and missing test coverage.  
Importantly, it did not invent any rules. Everything came from the KB.

### 2. Context Was Applied Properly  
If a rule didn’t exist in the KB, the reviewer didn’t mention it.  
This confirms that retrieval is controlled and the system isn’t guessing or filling in blanks on its own.

### 3. Security Tests Passed  
Fake API keys, passwords, and token-like strings were all caught.  
The reviewer explained the risk clearly and flagged them with the right severity.

### 4. Performance Was Strong  
Large PRs over 5,000 lines were processed without any slowdown or instability.  
The system stayed responsive and completed all steps cleanly.

### 5. Stability Across All Tests  
Across more than 20 PRs, including intentionally broken ones, the system stayed stable.  
No crashes, no corrupted state, and the learning file updated properly every time.

### 6. PR-404 Handling Failed  
Expected: stop processing when the PR isn’t found.  
Actual: the system continues with ingestion, retrieval, review generation, selector learning, and external calls.  
This wastes compute and should be fixed with a simple early exit.

### 7. Static Analysis (Small Note)  
Not part of this test, but a few messages appeared during runs related to missing files and path lookups.  
These don’t affect RAG behavior but should be shared with the teammate working on that module.



## Test Coverage

### General Tests  
- Tiny, small, medium, and large PRs  
- Empty PR  
- Multi-file and multi-language PRs  
- Unicode and binary files  
- Cross-file logic

### Edge Cases  
- Missing files  
- Corrupted code  
- Missing imports  
- Large single files  
- Merge conflicts

### Special Tests  
- Security checks  
- Performance tests 

### Failure  
- PR-404 Handling — FAILED

### Not in Scope  
- Static Analysis (only minor observations)



## Final Verdict

**RAG Engine:** Passed  
**Security:** Passed  
**Performance:** Passed  
**Learning System:** Passed  
**Core Logic:** Passed  
**PR-404 Handling:** Failed (needs a fix before production)

Static Analysis wasn’t evaluated, but minor path issues were noticed.



## Recommendations

1. Add an early exit for missing PRs.  
2. Add a quick regression check for PR existence before running the full workflow.
3. Share the small static-analysis path notes with the teammate handling that module.
