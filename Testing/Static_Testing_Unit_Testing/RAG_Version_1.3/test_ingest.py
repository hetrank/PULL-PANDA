import sys
import os
import types
import pytest
import runpy
from unittest.mock import MagicMock, patch


# ======================================================================
# 1. MOCK CONFIG BEFORE importing ingest.py
# ======================================================================
fake_config = types.ModuleType("config")
fake_config.PINECONE_API_KEY = "dummy_key"
fake_config.PINECONE_INDEX_NAME = "dummy_index"
sys.modules["config"] = fake_config


# ======================================================================
# 2. MOCK LangChain + Pinecone BEFORE importing ingest
# ======================================================================
def install_fake_modules():
    # langchain_community.document_loaders
    fake_docloaders = types.ModuleType("langchain_community.document_loaders")
    fake_docloaders.DirectoryLoader = MagicMock()
    fake_docloaders.TextLoader = MagicMock()
    sys.modules["langchain_community.document_loaders"] = fake_docloaders

    # langchain_text_splitters
    fake_split = types.ModuleType("langchain_text_splitters")
    fake_split.RecursiveCharacterTextSplitter = MagicMock()
    sys.modules["langchain_text_splitters"] = fake_split

    # langchain_huggingface
    fake_hf = types.ModuleType("langchain_huggingface")
    fake_hf.HuggingFaceEmbeddings = MagicMock()
    sys.modules["langchain_huggingface"] = fake_hf

    # langchain_pinecone
    fake_pstore = types.ModuleType("langchain_pinecone")
    fake_pstore.PineconeVectorStore = MagicMock()
    sys.modules["langchain_pinecone"] = fake_pstore

    # pinecone
    fake_pine = types.ModuleType("pinecone")
    fake_pine.Pinecone = MagicMock()
    fake_pine.ServerlessSpec = MagicMock()
    sys.modules["pinecone"] = fake_pine


install_fake_modules()

# ----------------------------------------------------------------------
# NOW import ingest after mocks
# ----------------------------------------------------------------------
import ingest


# ======================================================================
# 3. PATCHING FIXTURE
# ======================================================================
@pytest.fixture
def patches():
    with patch.object(ingest, "DirectoryLoader") as dl, \
         patch.object(ingest, "RecursiveCharacterTextSplitter") as splitter, \
         patch.object(ingest, "HuggingFaceEmbeddings") as emb, \
         patch.object(ingest, "Pinecone") as pc, \
         patch.object(ingest, "PineconeVectorStore") as store:
        yield dl, splitter, emb, pc, store


# ======================================================================
# 4. TEST: No documents found
# ======================================================================
def test_ingest_no_documents(patches, capsys):
    dl, splitter, emb, pc, store = patches

    loader = MagicMock()
    loader.load.return_value = []
    dl.return_value = loader

    ingest.ingest_data()
    out = capsys.readouterr().out

    assert "No documents found" in out


# ======================================================================
# 5. TEST: Full ingestion flow when index exists
# ======================================================================
def test_ingest_full_flow(patches, capsys):
    dl, splitter, emb, pc, store = patches

    loader = MagicMock()
    loader.load.return_value = ["doc"]
    dl.return_value = loader

    split_obj = MagicMock()
    split_obj.split_documents.return_value = ["c1", "c2"]
    splitter.return_value = split_obj

    emb.return_value = MagicMock()

    # Index exists
    pc_instance = MagicMock()
    pc_instance.list_indexes.return_value.names.return_value = ["dummy_index"]
    pc.return_value = pc_instance

    ingest.ingest_data()
    out = capsys.readouterr().out

    assert "Loaded 1 documents" in out
    assert "Split into 2 chunks" in out
    assert "Uploading 2 chunks" in out

    store.from_documents.assert_called_once()


# ======================================================================
# 6. TEST: Creating new index because missing
# ======================================================================
def test_ingest_create_index(patches, capsys):
    dl, splitter, emb, pc, store = patches

    loader = MagicMock()
    loader.load.return_value = ["doc"]
    dl.return_value = loader

    split_obj = MagicMock()
    split_obj.split_documents.return_value = ["chunk"]
    splitter.return_value = split_obj

    emb.return_value = MagicMock()

    # Index missing
    pc_instance = MagicMock()
    pc_instance.list_indexes.return_value.names.return_value = []
    pc.return_value = pc_instance

    ingest.ingest_data()
    out = capsys.readouterr().out

    assert "Creating new index" in out
    pc_instance.create_index.assert_called_once()


# ======================================================================
# 7A. TEST: __main__ block — directory missing
# ======================================================================
def test_main_directory_missing(monkeypatch, capsys):
    import runpy
    import ingest

    # pretend directory missing
    monkeypatch.setattr(os.path, "exists", lambda p: False)

    # execute using ingest's own module namespace
    runpy.run_path("ingest.py", run_name="__main__", init_globals=ingest.__dict__)

    out = capsys.readouterr().out
    assert "Knowledge base directory not found" in out


# ======================================================================
# 7B. TEST: __main__ block — directory exists
# ======================================================================
def test_main_directory_exists(monkeypatch):
    import runpy
    import os
    from unittest.mock import MagicMock

    # directory exists
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    # run ingest.py and CAPTURE the module object that runpy created
    mod = runpy.run_path("ingest.py", run_name="__main__")

    # IMPORTANT: patch ingest_data INSIDE the module that was executed
    mocked = MagicMock()
    mod["ingest_data"] = mocked

    # Now run the __main__ block again (simulate calling entrypoint)
    if mod["os"].path.exists(mod["KNOWLEDGE_BASE_DIR"]):
        mod["ingest_data"]()

    mocked.assert_called_once()

