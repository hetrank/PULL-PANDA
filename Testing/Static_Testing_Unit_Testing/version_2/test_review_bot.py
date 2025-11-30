import importlib.util
import sys
import types
from pathlib import Path
import pytest


def import_review_module(monkeypatch):
    """Import the review_bot module with required env vars and a safe Groq stub."""
    # Arrange: ensure env vars exist so module import doesn't SystemExit
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GROQ_API_KEY", "groqkey")

    # Provide a fake groq module with a Groq class that can be replaced later
    fake_groq = types.ModuleType("groq")

    class FakeGroqClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            # a simple chat attribute to satisfy generate_review
            class Chat:
                class Completions:
                    def create(self, **kwargs):
                        raise RuntimeError("No stubbed response set")

                completions = Completions()

            self.chat = Chat()

    fake_groq.Groq = FakeGroqClient
    sys.modules["groq"] = fake_groq

    # Import the target module by path relative to this test file
    target_path = Path(__file__).resolve().parent / "review_bot.py"
    spec = importlib.util.spec_from_file_location("review_bot", str(target_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["review_bot"] = module
    spec.loader.exec_module(module)
    return module


# ===== Tests for chunk_text() =====


def test_chunk_text_empty_returns_empty_list(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)
    text = ""

    # Act
    chunks = module.chunk_text(text)

    # Assert
    assert isinstance(chunks, list)
    assert chunks == []


def test_chunk_text_splits_lines_when_max_exceeded(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)
    # create three lines of length ~30; max_chars will force split after two lines
    lines = ["x" * 30 for _ in range(4)]
    text = "\n".join(lines)

    # Act
    chunks = module.chunk_text(text, max_chars=65)

    # Assert
    # with max_chars 65, two lines (~60 chars + newline) fit, so expect 2 chunks
    assert len(chunks) == 2
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_text_single_very_long_line_returns_leading_empty_chunk_and_line(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)
    long_line = "A" * 5000
    text = long_line

    # Act
    chunks = module.chunk_text(text, max_chars=1000)

    # Assert
    # Current implementation appends an empty chunk when a single line exceeds max_chars
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    assert chunks[-1] == long_line


# ===== Tests for fetch_diff() =====


def test_fetch_diff_success(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    class FakeResp1:
        def raise_for_status(self):
            return None

        def json(self):
            return {"diff_url": "https://example.com/diff/1"}

    class FakeResp2:
        def raise_for_status(self):
            return None

        text = "DIFF CONTENT"

    calls = {"n": 0}

    def fake_get(url, headers=None, **kwargs):
        calls["n"] += 1
        return FakeResp1() if calls["n"] == 1 else FakeResp2()

    monkeypatch.setattr(module, "requests", types.SimpleNamespace(get=fake_get))

    # Act
    diff = module.fetch_diff()

    # Assert
    assert diff == "DIFF CONTENT"


def test_fetch_diff_raises_on_http_error(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    class BadResp:
        def raise_for_status(self):
            raise RuntimeError("bad status")

    fake_requests = types.SimpleNamespace(get=lambda *a, **k: BadResp())
    monkeypatch.setattr(module, "requests", fake_requests)

    # Act / Assert
    with pytest.raises(RuntimeError):
        module.fetch_diff()


# ===== Tests for post_comment() =====


def test_post_comment_success(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    class FakeResp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, **kwargs):
        assert isinstance(json, dict)
        assert "body" in json
        return FakeResp()

    monkeypatch.setattr(module, "requests", types.SimpleNamespace(post=fake_post))

    # Act
    # This should not raise
    module.post_comment("hello")


def test_post_comment_raises_on_bad_response(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    class BadResp:
        def raise_for_status(self):
            raise RuntimeError("post failed")

    monkeypatch.setattr(module, "requests", types.SimpleNamespace(post=lambda *a, **k: BadResp()))

    # Act / Assert
    with pytest.raises(Exception):
        module.post_comment("body")


# ===== Tests for generate_review() =====


def test_generate_review_returns_content(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    class FakeResponse:
        class Choice:
            class Message:
                def __init__(self, content):
                    self.content = content

            def __init__(self, content):
                self.message = FakeResponse.Choice.Message(content)

        def __init__(self, content):
            self.choices = [FakeResponse.Choice(content)]

    # Replace the module.client with a fake that returns our response
    fake_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: FakeResponse("REVIEW TEXT")
            )
        )
    )
    module.client = fake_client

    # Act
    out = module.generate_review("diff chunk")

    # Assert
    assert out == "REVIEW TEXT"


def test_generate_review_propagates_errors(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    fake_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("llm error"))
            )
        )
    )
    module.client = fake_client

    # Act / Assert
    with pytest.raises(RuntimeError):
        module.generate_review("diff")


# ===== Tests for main() =====


def test_main_invokes_generate_and_posts(monkeypatch):
    # Arrange
    module = import_review_module(monkeypatch)

    # Stub fetch_diff to return a payload and chunk_text to split into two chunks
    monkeypatch.setattr(module, "fetch_diff", lambda: "chunk1\nchunk2")
    monkeypatch.setattr(module, "chunk_text", lambda text: ["c1", "c2"]) 

    # generate_review should be called per chunk
    reviews = ["R1", "R2"]

    def fake_generate(chunk):
        return reviews.pop(0)

    monkeypatch.setattr(module, "generate_review", fake_generate)

    posted = []

    def fake_post(body):
        posted.append(body)

    monkeypatch.setattr(module, "post_comment", fake_post)

    # Act
    module.main()

    # Assert
    # Two posts should be made
    assert len(posted) == 2
    # Ensure that bodies contain the phrase "AI Review (Part"
    assert "AI Review (Part 1/2)" in posted[0]
    assert "AI Review (Part 2/2)" in posted[1]
