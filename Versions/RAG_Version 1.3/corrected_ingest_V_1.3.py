import os
import shutil
import stat
import sys                      
from git import Repo
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, OWNER, REPO

GITHUB_REPO_URL = f"https://github.com/{OWNER}/{REPO}.git"

# Shared clone path (GitHub workflow passes this)
SHARED_REPO_PATH = None
if len(sys.argv) > 1:
    SHARED_REPO_PATH = sys.argv[1]
    print(f"🔄 Shared repo path argument detected: {SHARED_REPO_PATH}")

GLOB_PATTERN = "**/*"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


# HANDLE WINDOWS READ-ONLY FILES

def on_rm_error(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise


# MAIN INGEST LOGIC

    #  Decide repo path: shared OR clone new

    if SHARED_REPO_PATH and os.path.exists(SHARED_REPO_PATH):
        repo_path = SHARED_REPO_PATH
        print(f"♻ Using shared repo path (no clone): {repo_path}")
        remove_after = False
    else:
        repo_path = "temp_ingest_repo"
        remove_after = True

        if os.path.exists(repo_path):
            print("🧹 Cleaning old temp folder…")
            shutil.rmtree(repo_path, onerror=on_rm_error)

        print(f"📥 Cloning {GITHUB_REPO_URL} → {repo_path}")
        try:
            Repo.clone_from(GITHUB_REPO_URL, repo_path)
            print("✅ Repo cloned successfully.")
        except Exception as e:
            print(f"❌ Repo clone failed: {e}")
            return

    
    #  Load all repo files

    print(f"\n📄 Loading repo files from: {repo_path}")

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
        print(f"📄 Loaded {len(documents)} files.")
    except Exception as e:
        print(f"❌ Error while loading documents: {e}")
        return

    if not documents:
        print("⚠ No documents found, stopping.")
        return

    #  Split documents

    print("\n🔪 Splitting documents…")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(documents)

    print(f"📄 Total chunks created: {len(chunks)}")

    #  Embeddings

    print(f"\n🔢 Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Pinecone index check

    print("🌲 Initializing Pinecone client…")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing_idx = pc.list_indexes().names()

    if PINECONE_INDEX_NAME not in existing_idx:
        print(f"📌 Creating Pinecone index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    else:
        print(f"✔ Pinecone index '{PINECONE_INDEX_NAME}' already exists.")

    #  Upload to Pinecone
    
    print(f"\n📤 Uploading {len(chunks)} chunks to Pinecone…")

    PineconeVectorStore.from_documents(
        chunks,
        embeddings,
        index_name=PINECONE_INDEX_NAME,
    )

    print("\n✅ Ingestion completed successfully!")

    #  Cleanup

    if remove_after:
        print(f"🧹 Removing temp repo: {repo_path}")
        shutil.rmtree(repo_path, onerror=on_rm_error)
    else:
        print("♻ Shared repo mode, not deleting.")


# MAIN ENTRY
if __name__ == "__main__":
    if not all([OWNER, REPO, PINECONE_API_KEY, PINECONE_INDEX_NAME]):
        print("❌ Missing env vars in config.py (.env).")
    else:
        ingest_data()
