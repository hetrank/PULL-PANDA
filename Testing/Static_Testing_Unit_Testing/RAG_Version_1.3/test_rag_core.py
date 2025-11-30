import sys
import types
import pytest

# ============================================================
# Create fake modules to replace heavy libraries
# ============================================================

# --- Fake HuggingFaceEmbeddings ---
fake_hf = types.ModuleType("langchain_huggingface")

class FakeEmbeddings:
    def __init__(self, model_name):
        self.model_name = model_name

fake_hf.HuggingFaceEmbeddings = FakeEmbeddings
sys.modules["langchain_huggingface"] = fake_hf


# --- Fake PineconeVectorStore ---
fake_pinecone = types.ModuleType("langchain_pinecone")

class FakeVectorStore:
    def __init__(self):
        self.called = True

    @classmethod
    def from_existing_index(cls, index_name, embedding):
        inst = cls()
        inst.index_name = index_name
        inst.embedding = embedding
        return inst

    def as_retriever(self, search_kwargs):
        return {"retriever": True, "k": search_kwargs["k"]}

fake_pinecone.PineconeVectorStore = FakeVectorStore
sys.modules["langchain_pinecone"] = fake_pinecone


# --- Fake BaseRetriever (only to satisfy type) ---
fake_core = types.ModuleType("langchain_core.retrievers")

class FakeBaseRetriever:
    pass

fake_core.BaseRetriever = FakeBaseRetriever
sys.modules["langchain_core.retrievers"] = fake_core


# ============================================================
# Create a fake config module
# ============================================================
fake_config = types.ModuleType("config")
fake_config.PINECONE_API_KEY = "dummy_key"
fake_config.PINECONE_INDEX_NAME = "dummy_index"
sys.modules["config"] = fake_config


# ============================================================
# Now import rag_core after mocking everything
# ============================================================
import rag_core


# ============================================================
# TESTS
# ============================================================

def reset_cache():
    rag_core._cached_embeddings = None
    rag_core._cached_vector_store = None
    rag_core._cached_retriever = None


def test_get_embeddings_first_call():
    reset_cache()
    emb = rag_core._get_embeddings()

    assert isinstance(emb, FakeEmbeddings)
    assert emb.model_name == rag_core.EMBEDDING_MODEL
    assert rag_core._cached_embeddings is emb  # cached


def test_get_embeddings_cached():
    reset_cache()
    first = rag_core._get_embeddings()
    second = rag_core._get_embeddings()
    assert first is second  # same cached object


def test_get_vector_store_first_call():
    reset_cache()
    store = rag_core._get_vector_store()

    assert hasattr(store, "called")
    assert store.index_name == fake_config.PINECONE_INDEX_NAME
    assert rag_core._cached_vector_store is store  # cached


def test_get_vector_store_cached():
    reset_cache()
    first = rag_core._get_vector_store()
    second = rag_core._get_vector_store()
    assert first is second


def test_get_vector_store_missing_api_key(monkeypatch):
    reset_cache()

    # must patch rag_core.PINECONE_API_KEY directly
    monkeypatch.setattr(rag_core, "PINECONE_API_KEY", None)

    with pytest.raises(ValueError) as exc:
        rag_core._get_vector_store()

    assert "PINECONE_API_KEY" in str(exc.value)


def test_get_retriever_first_call():
    reset_cache()
    r = rag_core.get_retriever(k_value=10)

    assert isinstance(r, dict)
    assert r["retriever"]
    assert r["k"] == 10
    assert rag_core._cached_retriever is r


def test_get_retriever_cached():
    reset_cache()
    r1 = rag_core.get_retriever()
    r2 = rag_core.get_retriever()
    assert r1 is r2
