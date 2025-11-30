"""Configuration module for the automated PR review system.

This module loads and validates all environment variables required for the
automated GitHub Pull Request review workflow, including API keys and repository
details. It ensures that all mandatory configuration values are available before
execution, and gracefully handles missing or invalid values.

Loaded values:
- OWNER, REPO: GitHub repository owner and name.
- PR_NUMBER: Pull request number (converted safely to int, defaults to 0 if invalid).
- GITHUB_TOKEN: GitHub Personal Access Token for API access.
- GROQ_API_KEY: API key for the Groq LLM integration.
- PINECONE_API_KEY, PINECONE_INDEX_NAME: Required for the RAG vector database.
"""

import os
from dotenv import load_dotenv

load_dotenv()

OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
# --- Convert PR_NUMBER to int here, default to 0 if not set or invalid ---
try:
    PR_NUMBER = int(os.getenv("PR_NUMBER"))
except (TypeError, ValueError):
    PR_NUMBER = 0
# ------------------------------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- NEW: Load Pinecone variables ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
# ------------------------------------

if not all([OWNER, REPO, GITHUB_TOKEN, GROQ_API_KEY]):
    raise SystemExit("❌ Missing required .env variables (excluding PR_NUMBER)")

# --- NEW: Check for Pinecone variables ---
if not all([PINECONE_API_KEY, PINECONE_INDEX_NAME]):
    raise SystemExit("❌ Missing PINECONE_API_KEY or PINECONE_INDEX_NAME in .env")
# -----------------------------------------

if PR_NUMBER <= 0:
    print("⚠️ WARNING: PR_NUMBER is missing or invalid in .env.")
