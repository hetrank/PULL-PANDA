"""
Prompt templates for PR review testing.

This module provides various prompt engineering strategies for code review,
including zero-shot, few-shot, chain-of-thought, and advanced techniques.
"""

from collections import OrderedDict
from langchain_core.prompts import ChatPromptTemplate


def get_prompts():
    """
    Get collection of different prompt strategies for PR reviews.

    Returns:
        OrderedDict: Mapping of prompt names to ChatPromptTemplate objects
    """
    prompts = OrderedDict()

    # 1) Zero-shot (intentionally basic)
    prompts["zero_shot"] = ChatPromptTemplate.from_messages([
        ("system", "You are a software engineer."),
        (
            "human",
            "Look at this code change and tell me what you think.\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 2) Few-shot (structured with examples)
    prompts["few_shot"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a senior engineer who follows examples closely to "
            "provide structured reviews."
        ),
        (
            "human",
            "Here are example reviews showing the format and depth "
            "expected:\n\n"
            "Example 1 - Authentication Bug:\n"
            "```\n"
            "🐛 CRITICAL: Line 23 - Missing authentication check in "
            "`/api/users` endpoint\n"
            "💡 FIX: Add `@require_auth` decorator before function "
            "definition\n"
            "🧪 TEST: Verify unauthorized access returns 401\n"
            "```\n\n"
            "Example 2 - Performance Issue:\n"
            "```\n"
            "⚡ PERFORMANCE: Line 45 - N+1 query in user loop "
            "(database call per iteration)\n"
            "💡 FIX: Use `select_related()` or batch the queries\n"
            "📊 IMPACT: Could slow down with >100 users\n"
            "```\n\n"
            "Now review this diff using the same structured format with "
            "emojis, specific line references, and actionable fixes:\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 3) Chain-of-Thought (systematic analysis)
    prompts["chain_of_thought"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a principal engineer who thinks systematically "
            "through code reviews step by step."
        ),
        (
            "human",
            "Analyze this PR systematically following these steps:\n\n"
            "**STEP 1: UNDERSTANDING**\n"
            "- What is the main purpose of this change?\n"
            "- Which components/modules are affected?\n\n"
            "**STEP 2: SECURITY & CORRECTNESS**\n"
            "- Are there any security vulnerabilities?\n"
            "- Logic errors or edge cases not handled?\n"
            "- Input validation issues?\n\n"
            "**STEP 3: PERFORMANCE & SCALABILITY**\n"
            "- Database queries, algorithms, memory usage\n"
            "- Potential bottlenecks at scale\n\n"
            "**STEP 4: CODE QUALITY**\n"
            "- Readability, maintainability, documentation\n"
            "- Adherence to patterns and conventions\n\n"
            "**FINAL RECOMMENDATION**\n"
            "- Priority ranking of issues (P0=blocker, P1=important, "
            "P2=nice-to-have)\n"
            "- Overall assessment: APPROVE/REQUEST_CHANGES/"
            "NEEDS_DISCUSSION\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 4) Tree-of-Thought (multi-perspective analysis)
    prompts["tree_of_thought"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a tech lead conducting a comprehensive review from "
            "multiple expert perspectives."
        ),
        (
            "human",
            "Analyze this PR from 4 different expert perspectives, then "
            "synthesize:\n\n"
            "**🔒 SECURITY EXPERT PERSPECTIVE:**\n"
            "- Authentication, authorization, input sanitization\n"
            "- Data exposure, injection vulnerabilities\n"
            "- Secrets management, encryption\n\n"
            "**⚡ PERFORMANCE EXPERT PERSPECTIVE:**\n"
            "- Database efficiency, caching strategies\n"
            "- Algorithm complexity, memory usage\n"
            "- Network calls, async patterns\n\n"
            "**🏗️ ARCHITECTURE EXPERT PERSPECTIVE:**\n"
            "- Design patterns, separation of concerns\n"
            "- Coupling, cohesion, scalability\n"
            "- API design, backward compatibility\n\n"
            "**🧪 QA EXPERT PERSPECTIVE:**\n"
            "- Test coverage, edge cases\n"
            "- Error handling, logging\n"
            "- Integration points, rollback scenarios\n\n"
            "**📋 SYNTHESIZED REVIEW:**\n"
            "Consolidate findings into prioritized action items with "
            "owner assignments.\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 5) Self-consistency (multiple approaches, best selection)
    prompts["self_consistency"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert reviewer who generates multiple review "
            "approaches and selects the most comprehensive."
        ),
        (
            "human",
            "Generate 3 different review approaches, then select and "
            "enhance the best:\n\n"
            "**APPROACH A - RAPID SECURITY SCAN:**\n"
            "Focus on security vulnerabilities, auth issues, data "
            "validation\n\n"
            "**APPROACH B - MAINTAINABILITY DEEP-DIVE:**\n"
            "Focus on code structure, readability, technical debt, "
            "future extensibility\n\n"
            "**APPROACH C - PRODUCTION READINESS:**\n"
            "Focus on performance, monitoring, error handling, "
            "deployment risks\n\n"
            "**SELECTION & ENHANCEMENT:**\n"
            "- Which approach found the most critical issues?\n"
            "- Combine insights from all three approaches\n"
            "- Provide final comprehensive review with confidence "
            "scores\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 6) Reflection (draft -> self-critique -> refinement)
    prompts["reflection"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a staff engineer who iteratively improves your "
            "reviews through self-reflection."
        ),
        (
            "human",
            "**INITIAL DRAFT REVIEW:**\n"
            "Write your first-pass review of this diff.\n\n"
            "**SELF-CRITIQUE:**\n"
            "Now critically evaluate your draft:\n"
            "- What important aspects did I miss?\n"
            "- Are my suggestions specific and actionable enough?\n"
            "- Did I consider the business context and user impact?\n"
            "- Are there any false positives in my findings?\n\n"
            "**REFINED REVIEW:**\n"
            "Based on the self-critique, provide an improved review "
            "that:\n"
            "- Addresses the gaps identified\n"
            "- Balances thoroughness with practicality\n"
            "- Includes confidence levels for each finding\n"
            "- Suggests implementation timeline and effort "
            "estimates\n\n"
            "Diff:\n{diff}"
        )
    ])

    # 7) Meta (production-grade comprehensive review)
    prompts["meta"] = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a distinguished engineer conducting a "
            "production-grade PR review with enterprise standards."
        ),
        (
            "human",
            "Conduct a comprehensive PR review following enterprise "
            "standards:\n\n"
            "**📋 EXECUTIVE SUMMARY**\n"
            "- Change description and business impact\n"
            "- Overall risk assessment (LOW/MEDIUM/HIGH)\n"
            "- Recommendation with confidence level\n\n"
            "**🚨 CRITICAL ISSUES (Merge Blockers)**\n"
            "- Security vulnerabilities with CVSS scores\n"
            "- Data corruption or loss risks\n"
            "- Breaking changes without migration path\n\n"
            "**⚠️ IMPORTANT ISSUES (Address Before Next Release)**\n"
            "- Performance regressions with benchmarks\n"
            "- Scalability concerns with user load estimates\n"
            "- Integration failures with dependent services\n\n"
            "**🔧 CODE QUALITY IMPROVEMENTS**\n"
            "- Maintainability metrics and technical debt\n"
            "- Documentation gaps and knowledge transfer\n"
            "- Testing coverage with gap analysis\n\n"
            "**📊 METRICS & MONITORING**\n"
            "- Suggested telemetry and alerting\n"
            "- Performance benchmarks to track\n"
            "- A/B testing recommendations\n\n"
            "**✅ POSITIVE HIGHLIGHTS**\n"
            "- Well-implemented patterns and practices\n"
            "- Performance improvements and optimizations\n\n"
            "**🎯 ACTION ITEMS**\n"
            "- Prioritized checklist with owners and deadlines\n"
            "- Follow-up tasks and future improvements\n\n"
            "Provide specific line numbers, code snippets, and "
            "measurable impact estimates where possible.\n\n"
            "Diff:\n{diff}"
        )
    ])

    return prompts
