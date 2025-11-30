"""
Document ingestion module for vector store.

This module loads documents from a knowledge base directory, splits them into
chunks, embeds them, and uploads them to a Pinecone vector store index.
"""

import os

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from config import PINECONE_API_KEY, PINECONE_INDEX_NAME

# --- Configuration ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# The dimension of the 'all-MiniLM-L6-v2' model. This is critical.
EMBEDDING_DIMENSION = 384


def ingest_data():
    """
    Load data, split, embed, and upload to a Pinecone index.
    """
    print(f"Loading documents from {KNOWLEDGE_BASE_DIR}...")
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*",
        loader_cls=TextLoader,
        show_progress=True,
        use_multithreading=True
    )
    documents = loader.load()

    if not documents:
        print("No documents found to ingest. Exiting.")
        return

    print(f"Loaded {len(documents)} documents.")

    # Split documents into chunks
    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    texts = text_splitter.split_documents(documents)
    print(f"Split into {len(texts)} chunks.")

    # Load embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # --- Pinecone Initialization ---
    print("Initializing Pinecone client...")
    pinecone_client = Pinecone(api_key=PINECONE_API_KEY)

    if PINECONE_INDEX_NAME not in pinecone_client.list_indexes().names():
        print(f"Index '{PINECONE_INDEX_NAME}' not found. Creating new index...")
        pinecone_client.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",  # Cosine similarity is standard for text embeddings
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'  # Use a free-tier compatible region
            )
        )
        print("Index created. Waiting for it to be ready...")
        # Note: In a real app, you might wait in a loop, but adding docs
        # will wait.
    else:
        print(f"Found existing index '{PINECONE_INDEX_NAME}'.")

    # Upload documents to Pinecone
    print(f"Uploading {len(texts)} chunks to Pinecone index...")
    PineconeVectorStore.from_documents(
        texts,
        embeddings,
        index_name=PINECONE_INDEX_NAME
    )

    print("\nIngestion complete!")
    print(f"Vector store is ready in Pinecone index '{PINECONE_INDEX_NAME}'.")


if __name__ == "__main__":
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"Error: Knowledge base directory not found at "
              f"'{KNOWLEDGE_BASE_DIR}'")
        print("Please create it and add your documents (e.g., .md, .txt "
              "files).")
    else:
        ingest_data()
