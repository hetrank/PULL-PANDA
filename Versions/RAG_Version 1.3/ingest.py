import os
import shutil
import stat
import sys   # add for get context using github action
from git import Repo
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, OWNER, REPO

GITHUB_REPO_URL = f"https://github.com/{OWNER}/{REPO}.git"

SHARED_REPO_PATH = None
if len(sys.argv) > 1:
    SHARED_REPO_PATH = sys.argv[1]
    print(f"🔄 Shared repo path detected: {SHARED_REPO_PATH}")

GLOB_PATTERN = "**/*"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

#  Helper: Handle Read-only Files
def on_rm_error(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise


#  Main Ingestion Logic
def ingest_data():
    """
    UPDATED:
    - If shared repo path is provided → reuse it
    - Otherwise clone repo
    - No temp delete when reusing shared clone
    """

  # 1) Decide Repo Path (shared or clone)
    if SHARED_REPO_PATH and os.path.exists(SHARED_REPO_PATH):
        repo_path = SHARED_REPO_PATH
        print(f"🔄 Reusing provided repo path: {repo_path}")
        remove_after = False
    else:
        repo_path = "temp_client_repo_ingest"
        remove_after = True

        if os.path.exists(repo_path):
            print("Deleting old temp repo...")
            shutil.rmtree(repo_path, onerror=on_rm_error)

        print(f"📥 Cloning repository {GITHUB_REPO_URL} into {repo_path}...")
        try:
            Repo.clone_from(GITHUB_REPO_URL, repo_path)
            print("Repo cloned successfully.")
        except Exception as e:
            print(f"❌ FAILED to clone repo: {e}")
            return

    # 2) Load Files
    print(f"\n--- Loading Repo Files ({GLOB_PATTERN}) ---")

    try:
        loader = DirectoryLoader(
            repo_path,
            glob=GLOB_PATTERN,
            loader_cls=TextLoader,
            loader_kwargs={"autodetect_encoding": True},
            show_progress=True,
            use_multithreading=True,
            silent_errors=True,
        )

        documents = loader.load()
        print(f"Loaded {len(documents)} files.")

    except Exception as e:
        print(f"❌ Error during document loading: {e}")
        return

    if not documents:
        print("⚠ No documents found. Exiting.")
        return

    # 3) Split into Chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    texts = splitter.split_documents(documents)

    print(f"Split into {len(texts)} chunks.")

    # 4) Embedding Model
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 5) Pinecone Index Check
    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = pc.list_indexes().names()

    if PINECONE_INDEX_NAME not in existing:
        print(f"Index '{PINECONE_INDEX_NAME}' not found → Creating new index.")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' exists.")

    # 6) Upload to Pinecone
    print(f"📤 Uploading {len(texts)} chunks → Pinecone…")

    PineconeVectorStore.from_documents(
        texts,
        embeddings,
        index_name=PINECONE_INDEX_NAME,
    )

    print("\n✅ Ingestion complete!")

    # 7) Cleanup
    if remove_after:
        print(f"🧹 Removing temp repo folder: {repo_path}")
        shutil.rmtree(repo_path, onerror=on_rm_error)
    else:
        print("♻ Reuse mode active → Repo NOT deleted.")


#  Main Entry

if __name__ == "__main__":
    if not all([OWNER, REPO, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
        print("❌ Missing required env vars in .env file.")
        print("Please set OWNER, REPO, PINECONE_API_KEY, PINECONE_INDEX_NAME.")
    else:
        ingest_data()
