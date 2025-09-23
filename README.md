# 🤖 GitHub PR Review Agent

An AI-powered agent that reviews GitHub Pull Requests (PRs) and provides meaningful feedback on code changes, descriptions, and best practices.

This project explores **three approaches** to AI-assisted PR review:
1. **Cloud LLMs** – Prompting hosted models (e.g., Groq, OpenAI) for fast results.
2. **Local LLMs** – Using models via Ollama for privacy & offline usage.
3. **Custom Training** – Fine-tuning a lightweight model on synthetic + real PR data for tailored reviews.

---

## 🚀 Features

- 📋 Generate synthetic PRs (title, description, code diff, review) for training datasets.
- 🧠 Train a custom model (LoRA fine-tuning on GPT-2 or similar).
- 🔍 Run inference on new PRs and get AI-generated reviews.
- 🔒 Privacy toggle: choose between **cloud** (more powerful) and **local** (private) review.
- 🛠️ Extensible to integrate static analyzers, linters, and RAG with repo context.

---

## 🧩 Future Roadmap

- ✅ **Sprint 1:** Cloud LLM MVP – PR fetch → LLM → Review comment
- ✅ **Sprint 2:** Add static analyzers & linter outputs in prompts
- ✅ **Sprint 3:** Repo indexing with RAG for context-aware reviews
- ✅ **Sprint 4:** Local LoRA fine-tuned model with Ollama integration
- ✅ **Final:** Dashboard, evaluation, and report

