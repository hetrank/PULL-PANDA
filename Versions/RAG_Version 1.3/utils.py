# utils.py

import os
from typing import List

def safe_truncate(text: str, max_len: int = 4000) -> str:
    """
    Truncates text to a max length, ensuring it breaks cleanly at a newline
    and adds an ellipsis for clarity.
    """
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_newline = truncated.rfind('\n')
    if last_newline != -1:
        return truncated[:last_newline] + "\n\n... (Output truncated)"
    return truncated + " ... (Output truncated)"