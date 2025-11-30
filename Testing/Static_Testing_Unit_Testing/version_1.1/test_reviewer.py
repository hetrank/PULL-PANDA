"""
Combined test suite for reviewer_refactored module - Edge Cases Only.
Contains critical edge cases for all functions without trivial tests.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
import requests
from reviewer_refactored import (
    fetch_pr_diff,
    post_review_comment,
    save_text_to_file,
    parser
)


class TestFetchPRDiffEdgeCases:
    """Critical edge cases for fetch_pr_diff."""

    @patch('reviewer_refactored.requests.get')
    def test_missing_diff_url_in_response(self, mock_get):
        """Test handling when diff_url is missing from PR data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"number": 1}  # No diff_url
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            fetch_pr_diff("owner", "repo", 1, "token123")
        
        assert "No diff_url found" in str(exc_info.value)

    @patch('reviewer_refactored.requests.get')
    def test_diff_url_none_value(self, mock_get):
        """Test handling when diff_url is explicitly None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"diff_url": None}
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            fetch_pr_diff("owner", "repo", 1, "token123")
        
        assert "No diff_url found" in str(exc_info.value)

    @patch('reviewer_refactored.requests.get')
    def test_pr_api_403_rate_limit(self, mock_get):
        """Test handling of rate limit exceeded (403)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_pr_diff("owner", "repo", 1, "token123")

    @patch('reviewer_refactored.requests.get')
    def test_diff_fetch_fails_after_successful_pr_fetch(self, mock_get):
        """Test handling when diff URL fetch fails after successful PR fetch."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 500
        
        mock_get.side_effect = [pr_response, diff_response]
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            fetch_pr_diff("owner", "repo", 1, "token123")
        
        assert "Failed to fetch diff from diff_url" in str(exc_info.value)

    @patch('reviewer_refactored.requests.get')
    def test_connection_timeout(self, mock_get):
        """Test handling of connection timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            fetch_pr_diff("owner", "repo", 1, "token123")

    @patch('reviewer_refactored.requests.get')
    def test_very_large_diff(self, mock_get):
        """Test handling of very large diff content (1MB)."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        large_diff = "+" * 1_000_000
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = large_diff
        
        mock_get.side_effect = [pr_response, diff_response]
        
        result = fetch_pr_diff("owner", "repo", 1, "token")
        
        assert len(result) == 1_000_000

    @patch('reviewer_refactored.requests.get')
    def test_special_characters_in_diff(self, mock_get):
        """Test handling of special characters and unicode in diff."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_content = "diff --git a/文件.py b/文件.py\n+中文内容\n+emoji: 🚀"
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = diff_content
        
        mock_get.side_effect = [pr_response, diff_response]
        
        result = fetch_pr_diff("owner", "repo", 1, "token")
        
        assert "🚀" in result
        assert "中文内容" in result

    @patch('reviewer_refactored.requests.get')
    def test_empty_diff_content(self, mock_get):
        """Test handling of empty diff (no changes)."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = ""
        
        mock_get.side_effect = [pr_response, diff_response]
        
        result = fetch_pr_diff("owner", "repo", 1, "token")
        
        assert result == ""

    @patch('reviewer_refactored.requests.get')
    def test_pr_json_parse_error(self, mock_get):
        """Test handling of malformed JSON in PR response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError):
            fetch_pr_diff("owner", "repo", 1, "token")


class TestPostReviewCommentEdgeCases:
    """Critical edge cases for post_review_comment."""

    @patch('reviewer_refactored.requests.post')
    def test_unauthorized_403_insufficient_permissions(self, mock_post):
        """Test handling of insufficient permissions (403)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "Forbidden - insufficient permissions"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            post_review_comment("owner", "repo", 1, "token", "comment")
        
        assert "Failed to post comment" in str(exc_info.value)

    @patch('reviewer_refactored.requests.post')
    def test_rate_limit_429(self, mock_post):
        """Test handling of rate limit exceeded (429)."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            post_review_comment("owner", "repo", 1, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_pr_not_found_404(self, mock_post):
        """Test handling when PR doesn't exist (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            post_review_comment("owner", "repo", 999, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_connection_timeout(self, mock_post):
        """Test handling of connection timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            post_review_comment("owner", "repo", 1, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_empty_comment_body(self, mock_post):
        """Test posting empty comment."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1, "body": ""}
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", "")
        
        assert result["body"] == ""

    @patch('reviewer_refactored.requests.post')
    def test_very_long_comment_65kb(self, mock_post):
        """Test posting very long comment (65KB)."""
        mock_response = Mock()
        mock_response.status_code = 201
        long_body = "x" * 65000
        mock_response.json.return_value = {"id": 1, "body": long_body}
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", long_body)
        
        assert len(result["body"]) == 65000

    @patch('reviewer_refactored.requests.post')
    def test_unicode_and_emoji_in_comment(self, mock_post):
        """Test posting comment with unicode and emoji."""
        mock_response = Mock()
        mock_response.status_code = 201
        unicode_body = "Great work! 👍 中文评论 🚀"
        mock_response.json.return_value = {"id": 1, "body": unicode_body}
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", unicode_body)
        
        assert "👍" in result["body"]
        assert "中文评论" in result["body"]

    @patch('reviewer_refactored.requests.post')
    def test_validation_error_422(self, mock_post):
        """Test handling of validation error (422)."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "Validation Failed",
            "errors": [{"field": "body", "code": "missing_field"}]
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            post_review_comment("owner", "repo", 1, "token", "")
        
        assert "Failed to post comment" in str(exc_info.value)

    @patch('reviewer_refactored.requests.post')
    def test_json_parse_error_in_response(self, mock_post):
        """Test handling of malformed JSON in response."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError):
            post_review_comment("owner", "repo", 1, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_both_status_codes_accepted(self, mock_post):
        """Test that both 200 and 201 are accepted as success."""
        # Test 200
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"id": 1}
        mock_post.return_value = mock_response_200
        
        result = post_review_comment("owner", "repo", 1, "token", "test")
        assert result["id"] == 1
        
        # Test 201
        mock_response_201 = Mock()
        mock_response_201.status_code = 201
        mock_response_201.json.return_value = {"id": 2}
        mock_post.return_value = mock_response_201
        
        result = post_review_comment("owner", "repo", 1, "token", "test")
        assert result["id"] == 2


class TestSaveTextToFileEdgeCases:
    """Critical edge cases for save_text_to_file."""

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

    def test_save_large_text_1mb(self):
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

    def test_file_handle_closed_on_error(self):
        """Test that file handle is closed even if write fails."""
        m = mock_open()
        mock_file = m.return_value
        mock_file.write.side_effect = IOError("Write failed")
        
        with patch('builtins.open', m):
            with pytest.raises(IOError):
                save_text_to_file("test.txt", "content")
            
            # File should be closed via context manager
            assert mock_file.__exit__.called

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

    def test_save_with_trailing_whitespace_preserved(self):
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


class TestParserEdgeCases:
    """Critical edge cases for parser."""

    def test_parser_parse_empty_string(self):
        """Test parser with empty string."""
        result = parser.parse("")
        assert result == ""
        assert isinstance(result, str)

    def test_parser_parse_multiline_string(self):
        """Test parser with multiline string."""
        text = "Line 1\nLine 2\nLine 3"
        result = parser.parse(text)
        assert result == text

    def test_parser_parse_unicode_string(self):
        """Test parser with unicode characters."""
        text = "Hello 世界 🌍"
        result = parser.parse(text)
        assert result == text
        assert "世界" in result

    def test_parser_with_very_long_text(self):
        """Test parser with very long text."""
        long_text = "x" * 100000
        result = parser.parse(long_text)
        assert len(result) == 100000

    def test_parser_with_special_characters(self):
        """Test parser with special characters."""
        text = "Special chars: @#$%^&*()[]{}|\\<>?/~`"
        result = parser.parse(text)
        assert result == text


class TestIntegrationEdgeCases:
    """Integration tests for edge case scenarios."""

    @patch('reviewer_refactored.requests.get')
    @patch('reviewer_refactored.requests.post')
    def test_fetch_diff_then_post_comment_flow(self, mock_post, mock_get):
        """Test complete flow: fetch diff, then post comment."""
        # Mock fetch_pr_diff
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff content"
        
        mock_get.side_effect = [pr_response, diff_response]
        
        # Mock post_review_comment
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": 123, "body": "review"}
        mock_post.return_value = post_response
        
        # Execute flow
        diff = fetch_pr_diff("owner", "repo", 1, "token")
        assert diff == "diff content"
        
        result = post_review_comment("owner", "repo", 1, "token", "review")
        assert result["id"] == 123

    @patch('reviewer_refactored.requests.get')
    def test_fetch_diff_timeout_then_retry_success(self, mock_get):
        """Test retry scenario after timeout."""
        # First call times out
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff"
        
        # First attempt: timeout, second attempt: success
        mock_get.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            pr_response,
            diff_response
        ]
        
        # First call should timeout
        with pytest.raises(requests.exceptions.Timeout):
            fetch_pr_diff("owner", "repo", 1, "token")
        
        # Second call should succeed
        result = fetch_pr_diff("owner", "repo", 1, "token")
        assert result == "diff"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])