# prompts_v2.py
#
# Contains all prompt templates in a dictionary for easy access

from langchain_core.prompts import ChatPromptTemplate

def get_prompts():
    """Return all available prompts in a dictionary"""
    prompts = {}
    
    # Zero-shot (baseline)
    prompts["Zero-shot"] = ChatPromptTemplate.from_messages([
        ("system", "You are a software engineer."),
        ("human", "Review the following GitHub Pull Request diff. Point out bugs, mistakes, and give suggestions.\n\nDiff:\n{diff}")
    ])
    
    # Few-shot (examples)
    prompts["Few-shot"] = ChatPromptTemplate.from_messages([
        ("system", "You are a senior software engineer who writes concise, example-driven reviews."),
        ("human",
         "Here are examples of good short PR reviews (follow their style):\n\n"
         "Example 1:\n- Bug: `fetchData` may throw on null response.\n- Suggestion: Add null-check and early return, add unit test.\n\n"
         "Example 2:\n- Code style: inconsistent naming `myVar` vs `my_var`.\n- Suggestion: follow project lint rules and rename variables.\n\n"
         "Now review the following diff in the same style:\n\nDiff:\n{diff}")
    ])
    
    # Chain-of-Thought style (structured reasoning)
    prompts["Chain-of-Thought"] = ChatPromptTemplate.from_messages([
        ("system", "You are a senior software engineer. Use step-by-step analysis then produce a concise final review."),
        ("human",
         "Steps:\n"
         "1) Summarize what changed.\n"
         "2) Identify functional/logic bugs.\n"
         "3) Identify style/maintainability issues.\n"
         "4) Suggest prioritized fixes.\n\n"
         "Provide a short final review after the analysis.\n\nDiff:\n{diff}\n\n"
         "IMPORTANT: Provide only the final review in the 'Final Review' section at the end.")
    ])
    
    # Tree-of-Thought style (branch analysis)
    prompts["Tree-of-Thought"] = ChatPromptTemplate.from_messages([
        ("system", "You are an experienced reviewer. Explore the diff through multiple focused branches, then consolidate."),
        ("human",
         "Create 4 branches of analysis and then consolidate:\n"
         "- Branch A: Functional correctness (bugs, edge cases).\n"
         "- Branch B: Code quality (readability, naming, duplication).\n"
         "- Branch C: Performance & security concerns.\n"
         "- Branch D: Tests, docs, and CI considerations.\n\n"
         "For each branch, list findings (short bullets). Then produce a consolidated structured review.\n\nDiff:\n{diff}")
    ])
    
    # Self-Consistency (generate multiple candidates, pick best)
    prompts["Self-Consistency"] = ChatPromptTemplate.from_messages([
        ("system", "You are an expert reviewer. Generate multiple candidate reviews and select the best."),
        ("human",
         "Task:\n"
         "1) Generate 3 concise reviews (label them Review A, B, C).\n"
         "2) Compare them for clarity, correctness, and actionability.\n"
         "3) Return the best review and a 1-line reason why you picked it.\n\nDiff:\n{diff}")
    ])
    
    # Reflection (draft -> critique -> refine)
    prompts["Reflection"] = ChatPromptTemplate.from_messages([
        ("system", "You are a senior engineer. Produce a review, critique it, then refine it."),
        ("human",
         "Steps:\n"
         "1) Write an initial concise review.\n"
         "2) Critique that review for any missing issues or unclear suggestions.\n"
         "3) Produce a final refined review incorporating the critique.\n\nDiff:\n{diff}")
    ])
    
    # Meta (combined best practices)
    prompts["Meta"] = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert senior software engineer performing a professional GitHub Pull Request review."),
        ("human",
         "Analyze the PR diff across these dimensions:\n"
         "- Summary: short overview (1-2 lines).\n"
         "- Critical Bugs: list issues that must be fixed before merge.\n"
         "- Important Improvements: performance, security, correctness.\n"
         "- Code Quality & Maintainability: naming, complexity, duplication.\n"
         "- Tests & CI: missing tests or flakiness.\n"
         "- Positive notes: what was done well.\n\n"
         "Make all suggestions actionable (code snippets or exact lines when possible). Keep it concise and prioritize items by severity.\n\nDiff:\n{diff}")
    ])
    
    return prompts