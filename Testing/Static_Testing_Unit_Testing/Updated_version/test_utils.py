import pytest

from utils import safe_truncate, chunk_text


# ===== Tests for safe_truncate() =====
def test_safe_truncate_returns_original_when_within_limit():
	# Arrange
	text = "Short text"

	# Act
	result = safe_truncate(text, max_len=20)

	# Assert
	assert result == text


def test_safe_truncate_truncates_at_last_newline_with_ellipsis():
	# Arrange
	text = "Line one\nLine two that continues"

	# Act
	result = safe_truncate(text, max_len=15)

	# Assert
	assert result.endswith("\n\n... (Output truncated)")
	assert "Line one" in result
	assert "Line two" not in result


def test_safe_truncate_appends_inline_ellipsis_when_no_newline():
	# Arrange
	text = "abcdefghijklmnopqrstuvwxyz"

	# Act
	result = safe_truncate(text, max_len=10)

	# Assert
	assert result.startswith("abcdefghij")
	assert result.endswith(" ... (Output truncated)")


def test_safe_truncate_raises_type_error_for_non_string_input():
	# Arrange
	non_text_value = None

	# Act / Assert
	with pytest.raises(TypeError):
		safe_truncate(non_text_value, max_len=5)


# ===== Tests for chunk_text() =====
def test_chunk_text_splits_long_text_into_respected_chunks():
	# Arrange
	lines = [f"Line {i}" for i in range(10)]
	text = "\n".join(lines)

	# Act
	chunks = chunk_text(text, max_chars=12)

	# Assert
	assert len(chunks) > 1
	assert all(len(chunk) <= 12 for chunk in chunks if chunk)
	assert chunks[0].startswith("Line 0")
	assert "Line 9" in chunks[-1]


def test_chunk_text_returns_single_chunk_when_within_limit():
	# Arrange
	text = "line-one\nline-two"

	# Act
	chunks = chunk_text(text, max_chars=100)

	# Assert
	assert chunks == [text]


def test_chunk_text_returns_empty_list_for_empty_text():
	# Arrange
	text = ""

	# Act
	chunks = chunk_text(text, max_chars=50)

	# Assert
	assert chunks == []


def test_chunk_text_raises_attribute_error_for_non_string_input():
	# Arrange
	non_text_value = None

	# Act / Assert
	with pytest.raises(AttributeError):
		chunk_text(non_text_value, max_chars=10)
