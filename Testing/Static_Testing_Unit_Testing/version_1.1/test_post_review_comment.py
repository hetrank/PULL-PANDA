"""
Test suite for post_review_comment function.
Tests GitHub comment posting and error handling.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from reviewer_refactored import post_review_comment


class TestPostReviewComment:
    """Test suite for post_review_comment function."""

    @patch('reviewer_refactored.requests.post')
    def test_successful_comment_post_200(self, mock_post):
        """Test successful comment posting with 200 status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 123456,
            "body": "Great PR!",
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", "Great PR!")
        
        assert result["id"] == 123456
        assert result["body"] == "Great PR!"

    @patch('reviewer_refactored.requests.post')
    def test_successful_comment_post_201(self, mock_post):
        """Test successful comment posting with 201 status."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 789,
            "body": "LGTM"
        }
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 5, "token", "LGTM")
        
        assert result["id"] == 789

    @patch('reviewer_refactored.requests.post')
    def test_unauthorized_403_error(self, mock_post):
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
    def test_unauthorized_401_error(self, mock_post):
        """Test handling of invalid token (401)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "message": "Bad credentials"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            post_review_comment("owner", "repo", 1, "bad_token", "comment")

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
    def test_rate_limit_error_429(self, mock_post):
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
    def test_server_error_500(self, mock_post):
        """Test handling of server error (500)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "message": "Internal Server Error"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.exceptions.HTTPError):
            post_review_comment("owner", "repo", 1, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_correct_url_construction(self, mock_post):
        """Test that comment URL is constructed correctly."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response
        
        post_review_comment("my-owner", "my-repo", 42, "token", "test")
        
        expected_url = "https://api.github.com/repos/my-owner/my-repo/issues/42/comments"
        actual_url = mock_post.call_args[0][0]
        assert actual_url == expected_url

    @patch('reviewer_refactored.requests.post')
    def test_correct_headers_sent(self, mock_post):
        """Test that correct headers are included."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response
        
        post_review_comment("owner", "repo", 1, "my_token", "body")
        
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "token my_token"
        assert headers["Accept"] == "application/vnd.github+json"

    @patch('reviewer_refactored.requests.post')
    def test_correct_payload_sent(self, mock_post):
        """Test that correct payload is sent."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response
        
        review_text = "This is a detailed review with multiple lines.\nSecond line."
        post_review_comment("owner", "repo", 1, "token", review_text)
        
        payload = mock_post.call_args[1]["json"]
        assert payload["body"] == review_text

    @patch('reviewer_refactored.requests.post')
    def test_timeout_parameter(self, mock_post):
        """Test that timeout is set correctly."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response
        
        post_review_comment("owner", "repo", 1, "token", "comment")
        
        assert mock_post.call_args[1]["timeout"] == 10

    @patch('reviewer_refactored.requests.post')
    def test_connection_timeout(self, mock_post):
        """Test handling of connection timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            post_review_comment("owner", "repo", 1, "token", "comment")

    @patch('reviewer_refactored.requests.post')
    def test_network_error(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )
        
        with pytest.raises(requests.exceptions.ConnectionError):
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
    def test_very_long_comment(self, mock_post):
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
    def test_markdown_in_comment(self, mock_post):
        """Test posting comment with markdown formatting."""
        mock_response = Mock()
        mock_response.status_code = 201
        markdown_body = "# Title\n- Item 1\n- Item 2\n```python\ncode\n```"
        mock_response.json.return_value = {"id": 1, "body": markdown_body}
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", markdown_body)
        
        assert "```python" in result["body"]

    @patch('reviewer_refactored.requests.post')
    def test_special_characters_in_comment(self, mock_post):
        """Test posting comment with special characters."""
        mock_response = Mock()
        mock_response.status_code = 201
        special_body = "Test with quotes: \"hello\" and 'world' & <tag>"
        mock_response.json.return_value = {"id": 1, "body": special_body}
        mock_post.return_value = mock_response
        
        result = post_review_comment("owner", "repo", 1, "token", special_body)
        
        assert '"hello"' in result["body"]

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