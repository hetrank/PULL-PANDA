# config.py

import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- GitHub & Repo Config ---
OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# --- Convert PR_NUMBER to int safely ---
try:
    PR_NUMBER = int(os.getenv("PR_NUMBER", "0"))
except (TypeError, ValueError):
    PR_NUMBER = 0

# --- LLM Config ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- RAG (Pinecone) Config ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# --- Validation ---
# We check that all CRITICAL variables are present. 
# We exclude PR_NUMBER from this check because it might be passed via arguments in some scripts.
required_vars = [
    OWNER, 
    REPO, 
    GITHUB_TOKEN, 
    GROQ_API_KEY, 
    PINECONE_API_KEY, 
    PINECONE_INDEX_NAME
]

if not all(required_vars):
    # Helpful error message to identify exactly what is missing
    missing = []
    if not OWNER: missing.append("OWNER")
    if not REPO: missing.append("REPO")
    if not GITHUB_TOKEN: missing.append("GITHUB_TOKEN")
    if not GROQ_API_KEY: missing.append("GROQ_API_KEY")
    if not PINECONE_API_KEY: missing.append("PINECONE_API_KEY")
    if not PINECONE_INDEX_NAME: missing.append("PINECONE_INDEX_NAME")
    
    raise SystemExit(f" Missing required .env variables: {', '.join(missing)}")

if PR_NUMBER <= 0: 
    print(" WARNING: PR_NUMBER is missing or invalid in .env (defaulting to 0).")
