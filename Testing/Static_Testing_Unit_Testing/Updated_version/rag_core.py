"""
RAG (Retrieval-Augmented Generation) core module.

This module provides functionality to initialize and cache embedding models,
vector stores, and retrievers for document retrieval from Pinecone.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.retrievers import BaseRetriever
from config import PINECONE_INDEX_NAME

# --- Configuration ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Module-level cache variables (not constants, hence lowercase) ---
# These are intentionally lowercase as they are mutable cache variables
_embeddings = None  # pylint: disable=invalid-name
_vector_store = None  # pylint: disable=invalid-name
_retriever = None  # pylint: disable=invalid-name


def _get_embeddings():
    """Load and cache the embedding model."""
    global _embeddings  # pylint: disable=global-statement
    if _embeddings is None:
        print("Loading embedding model...")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def _get_vector_store():
    """Load and cache the Pinecone vector store."""
    global _vector_store  # pylint: disable=global-statement
    if _vector_store is None:
        print(f"Connecting to Pinecone index: '{PINECONE_INDEX_NAME}'...")
        embeddings = _get_embeddings()
        _vector_store = PineconeVectorStore.from_existing_index(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings
        )
    return _vector_store


def get_retriever(k_value: int = 4) -> BaseRetriever:
    """
    Initialize and return a cached vector store retriever.

    Args:
        k_value: Number of documents to retrieve (default: 4)

    Returns:
        BaseRetriever: Cached retriever instance
    """
    global _retriever  # pylint: disable=global-statement
    if _retriever is None:
        vector_store = _get_vector_store()
        _retriever = vector_store.as_retriever(search_kwargs={"k": k_value})
        print("Retriever initialized from Pinecone.")
    return _retriever


if __name__ == "__main__":
    # A simple test to check if the retriever works
    try:
        retriever = get_retriever()
        print("\nRetriever test:")
        TEST_QUERY = "python type hints"
        docs = retriever.invoke(TEST_QUERY)
        print(f"Query: '{TEST_QUERY}'")
        print(f"Found {len(docs)} relevant chunks:")
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'N/A')
            print(f"--- Doc {i+1} (Source: {source}) ---")
            print(doc.page_content[:200] + "...")
    except (ConnectionError, ValueError, RuntimeError) as error:
        print(f"\nTest failed: {error}")
