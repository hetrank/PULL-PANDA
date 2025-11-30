"""Pytest tests for `rag_core.py`.

Ensures that embedding/vector store/retriever helpers cache results, call external APIs correctly,
and handle configuration issues gracefully. All external dependencies are mocked so no Pinecone or
HuggingFace calls occur.
"""

import os
import sys
import types
import importlib.util
import runpy
import pytest


def _import_rag_core_with_stubs():
    """Import `rag_core.py` from this directory with stubbed dependencies for tests."""
    originals = {}

    def _set_module(name, module_obj):
        originals[name] = sys.modules.get(name)
        sys.modules[name] = module_obj

    sys.modules.pop("rag_core", None)

    # Stub config to provide PINECONE_INDEX_NAME
    cfg = types.ModuleType("config")
    cfg.PINECONE_INDEX_NAME = "test-index"
    _set_module("config", cfg)

    # Stub HuggingFaceEmbeddings
    class DummyEmbeddings:
        def __init__(self, model_name):
            self.model_name = model_name

    hf = types.ModuleType("langchain_huggingface")
    hf.HuggingFaceEmbeddings = DummyEmbeddings
    _set_module("langchain_huggingface", hf)

    # Stub PineconeVectorStore
    class DummyRetriever:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def invoke(self, query):
            return []

    class DummyVectorStore:
        def __init__(self, name, embedding):
            self.name = name
            self.embedding = embedding
            self.as_retriever_called = []
        def as_retriever(self, search_kwargs):
            self.as_retriever_called.append(search_kwargs)
            return DummyRetriever(**search_kwargs)

    class DummyVectorStoreFactory:
        @staticmethod
        def from_existing_index(index_name, embedding):
            if not index_name:
                raise ValueError("index_name must be provided")
            return DummyVectorStore(index_name, embedding)

    pc = types.ModuleType("langchain_pinecone")
    pc.PineconeVectorStore = DummyVectorStoreFactory
    _set_module("langchain_pinecone", pc)

    lc_retrievers = types.ModuleType("langchain_core.retrievers")
    lc_retrievers.BaseRetriever = object
    _set_module("langchain_core.retrievers", lc_retrievers)

    here = os.path.dirname(__file__)
    path = os.path.join(here, "rag_core.py")
    spec = importlib.util.spec_from_file_location("rag_core", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Restore original modules to avoid leaking stubs to other tests
    for name, original in originals.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original

    return mod


def _run_rag_core_main_with_stubs(raise_error=False):
    """Execute rag_core.py as __main__ with stubbed dependencies for coverage."""
    originals = {}

    def _set_module(name, module_obj):
        originals[name] = sys.modules.get(name)
        sys.modules[name] = module_obj

    # Stub config
    cfg = types.ModuleType("config")
    cfg.PINECONE_INDEX_NAME = "main-test-index"
    _set_module("config", cfg)

    class DummyEmbeddings:
        def __init__(self, model_name):
            self.model_name = model_name

    hf = types.ModuleType("langchain_huggingface")
    hf.HuggingFaceEmbeddings = DummyEmbeddings
    _set_module("langchain_huggingface", hf)

    class DummyDoc:
        def __init__(self, idx):
            self.metadata = {"source": f"doc-{idx}"}
            self.page_content = f"content-{idx}" * 5

    class DummyRetriever:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail
            self.kwargs = {}

        def invoke(self, query):
            if self.should_fail:
                raise ConnectionError("retriever failure")
            return [DummyDoc(1), DummyDoc(2)]

    class DummyVectorStore:
        def __init__(self, index_name, embedding):
            self.index_name = index_name
            self.embedding = embedding

        def as_retriever(self, search_kwargs):
            retriever = DummyRetriever(should_fail=raise_error)
            retriever.kwargs = search_kwargs
            return retriever

    class DummyVectorStoreFactory:
        @staticmethod
        def from_existing_index(index_name, embedding):
            if not index_name:
                raise ValueError("index_name must be provided")
            return DummyVectorStore(index_name, embedding)

    pc = types.ModuleType("langchain_pinecone")
    pc.PineconeVectorStore = DummyVectorStoreFactory
    _set_module("langchain_pinecone", pc)

    lc_retrievers = types.ModuleType("langchain_core.retrievers")
    lc_retrievers.BaseRetriever = object
    _set_module("langchain_core.retrievers", lc_retrievers)

    try:
        here = os.path.dirname(__file__)
        path = os.path.join(here, "rag_core.py")
        runpy.run_path(path, run_name="__main__")
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


# ===== Tests for _get_embeddings() =====


def test_get_embeddings_initializes_once_and_caches(monkeypatch):
    """Arrange: import module; Act: call _get_embeddings twice; Assert: same instance and prints once."""
    mod = _import_rag_core_with_stubs()

    outputs = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: outputs.append(a[0] if a else ""))

    emb1 = mod._get_embeddings()
    emb2 = mod._get_embeddings()

    assert emb1 is emb2
    assert outputs.count("Loading embedding model...") == 1
    assert emb1.model_name == mod.EMBEDDING_MODEL


# ===== Tests for _get_vector_store() =====


def test_get_vector_store_initializes_with_embeddings_and_caches(monkeypatch):
    """Arrange: ensure vector store built using embeddings; Act: call twice; Assert: caching and print message."""
    mod = _import_rag_core_with_stubs()
    outputs = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: outputs.append(a[0] if a else ""))

    vs1 = mod._get_vector_store()
    vs2 = mod._get_vector_store()

    assert vs1 is vs2
    assert outputs.count(f"Connecting to Pinecone index: '{mod.PINECONE_INDEX_NAME}'...") == 1
    assert vs1.embedding.model_name == mod.EMBEDDING_MODEL


def test_get_vector_store_uses_existing_embeddings(monkeypatch):
    """Arrange: pre-populate embeddings; Act: call _get_vector_store; Assert: does not recreate embeddings."""
    mod = _import_rag_core_with_stubs()
    mod._embeddings = object()
    create_calls = []

    # Replace embeddings creator to track usage
    def fake_embeddings(model_name):
        create_calls.append(model_name)
        return object()

    monkeypatch.setattr(mod, "HuggingFaceEmbeddings", fake_embeddings)

    vs = mod._get_vector_store()
    assert create_calls == []
    assert vs.embedding is mod._embeddings


# ===== Tests for get_retriever() =====


def test_get_retriever_initializes_once_and_uses_vector_store(monkeypatch):
    """Arrange: import module; Act: call get_retriever twice; Assert: caching and search kwargs used."""
    mod = _import_rag_core_with_stubs()
    outputs = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: outputs.append(a[0] if a else ""))

    ret1 = mod.get_retriever(k_value=2)
    ret2 = mod.get_retriever(k_value=2)

    assert ret1 is ret2
    assert "Retriever initialized from Pinecone." in outputs
    assert ret1.kwargs.get("k") == 2


def test_get_retriever_respects_default_k_value():
    mod = _import_rag_core_with_stubs()
    retriever = mod.get_retriever()
    assert retriever.kwargs.get("k") == 4


# ===== Tests for configuration errors =====


def test_get_vector_store_raises_when_pinecone_index_missing(monkeypatch):
    mod = _import_rag_core_with_stubs()
    # Remove index name
    mod.PINECONE_INDEX_NAME = ""

    with pytest.raises(ValueError):
        mod._get_vector_store()


# ===== Tests for __main__ execution block =====


def test_rag_core_main_block_prints_results(capsys):
    _run_rag_core_main_with_stubs(raise_error=False)
    captured = capsys.readouterr().out
    assert "Retriever test:" in captured
    assert "Found 2 relevant chunks" in captured


def test_rag_core_main_block_handles_errors(capsys):
    _run_rag_core_main_with_stubs(raise_error=True)
    captured = capsys.readouterr().out
    assert "Test failed:" in captured
    assert "retriever failure" in captured
