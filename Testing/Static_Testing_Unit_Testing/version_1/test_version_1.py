"""
Comprehensive test suite for GitHub Pull Request Review Tool.

Tests cover all functions, edge cases, error handling, and integration scenarios.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import requests
from io import StringIO
import sys
import os


class TestFetchPRDiff:
    """Tests for fetch_pr_diff function."""

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_success(self, mock_get):
        """Test successful PR diff fetching."""
        # Mock PR data response
        mock_pr_response = Mock()
        mock_pr_response.json.return_value = {
            "diff_url": "https://github.com/test/repo/pulls/1.diff"
        }
        mock_pr_response.raise_for_status = Mock()
        
        # Mock diff content response
        mock_diff_response = Mock()
        mock_diff_response.text = "diff --git a/file.py b/file.py\n+added line"
        mock_diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_pr_response, mock_diff_response]
        
        # Import function after mocking environment
        from version_1 import fetch_pr_diff
        
        result = fetch_pr_diff("owner", "repo", "123", "token123")
        
        assert result == "diff --git a/file.py b/file.py\n+added line"
        assert mock_get.call_count == 2
        
        # Verify API calls
        mock_get.assert_any_call(
            "https://api.github.com/repos/owner/repo/pulls/123",
            headers={"Authorization": "token token123"},
            timeout=10
        )

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_api_error(self, mock_get):
        """Test handling of GitHub API errors."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        from version_1 import fetch_pr_diff
        
        with pytest.raises(RuntimeError, match="GitHub API Error"):
            fetch_pr_diff("owner", "repo", "123", "token123")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_timeout(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        from version_1 import fetch_pr_diff
        
        with pytest.raises(RuntimeError):
            fetch_pr_diff("owner", "repo", "123", "token123")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_http_error(self, mock_get):
        """Test handling of HTTP errors (404, 403, etc.)."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        from version_1 import fetch_pr_diff
        
        with pytest.raises(RuntimeError):
            fetch_pr_diff("owner", "repo", "999", "invalid_token")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        from version_1 import fetch_pr_diff
        
        with pytest.raises((RuntimeError, ValueError)):
            fetch_pr_diff("owner", "repo", "123", "token123")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_fetch_pr_diff_empty_diff(self, mock_get):
        """Test handling of empty diff content."""
        mock_pr_response = Mock()
        mock_pr_response.json.return_value = {"diff_url": "https://test.diff"}
        mock_pr_response.raise_for_status = Mock()
        
        mock_diff_response = Mock()
        mock_diff_response.text = ""
        mock_diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_pr_response, mock_diff_response]
        
        from version_1 import fetch_pr_diff
        
        result = fetch_pr_diff("owner", "repo", "123", "token123")
        assert result == ""


class TestPostReviewComment:
    """Tests for post_review_comment function."""

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_post_review_comment_success(self, mock_post):
        """Test successful comment posting."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 12345,
            "html_url": "https://github.com/owner/repo/pull/123#issuecomment-12345"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        from version_1 import post_review_comment
        
        result = post_review_comment("owner", "repo", "123", "token123", "Great code!")
        
        assert result["id"] == 12345
        assert "html_url" in result
        
        # Verify API call
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues/123/comments",
            headers={
                "Authorization": "token token123",
                "Accept": "application/vnd.github+json"
            },
            json={"body": "Great code!"},
            timeout=10
        )

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_post_review_comment_api_error(self, mock_post):
        """Test handling of API errors when posting."""
        mock_post.side_effect = requests.exceptions.RequestException("API Error")
        
        from version_1 import post_review_comment
        
        with pytest.raises(RuntimeError, match="Failed to post comment"):
            post_review_comment("owner", "repo", "123", "token123", "Review")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_post_review_comment_unauthorized(self, mock_post):
        """Test handling of unauthorized access."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")
        mock_post.return_value = mock_response
        
        from version_1 import post_review_comment
        
        with pytest.raises(RuntimeError):
            post_review_comment("owner", "repo", "123", "bad_token", "Review")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_post_review_comment_timeout(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        from version_1 import post_review_comment
        
        with pytest.raises(RuntimeError):
            post_review_comment("owner", "repo", "123", "token123", "Review")

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_post_review_comment_long_body(self, mock_post):
        """Test posting comment with very long review body."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "html_url": "https://test"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        from version_1 import post_review_comment
        
        long_review = "x" * 10000
        result = post_review_comment("owner", "repo", "123", "token123", long_review)
        
        assert result["id"] == 1
        # Verify the long body was sent
        call_args = mock_post.call_args
        assert call_args[1]["json"]["body"] == long_review


class TestMainFunction:
    """Tests for main execution function."""

    @patch.dict('os.environ', {
        'GITHUB_TOKEN': 'test_token',
        'API_KEY': 'groq_key',
        'OWNER': 'test_owner',
        'REPO': 'test_repo',
        'PR_NUMBER': '123'
    })
    @patch('version_1.post_review_comment')
    @patch('version_1.REVIEW_CHAIN')
    @patch('version_1.fetch_pr_diff')
    def test_main_success(self, mock_fetch, mock_chain, mock_post):
        """Test successful main execution flow."""
        mock_fetch.return_value = "diff content here"
        mock_chain.invoke.return_value = "AI review result"
        mock_post.return_value = {"html_url": "https://github.com/test"}
        
        from version_1 import main
        
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        main()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "✅ Diff fetched successfully" in output
        assert "=== AI REVIEW RESULT ===" in output
        assert "✅ Review posted at:" in output
        
        mock_fetch.assert_called_once()
        mock_chain.invoke.assert_called_once()
        mock_post.assert_called_once()

    @patch.dict('os.environ', {
        'GITHUB_TOKEN': 'test_token',
        'API_KEY': 'groq_key',
        'OWNER': 'test_owner',
        'REPO': 'test_repo',
        'PR_NUMBER': '123'
    })
    @patch('version_1.fetch_pr_diff')
    def test_main_fetch_error(self, mock_fetch):
        """Test main function handling fetch errors."""
        mock_fetch.side_effect = RuntimeError("GitHub API Error")
        
        from version_1 import main
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        main()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "Error:" in output

    @patch.dict('os.environ', {
        'GITHUB_TOKEN': 'test_token',
        'API_KEY': 'groq_key',
        'OWNER': 'test_owner',
        'REPO': 'test_repo',
        'PR_NUMBER': '123'
    })
    @patch('version_1.post_review_comment')
    @patch('version_1.REVIEW_CHAIN')
    @patch('version_1.fetch_pr_diff')
    def test_main_post_error(self, mock_fetch, mock_chain, mock_post):
        """Test main function handling post errors."""
        mock_fetch.return_value = "diff content"
        mock_chain.invoke.return_value = "review"
        mock_post.side_effect = RuntimeError("Failed to post")
        
        from version_1 import main
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        main()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "Error:" in output

    @patch.dict('os.environ', {
        'GITHUB_TOKEN': 'test_token',
        'API_KEY': 'groq_key',
        'OWNER': 'test_owner',
        'REPO': 'test_repo',
        'PR_NUMBER': '123'
    })
    @patch('version_1.post_review_comment')
    @patch('version_1.REVIEW_CHAIN')
    @patch('version_1.fetch_pr_diff')
    def test_main_diff_truncation(self, mock_fetch, mock_chain, mock_post):
        """Test that diff is truncated to 4000 characters."""
        long_diff = "x" * 10000
        mock_fetch.return_value = long_diff
        mock_chain.invoke.return_value = "review"
        mock_post.return_value = {"html_url": "https://test"}
        
        from version_1 import main
        
        # Capture output to prevent print statements
        captured_output = StringIO()
        sys.stdout = captured_output
        main()
        sys.stdout = sys.__stdout__
        
        # Verify truncation
        call_args = mock_chain.invoke.call_args
        assert len(call_args[0][0]["diff"]) == 4000


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    def test_missing_groq_api_key(self):
        """Test error when GROQ_API_KEY is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY not found"):
                import importlib
                import sys
                # Remove module if already imported
                if 'version_1' in sys.modules:
                    del sys.modules['version_1']
                import version_1

    @patch.dict('os.environ', {
        'API_KEY': 'test_key',
        'GITHUB_TOKEN': '',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    def test_empty_github_token(self):
        """Test behavior with empty GitHub token."""
        import importlib
        import sys
        if 'version_1' in sys.modules:
            del sys.modules['version_1']
        import version_1
        importlib.reload(version_1)
        assert version_1.GITHUB_TOKEN == ''

    @patch.dict('os.environ', {
        'API_KEY': 'test_key',
        'GITHUB_TOKEN': 'token',
        'OWNER': '',
        'REPO': '',
        'PR_NUMBER': ''
    })
    def test_empty_config_values(self):
        """Test behavior with empty config values."""
        import importlib
        import sys
        if 'version_1' in sys.modules:
            del sys.modules['version_1']
        import version_1
        importlib.reload(version_1)
        assert version_1.OWNER == ''
        assert version_1.REPO == ''
        assert version_1.PR_NUMBER == ''


class TestIntegration:
    """Integration tests for complete workflows."""

    @patch.dict('os.environ', {
        'GITHUB_TOKEN': 'integration_token',
        'API_KEY': 'groq_integration_key',
        'OWNER': 'test_owner',
        'REPO': 'test_repo',
        'PR_NUMBER': '456'
    })
    @patch('requests.post')
    @patch('requests.get')
    @patch('version_1.REVIEW_CHAIN')
    def test_full_workflow_integration(self, mock_chain, mock_get, mock_post):
        """Test complete workflow from fetch to post."""
        # Setup mocks for fetch
        mock_pr_response = Mock()
        mock_pr_response.json.return_value = {"diff_url": "https://diff.url"}
        mock_pr_response.raise_for_status = Mock()
        
        mock_diff_response = Mock()
        mock_diff_response.text = "diff --git\n+new code"
        mock_diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_pr_response, mock_diff_response]
        
        # Setup mock for AI review
        mock_chain.invoke.return_value = "Excellent work! LGTM."
        
        # Setup mock for post
        mock_comment_response = Mock()
        mock_comment_response.json.return_value = {
            "html_url": "https://github.com/test_owner/test_repo/pull/456#comment"
        }
        mock_comment_response.raise_for_status = Mock()
        mock_post.return_value = mock_comment_response
        
        from version_1 import main
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        main()
        
        sys.stdout = sys.__stdout__
        
        # Verify complete flow
        assert mock_get.call_count == 2
        mock_chain.invoke.assert_called_once()
        mock_post.assert_called_once()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_unicode_in_diff(self, mock_get):
        """Test handling of Unicode characters in diff."""
        mock_pr_response = Mock()
        mock_pr_response.json.return_value = {"diff_url": "https://test"}
        mock_pr_response.raise_for_status = Mock()
        
        mock_diff_response = Mock()
        mock_diff_response.text = "diff --git\n+emoji: 🚀 unicode: café"
        mock_diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_pr_response, mock_diff_response]
        
        from version_1 import fetch_pr_diff
        
        result = fetch_pr_diff("owner", "repo", "123", "token")
        assert "🚀" in result
        assert "café" in result

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.get')
    def test_very_large_diff(self, mock_get):
        """Test handling of very large diffs."""
        mock_pr_response = Mock()
        mock_pr_response.json.return_value = {"diff_url": "https://test"}
        mock_pr_response.raise_for_status = Mock()
        
        large_diff = "diff line\n" * 100000  # Very large diff
        mock_diff_response = Mock()
        mock_diff_response.text = large_diff
        mock_diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_pr_response, mock_diff_response]
        
        from version_1 import fetch_pr_diff
        
        result = fetch_pr_diff("owner", "repo", "123", "token")
        assert len(result) >= 1000000  # Changed to >= to handle exact 1000000

    @patch.dict('os.environ', {
        'API_KEY': 'test_groq_key',
        'GITHUB_TOKEN': 'test_token',
        'OWNER': 'owner',
        'REPO': 'repo',
        'PR_NUMBER': '1'
    })
    @patch('requests.post')
    def test_special_characters_in_review(self, mock_post):
        """Test posting review with special characters."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "html_url": "https://test"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        from version_1 import post_review_comment
        
        special_review = "Review with <html> & 'quotes' and \"double quotes\""
        result = post_review_comment("owner", "repo", "123", "token", special_review)
        
        assert result["id"] == 1


# Pytest configuration
@pytest.fixture(autouse=True)
def clean_imports():
    """Clean module imports between tests."""
    yield
    import sys
    if 'version_1' in sys.modules:
        del sys.modules['version_1']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=version_1", "--cov-report=html"])