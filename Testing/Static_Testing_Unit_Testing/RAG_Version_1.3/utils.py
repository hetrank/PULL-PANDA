"""
Utility helper functions for text processing, including safe truncation
for long strings such as LLM outputs.
"""


def safe_truncate(text: str, max_len: int = 4000) -> str:
    """
    Truncates text to a maximum length, breaking at the last newline
    before the limit when possible. Adds an ellipsis to indicate truncation.

    Args:
        text: The input string to truncate.
        max_len: Maximum allowed length.

    Returns:
        A cleanly truncated string, with an ellipsis if truncation occurs.
    """
    if len(text) <= max_len:
        return text

    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")

    if last_newline != -1:
        return truncated[:last_newline] + "\n\n... (Output truncated)"

    return truncated + " ... (Output truncated)"
