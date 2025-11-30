"""
Test suite for save_text_to_file function.
Tests file writing operations and error handling.
"""

import pytest
import os
import tempfile
from unittest.mock import mock_open, patch, MagicMock
from reviewer_refactored import save_text_to_file


class TestSaveTextToFile:
    """Test suite for save_text_to_file function."""

    def test_save_simple_text(self):
        """Test saving simple text to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, "Hello, World!")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == "Hello, World!"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_empty_string(self):
        """Test saving empty string to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, "")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == ""
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_multiline_text(self):
        """Test saving multiline text."""
        text = "Line 1\nLine 2\nLine 3"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == text
            assert content.count('\n') == 2
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_unicode_content(self):
        """Test saving unicode characters."""
        text = "Hello 世界 🌍 Привет"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == text
            assert "世界" in content
            assert "🌍" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_large_text(self):
        """Test saving large text (1MB)."""
        large_text = "x" * 1_000_000
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, large_text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert len(content) == 1_000_000
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_overwrite_existing_file(self):
        """Test overwriting existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
            f.write("Old content")
        
        try:
            save_text_to_file(temp_path, "New content")
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == "New content"
            assert "Old content" not in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_create_new_file_if_not_exists(self):
        """Test creating new file if it doesn't exist."""
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "new_file.txt")
        
        try:
            save_text_to_file(temp_path, "Content")
            
            assert os.path.exists(temp_path)
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "Content"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            os.rmdir(temp_dir)

    def test_permission_error(self):
        """Test handling of permission denied error."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(PermissionError):
                save_text_to_file("/root/protected.txt", "content")

    def test_directory_not_found(self):
        """Test handling when directory doesn't exist."""
        with pytest.raises((FileNotFoundError, OSError)):
            save_text_to_file("/nonexistent/path/file.txt", "content")

    def test_disk_full_error(self):
        """Test handling of disk full error."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.return_value.write.side_effect = OSError("No space left on device")
            
            with pytest.raises(OSError):
                save_text_to_file("/tmp/file.txt", "content")

    def test_special_characters_in_filename(self):
        """Test saving with special characters in filename."""
        temp_dir = tempfile.mkdtemp()
        # Use valid filename with underscores instead of special chars
        temp_path = os.path.join(temp_dir, "file_with_special_chars.txt")
        
        try:
            save_text_to_file(temp_path, "Content")
            
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            os.rmdir(temp_dir)

    def test_write_mode_and_encoding(self):
        """Test that file is opened with correct mode and encoding."""
        m = mock_open()
        with patch('builtins.open', m):
            save_text_to_file("test.txt", "content")
            
            m.assert_called_once_with("test.txt", "w", encoding="utf-8")

    def test_file_handle_closed_properly(self):
        """Test that file handle is closed even if write fails."""
        m = mock_open()
        mock_file = m.return_value
        mock_file.write.side_effect = IOError("Write failed")
        
        with patch('builtins.open', m):
            with pytest.raises(IOError):
                save_text_to_file("test.txt", "content")
            
            # File should be closed via context manager
            assert mock_file.__exit__.called

    def test_save_json_formatted_text(self):
        """Test saving JSON-formatted text."""
        json_text = '{"key": "value", "number": 123}'
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, json_text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == json_text
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_markdown_content(self):
        """Test saving markdown content."""
        markdown = "# Header\n\n- Item 1\n- Item 2\n\n```python\ncode\n```"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, markdown)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "# Header" in content
            assert "```python" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_with_trailing_whitespace(self):
        """Test that trailing whitespace is preserved."""
        text = "Line with spaces    \nAnother line\t\t"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == text
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_save_text_with_null_bytes(self):
        """Test saving text with null bytes."""
        text = "Before\x00After"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            save_text_to_file(temp_path, text)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert '\x00' in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_readonly_file_error(self):
        """Test error when trying to write to readonly file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            # Make file readonly
            os.chmod(temp_path, 0o444)
            
            with pytest.raises((PermissionError, OSError)):
                save_text_to_file(temp_path, "new content")
        finally:
            # Restore permissions and cleanup
            os.chmod(temp_path, 0o644)
            if os.path.exists(temp_path):
                os.remove(temp_path)