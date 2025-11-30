"""
Test suite for fetch_pr_diff function.
Tests GitHub API interaction and error handling.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from reviewer_refactored import fetch_pr_diff


class TestFetchPRDiff:
    """Test suite for fetch_pr_diff function."""

    @patch('reviewer_refactored.requests.get')
    def test_successful_diff_fetch(self, mock_get):
        """Test successful PR diff retrieval."""
        # Mock PR data response
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        # Mock diff content response
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff --git a/file.py b/file.py\n+new line"
        
        mock_get.side_effect = [pr_response, diff_response]
        
        result = fetch_pr_diff("owner", "repo", 1, "token123")
        
        assert result == "diff --git a/file.py b/file.py\n+new line"
        assert mock_get.call_count == 2

    @patch('reviewer_refactored.requests.get')
    def test_pr_api_404_error(self, mock_get):
        """Test handling of PR not found (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            fetch_pr_diff("owner", "repo", 999, "token123")
        
        assert "GitHub API Error" in str(exc_info.value)

    @patch('reviewer_refactored.requests.get')
    def test_pr_api_401_unauthorized(self, mock_get):
        """Test handling of unauthorized access (401)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_pr_diff("owner", "repo", 1, "invalid_token")

    @patch('reviewer_refactored.requests.get')
    def test_pr_api_403_forbidden(self, mock_get):
        """Test handling of forbidden access (403)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_pr_diff("owner", "repo", 1, "token123")

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
    def test_diff_fetch_fails_404(self, mock_get):
        """Test handling when diff URL returns 404."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 404
        
        mock_get.side_effect = [pr_response, diff_response]
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            fetch_pr_diff("owner", "repo", 1, "token123")
        
        assert "Failed to fetch diff from diff_url" in str(exc_info.value)

    @patch('reviewer_refactored.requests.get')
    def test_diff_fetch_fails_500(self, mock_get):
        """Test handling when diff URL returns server error."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 500
        
        mock_get.side_effect = [pr_response, diff_response]
        
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_pr_diff("owner", "repo", 1, "token123")

    @patch('reviewer_refactored.requests.get')
    def test_connection_timeout(self, mock_get):
        """Test handling of connection timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            fetch_pr_diff("owner", "repo", 1, "token123")

    @patch('reviewer_refactored.requests.get')
    def test_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )
        
        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_pr_diff("owner", "repo", 1, "token123")

    @patch('reviewer_refactored.requests.get')
    def test_correct_headers_sent(self, mock_get):
        """Test that correct authorization headers are sent."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff content"
        
        mock_get.side_effect = [pr_response, diff_response]
        
        fetch_pr_diff("owner", "repo", 1, "my_token")
        
        # Check first call (PR data)
        first_call = mock_get.call_args_list[0]
        assert first_call[1]["headers"]["Authorization"] == "token my_token"
        
        # Check second call (diff)
        second_call = mock_get.call_args_list[1]
        assert second_call[1]["headers"]["Authorization"] == "token my_token"

    @patch('reviewer_refactored.requests.get')
    def test_timeout_parameter_used(self, mock_get):
        """Test that timeout parameter is passed to requests."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff"
        
        mock_get.side_effect = [pr_response, diff_response]
        
        fetch_pr_diff("owner", "repo", 1, "token")
        
        # Both calls should have timeout
        for call in mock_get.call_args_list:
            assert call[1]["timeout"] == 10

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
    def test_very_large_diff(self, mock_get):
        """Test handling of very large diff content."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/owner/repo/pull/1.diff"
        }
        
        # Large diff (1MB)
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
    def test_pr_json_parse_error(self, mock_get):
        """Test handling of malformed JSON in PR response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError):
            fetch_pr_diff("owner", "repo", 1, "token")

    @patch('reviewer_refactored.requests.get')
    def test_correct_url_construction(self, mock_get):
        """Test that PR URL is constructed correctly."""
        pr_response = Mock()
        pr_response.status_code = 200
        pr_response.json.return_value = {
            "diff_url": "https://github.com/test/test/pull/123.diff"
        }
        
        diff_response = Mock()
        diff_response.status_code = 200
        diff_response.text = "diff"
        
        mock_get.side_effect = [pr_response, diff_response]
        
        fetch_pr_diff("test-owner", "test-repo", 456, "token")
        
        expected_url = "https://api.github.com/repos/test-owner/test-repo/pulls/456"
        actual_url = mock_get.call_args_list[0][0][0]
        assert actual_url == expected_url