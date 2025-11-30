"""
RAG loader module for agentic pull request reviews.

This module handles downloading GitHub repositories, building FAISS indexes
for vector search, and assembling context for LLM-based code reviews.
"""

import io
import os
import shutil
import zipfile
from pathlib import Path

import requests
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

# Shared directory path. MUST be consistent with version_1_Yash.py
REPO_DOWNLOAD_DIR = Path("repo_download")


# -------------------------------
# Helper: Download and Extract Repo
# -------------------------------
def download_and_extract_repo(owner, repo, token, dest_dir=REPO_DOWNLOAD_DIR):
    """Download and extract the repository zip for HEAD."""
    print("⬇️ Downloading repository snapshot...")

    # 1. Clear destination
    # We remove the directory tree to clear stale or old repo contents
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 2. Download zip
    url = f"https://api.github.com/repos/{owner}/{repo}/zipball/HEAD"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    # 3. Extract contents
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    zip_file.extractall(dest_dir)

    # The zip extracts into a single top-level folder (e.g., owner-repo-sha)
    # We return the path to this top-level folder for traversal and
    # the Agent's file reader tool
    repo_root = next((p for p in dest_dir.iterdir() if p.is_dir()), dest_dir)
    print(f"Repository extracted to: {repo_root}")
    return repo_root


# -------------------------------
# Helper: Traverse and Load Files for Indexing
# -------------------------------
def load_text_files(repo_root: Path):
    """
    Traverse the extracted repository and load content for indexing.
    Returns a list of strings (file contents).
    """
    file_texts = []

    # --- FINAL COMPREHENSIVE LIST OF SUPPORTED EXTENSIONS ---
    supported_extensions = (
        ".c", ".cpp", ".h",
        ".java",
        ".py",
        ".html",
        ".css",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".txt",
        ".md"
    )

    skip_dirs = {
        ".git", "node_modules", "__pycache__",
        ".venv", "venv", "env", "dist", "build"
    }

    for root, dirs, files in os.walk(repo_root):
        # Prune skip directories for faster traversal
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for fname in files:
            # Skip dot files and files without supported extensions
            if (fname.startswith(".") or
                    not any(fname.endswith(ext) for ext in supported_extensions)):
                continue

            path = Path(root) / fname
            try:
                # Store full content for the RAG index
                text = path.read_text(encoding="utf-8", errors="ignore")
                file_texts.append(text)
            except (IOError, OSError) as e:
                print(f"Failed to read {path}: {e}")

    return file_texts


# -------------------------------
# Build or load FAISS index
# -------------------------------
def build_index_for_repo(owner, repo, token, force_rebuild=False,
                         download_if_missing=False):
    """
    Build a FAISS index or load an existing one.
    Ensures local files are present if needed.
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    index_path = Path(f"rag_indexes/{owner}_{repo}")
    os.makedirs(index_path, exist_ok=True)

    index_file = index_path / "index.faiss"

    # Check if a download is required (either for a rebuild OR if files are
    # missing for the Agent tool). We check if the main repo_download
    # directory exists AND contains content
    repo_files_missing = (not REPO_DOWNLOAD_DIR.exists() or
                          not any(REPO_DOWNLOAD_DIR.iterdir()))

    if not index_file.exists() or force_rebuild:
        print("Index does not exist or force rebuild, "
              "creating new FAISS index...")

        # Download and extract the repository contents
        repo_root = download_and_extract_repo(owner, repo, token)

        # Load file contents for indexing
        texts = load_text_files(repo_root)
        if not texts:
            texts = ["Initial dummy text"]  # fallback so index creation works

        # Create FAISS vectorstore
        vectorstore = FAISS.from_texts(texts, embeddings)
        vectorstore.save_local(index_path)
        print(f"✅ Index created at {index_path}")

    else:
        print(f"Loading existing index from {index_path}")
        # Load the existing index
        vectorstore = FAISS.load_local(
            index_path, embeddings, allow_dangerous_deserialization=True
        )

        # If we didn't rebuild, but the Agent needs the files, download them.
        if download_if_missing and repo_files_missing:
            download_and_extract_repo(owner, repo, token)

    return vectorstore


# -------------------------------
# Assemble context
# -------------------------------
def assemble_context(retrieved_docs: list[Document], char_limit=3000):
    """
    Combine retrieved doc chunks (LangChain Document objects) into a single
    string within char_limit.
    """
    context_text = ""
    for doc in retrieved_docs:
        # doc is a LangChain Document, access content via .page_content
        new_text = (doc.page_content if hasattr(doc, "page_content")
                    else str(doc))
        if len(context_text) + len(new_text) > char_limit:
            break
        context_text += new_text + "\n\n"
    return context_text
