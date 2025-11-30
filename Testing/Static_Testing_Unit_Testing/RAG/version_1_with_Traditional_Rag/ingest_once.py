"""
This script ingests a GitHub repository and builds a retrieval index using RAG.
Usage:
    python ingest_once.py <owner> <repo>
Requires GITHUB_TOKEN in the .env file.
"""

import os
import sys
from dotenv import load_dotenv
from rag_loader import build_index_for_repo  # <-- import from your file

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
build_index_for_repo(owner, repo, GITHUB_TOKEN, force_rebuild=True)
print("✅ Index built successfully for", f"{owner}/{repo}")
