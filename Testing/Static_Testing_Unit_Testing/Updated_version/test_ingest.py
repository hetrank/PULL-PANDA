import os
import sys
import runpy
import types
import pytest


# ============================================================
# GLOBAL MOCKS — before ingest.py loads
# ============================================================

# -------- Fake config module --------
fake_config = types.ModuleType("config")
fake_config.PINECONE_API_KEY = "FAKE_KEY"
fake_config.PINECONE_INDEX_NAME = "FAKE_INDEX"

sys.modules["config"] = fake_config


# -------- Fake LangChain / Pinecone modules --------
def setup_fake_modules():
    fake_comm = types.ModuleType("langchain_community")
    fake_docloaders = types.ModuleType("langchain_community.document_loaders")
    fake_split = types.ModuleType("langchain_text_splitters")
    fake_hf = types.ModuleType("langchain_huggingface")
    fake_store = types.ModuleType("langchain_pinecone")
    fake_pine = types.ModuleType("pinecone")

    class FakeDirectoryLoader:
        def __init__(self, *a, **k): pass
        def load(self): return []

    class FakeTextLoader:
        def __init__(self, *a, **k): pass

    class FakeSplitter:
        def __init__(self, *a, **k): pass
        def split_documents(self, docs): return ["chunk1"]

    class FakeEmb:
        def __init__(self, *a, **k): pass

    class FakeVectorStore:
        @classmethod
        def from_documents(cls, *a, **k): return None

    class FakeIndexList:
        def names(self): return []

    class FakePineClient:
        def __init__(self, *a, **k): pass
        def list_indexes(self): return FakeIndexList()
        def create_index(self, *a, **k): pass

    fake_docloaders.DirectoryLoader = FakeDirectoryLoader
    fake_docloaders.TextLoader = FakeTextLoader
    fake_split.RecursiveCharacterTextSplitter = FakeSplitter
    fake_hf.HuggingFaceEmbeddings = FakeEmb
    fake_store.PineconeVectorStore = FakeVectorStore
    fake_pine.Pinecone = FakePineClient
    fake_pine.ServerlessSpec = lambda *a, **k: None

    # Register modules
    sys.modules["langchain_community"] = fake_comm
    sys.modules["langchain_community.document_loaders"] = fake_docloaders
    sys.modules["langchain_text_splitters"] = fake_split
    sys.modules["langchain_huggingface"] = fake_hf
    sys.modules["langchain_pinecone"] = fake_store
    sys.modules["pinecone"] = fake_pine


setup_fake_modules()


# ============================================================
# TESTS
# ============================================================

def test_main_directory_exists(monkeypatch, capsys):
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    runpy.run_path("ingest.py", run_name="__main__")

    out = capsys.readouterr().out
    assert "Loading documents from" in out


def test_main_directory_missing(monkeypatch, capsys):
    monkeypatch.setattr(os.path, "exists", lambda p: False)

    runpy.run_path("ingest.py", run_name="__main__")

    out = capsys.readouterr().out
    assert "Error: Knowledge base directory not found" in out


def test_ingest_no_documents(monkeypatch, capsys):
    import ingest

    class FakeLoader:
        def load(self): return []

    monkeypatch.setattr(ingest, "DirectoryLoader", lambda *a, **k: FakeLoader())

    ingest.ingest_data()
    out = capsys.readouterr().out
    assert "No documents found" in out


def test_ingest_with_documents(monkeypatch, capsys):
    import ingest

    class FakeDoc:
        page_content = "hello"

    class FakeLoader:
        def load(self): return [FakeDoc(), FakeDoc()]

    class FakeSplitter:
        def __init__(self, *a, **k): pass
        def split_documents(self, docs): return ["c1", "c2"]

    monkeypatch.setattr(ingest, "DirectoryLoader", lambda *a, **k: FakeLoader())
    monkeypatch.setattr(ingest, "RecursiveCharacterTextSplitter", FakeSplitter)

    ingest.ingest_data()
    out = capsys.readouterr().out

    assert "Loaded 2 documents" in out
    assert "Uploading" in out

def test_ingest_index_already_exists(monkeypatch, capsys):
    import ingest

    class FakeDoc:
        page_content = "hello"

    class FakeLoader:
        def load(self): return [FakeDoc()]

    # Fake Pinecone where index exists
    class FakeIndexList:
        def names(self):
            return ["FAKE_INDEX"]  # index already exists

    class FakePinecone:
        def __init__(self, *a, **k): pass
        def list_indexes(self): return FakeIndexList()
        def create_index(self, *a, **k): raise AssertionError("Should NOT call create_index")

    monkeypatch.setattr(ingest, "DirectoryLoader", lambda *a, **k: FakeLoader())
    monkeypatch.setattr(ingest, "Pinecone", FakePinecone)

    # Let other mocks remain as they are
    class FakeSplitter:
        def __init__(self, *a, **k): pass
        def split_documents(self, docs): return ["chunk1"]

    monkeypatch.setattr(ingest, "RecursiveCharacterTextSplitter", FakeSplitter)

    ingest.ingest_data()

    out = capsys.readouterr().out

    assert "Found existing index" in out
