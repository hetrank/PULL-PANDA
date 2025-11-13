# rag_core.py

import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.retrievers import BaseRetriever
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME # Make sure to add these to config.py

# --- Configuration ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Cached Globals ---
_embeddings = None
_vector_store = None
_retriever = None

def _get_embeddings():
    """Loads and caches the embedding model."""
    global _embeddings
    if _embeddings is None:
        print("Loading embedding model...")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings

def _get_vector_store():
    """Loads and caches the Pinecone vector store."""
    global _vector_store
    if _vector_store is None:
        # This requires PINECONE_API_KEY to be set as an environment variable
        # or for the config to be imported correctly
        if not PINECONE_API_KEY:
             raise ValueError("PINECONE_API_KEY not found in config.py")
        print(f"Connecting to Pinecone index: '{PINECONE_INDEX_NAME}'...")
        
        # --- THIS IS THE FIX ---
        # We must load the embeddings *before* trying to use them
        embeddings = _get_embeddings()
        # ---------------------
        
        _vector_store = PineconeVectorStore.from_existing_index(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings # <--- Pass the loaded embeddings object
        )
    return _vector_store

def get_retriever(k_value: int = 4) -> BaseRetriever:
    """
    Initializes and returns a cached vector store retriever.
    """
    global _retriever
    if _retriever is None:
        vector_store = _get_vector_store()
        _retriever = vector_store.as_retriever(search_kwargs={"k": k_value})
        print("Retriever initialized from Pinecone.")
    return _retriever