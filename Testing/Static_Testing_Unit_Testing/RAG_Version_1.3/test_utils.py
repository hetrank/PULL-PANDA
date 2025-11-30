import utils


def test_safe_truncate_no_truncation():
    text = "short text"
    out = utils.safe_truncate(text, max_len=20)
    assert out == text


def test_safe_truncate_truncate_with_newline():
    text = "line1\nline2\nline3"
    # force truncation inside "line2"
    out = utils.safe_truncate(text, max_len=10)

    # should cut at newline before limit
    assert out.startswith("line1")
    assert out.endswith("... (Output truncated)")


def test_safe_truncate_truncate_without_newline():
    text = "ABCDEFGHIJKL"
    out = utils.safe_truncate(text, max_len=5)

    assert out.startswith("ABCDE")
    assert out.endswith("... (Output truncated)")


def test_safe_truncate_exact_newline_on_limit():
    text = "hello\nworld"
    # newline sits exactly at position 5
    out = utils.safe_truncate(text, max_len=6)

    # Should truncate cleanly at newline
    assert out.startswith("hello")
    assert out.endswith("... (Output truncated)")


def test_safe_truncate_max_len_zero():
    text = "Hello"
    out = utils.safe_truncate(text, max_len=0)

    # No newline possible, so we get prefix '' + ellipsis
    assert out.startswith("")  # empty string prefix
    assert out.endswith("... (Output truncated)")


def test_safe_truncate_empty_string():
    text = ""
    out = utils.safe_truncate(text)
    assert out == ""


def test_safe_truncate_one_char_limit():
    text = "ABCDEFG"
    out = utils.safe_truncate(text, max_len=1)

    assert out.startswith("A")
    assert out.endswith("... (Output truncated)")
