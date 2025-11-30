"""
RAG core utilities for loading embeddings, connecting to Pinecone,
and creating a cached retriever. No logic has been changed; only
Pylint warnings resolved.
"""
# pylint: disable=import-error
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.retrievers import BaseRetriever
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME
# pylint: enable=import-error

# --- Configuration ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Private cached globals (intentionally not constants) ---
# pylint: disable=C0103
_cached_embeddings = None
_cached_vector_store = None
_cached_retriever = None


def _get_embeddings():
    """Load and cache the embedding model."""
    # pylint: disable=global-statement
    global _cached_embeddings

    if _cached_embeddings is None:
        print("Loading embedding model...")
        _cached_embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )
    return _cached_embeddings


def _get_vector_store():
    """Load and cache the Pinecone vector store."""
    # pylint: disable=global-statement
    global _cached_vector_store

    if _cached_vector_store is None:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not found in config.py")

        print(f"Connecting to Pinecone index: '{PINECONE_INDEX_NAME}'...")

        # Load embeddings before using them
        embeddings = _get_embeddings()

        _cached_vector_store = PineconeVectorStore.from_existing_index(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
        )
    return _cached_vector_store


def get_retriever(k_value: int = 4) -> BaseRetriever:
    """
    Initialize and return a cached Pinecone retriever.
    """
    # pylint: disable=global-statement
    global _cached_retriever

    if _cached_retriever is None:
        vector_store = _get_vector_store()
        _cached_retriever = vector_store.as_retriever(
            search_kwargs={"k": k_value}
        )
        print("Retriever initialized from Pinecone.")

    return _cached_retriever
