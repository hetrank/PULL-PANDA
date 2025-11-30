"""
ingest_once_agentic.py

This script loads a GitHub repository and builds an Agentic RAG index.
Usage:
    python ingest_once_agentic.py <owner> <repo>

Requires:
    - .env containing GITHUB_TOKEN
"""

import os
import sys
from dotenv import load_dotenv
from rag_loader_agentic import build_index_for_repo  # <-- import from your file

# Load environment variables for GitHub token
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in .env file")

# Expect: python ingest_once.py <owner> <repo>
if len(sys.argv) < 3:
    script_name = os.path.basename(sys.argv[0])
    print(f"Usage: python {script_name} <owner> <repo>")
    sys.exit(1)

owner = sys.argv[1]
repo = sys.argv[2]

print(f"🚀 Starting ingestion for repo: {owner}/{repo}")
# Set force_rebuild=True to ensure the index is built from scratch and files are downloaded
build_index_for_repo(owner, repo, GITHUB_TOKEN, force_rebuild=True)
print("✅ Index built successfully and files downloaded for", f"{owner}/{repo}")
