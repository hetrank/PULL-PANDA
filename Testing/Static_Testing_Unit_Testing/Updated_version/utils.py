"""Utility functions for safely truncating and chunking text content, 
such as GitHub PR diffs or long string outputs.
"""

from typing import List


def safe_truncate(text: str, max_len: int = 4000) -> str:
    """
    Truncates text to a maximum length, breaking cleanly at a newline if possible,
    and appends an ellipsis to indicate truncation.

    Args:
        text (str): The input text to truncate.
        max_len (int, optional): Maximum allowed character length. Defaults to 4000.

    Returns:
        str: Truncated text with ellipsis if necessary.
    """
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_newline = truncated.rfind('\n')
    if last_newline != -1:
        return truncated[:last_newline] + "\n\n... (Output truncated)"
    return truncated + " ... (Output truncated)"


def chunk_text(text: str, max_chars: int = 3500) -> List[str]:
    """
    Splits large text (e.g., a PR diff) into smaller chunks without exceeding
    the specified maximum character count.

    Args:
        text (str): The input text to split.
        max_chars (int, optional): The maximum number of characters per chunk. Defaults to 3500.

    Returns:
        List[str]: A list of text chunks.
    """
    lines = text.splitlines()
    chunks, current = [], []
    length = 0

    for line in lines:
        # +1 for newline character
        if length + len(line) + 1 > max_chars:
            chunks.append("\n".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line) + 1

    if current:
        chunks.append("\n".join(current))

    return chunks
