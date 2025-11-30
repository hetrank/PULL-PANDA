"""
RAG loader module for traditional pull request reviews.

This module handles downloading GitHub repository files via the GitHub API,
building FAISS indexes for vector search, and assembling context for
LLM-based code reviews.
"""

import os
from pathlib import Path

import requests
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


# -------------------------------
# Helper: download repo files
# -------------------------------
def download_repo_files(owner, repo, token):
    """
    Download text files from GitHub repo (only .py, .txt, .md etc.).

    Args:
        owner: Repository owner username
        repo: Repository name
        token: GitHub authentication token

    Returns:
        List of strings containing file contents
    """
    base_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    headers = {"Authorization": f"token {token}"}
    file_texts = []

    def traverse(path=""):
        """Recursively traverse repository directories."""
        url = base_url + path
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Error fetching {path}: {resp.status_code}")
            return
        items = resp.json()
        for item in items:
            if (item["type"] == "file" and
                    item["name"].endswith((".py", ".txt", ".md"))):
                file_resp = requests.get(item["download_url"], timeout=30)
                if file_resp.status_code == 200:
                    file_texts.append(file_resp.text)
            elif item["type"] == "dir":
                traverse(item["path"])

    traverse()
    return file_texts


# -------------------------------
# Build or load FAISS index
# -------------------------------
def build_index_for_repo(owner, repo, token, force_rebuild=False):
    """
    Build a FAISS index for a GitHub repo if it doesn't exist.

    Loads existing index if available and force_rebuild=False.

    Args:
        owner: Repository owner username
        repo: Repository name
        token: GitHub authentication token
        force_rebuild: If True, rebuild index even if it exists

    Returns:
        FAISS vectorstore object
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    index_path = Path(f"rag_indexes/{owner}_{repo}")
    os.makedirs(index_path, exist_ok=True)

    # check if index exists
    index_file = index_path / "index.faiss"
    if not index_file.exists() or force_rebuild:
        print("Index does not exist or force rebuild, "
              "creating new FAISS index...")
        texts = download_repo_files(owner, repo, token)
        if not texts:
            texts = ["Initial dummy text"]  # fallback so index creation works

        # create FAISS vectorstore
        vectorstore = FAISS.from_texts(texts, embeddings)
        vectorstore.save_local(index_path)
        print(f"✅ Index created at {index_path}")
    else:
        print(f"Loading existing index from {index_path}")
        vectorstore = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )

    return vectorstore


# -------------------------------
# Assemble context
# -------------------------------
def assemble_context(retrieved_docs, char_limit=3000):
    """
    Combine retrieved doc chunks into a single string within char_limit.

    Args:
        retrieved_docs: List of retrieved document objects
        char_limit: Maximum character limit for combined context

    Returns:
        String containing assembled context
    """
    context_text = ""
    for doc in retrieved_docs:
        new_text = (doc.page_content if hasattr(doc, "page_content")
                    else str(doc))
        if len(context_text) + len(new_text) > char_limit:
            break
        context_text += new_text + "\n\n"
    return context_text
