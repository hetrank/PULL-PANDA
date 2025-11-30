import pytest
import json
from unittest.mock import patch, MagicMock, call
import requests
import sys
from io import StringIO

import ollama_code_refactored as ollama_code


# Test data fixtures
@pytest.fixture
def mock_env_vars():
    """Fixture to mock environment variables"""
    return {"GITHUB_TOKEN": "test_token_12345"}


@pytest.fixture
def sample_pr_diff():
    """Fixture with sample PR diff content"""
    return """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
+import logging
 def calculate(a, b):
-    return a + b
+    return a * b
"""


@pytest.fixture
def sample_ollama_response():
    """Fixture with sample Ollama streaming response"""
    return [
        b'{"response": "## Summary\\n"}',
        b'{"response": "- Code changes multiplication\\n"}',
        b'{"response": "## Strengths\\n"}',
        b'{"response": "- Clean implementation\\n"}',
        b'{"response": "## Issues / Suggestions\\n"}',
        b'{"response": "- Add unit tests\\n"}',
        b'{"response": "## Final Verdict\\n"}',
        b'{"response": "Needs Work \\u274c"}',
    ]


# Test cases for environment variable loading
class TestEnvironmentVariables:
    """Test suite for environment variable handling"""

    @patch("ollama_code_refactored.load_dotenv")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_github_token_loads_successfully(self, mock_load_dotenv):
        """Test that GITHUB_TOKEN is loaded from environment"""
        token = ollama_code.load_github_token()
        
        assert token == "test_token"
        mock_load_dotenv.assert_called_once()

    @patch("ollama_code_refactored.load_dotenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_github_token_raises_error(self, mock_load_dotenv):
        """Test that missing GITHUB_TOKEN raises ValueError"""
        with pytest.raises(ValueError, match="GITHUB_TOKEN not found"):
            ollama_code.load_github_token()


# Test cases for GitHub API interaction
class TestGitHubAPIFetching:
    """Test suite for GitHub API PR diff fetching"""

    @patch("requests.get")
    def test_fetch_pr_diff_success(self, mock_get, sample_pr_diff):
        """Test successful PR diff fetching"""
        mock_response = MagicMock()
        mock_response.text = sample_pr_diff
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        diff = ollama_code.fetch_pr_diff(
            "prince-chovatiya01", 
            "nutrition-diet-planner", 
            2, 
            "test_token"
        )

        assert diff == sample_pr_diff
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert "token test_token" in call_args[1]["headers"]["Authorization"]

    @patch("requests.get")
    def test_fetch_pr_diff_with_correct_headers(self, mock_get):
        """Test that correct headers are sent to GitHub API"""
        mock_response = MagicMock()
        mock_response.text = "diff content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        ollama_code.fetch_pr_diff(
            "prince-chovatiya01",
            "nutrition-diet-planner",
            2,
            "test_token"
        )

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "token test_token"
        assert call_args[1]["headers"]["Accept"] == "application/vnd.github.v3.diff"

    @patch("requests.get")
    def test_fetch_pr_diff_network_error(self, mock_get):
        """Test handling of network errors when fetching PR diff"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with pytest.raises(ConnectionError, match="Failed to connect to GitHub API"):
            ollama_code.fetch_pr_diff(
                "prince-chovatiya01",
                "nutrition-diet-planner",
                2,
                "test_token"
            )

    @patch("requests.get")
    def test_fetch_pr_diff_401_unauthorized(self, mock_get):
        """Test handling of 401 unauthorized response"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Authentication failed"):
            ollama_code.fetch_pr_diff(
                "prince-chovatiya01",
                "nutrition-diet-planner",
                2,
                "test_token"
            )

    @patch("requests.get")
    def test_fetch_pr_diff_404_not_found(self, mock_get):
        """Test handling of 404 not found response"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="PR #9999 not found"):
            ollama_code.fetch_pr_diff(
                "prince-chovatiya01",
                "nutrition-diet-planner",
                9999,
                "test_token"
            )

    @patch("requests.get")
    def test_fetch_pr_diff_timeout(self, mock_get):
        """Test handling of timeout errors"""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        with pytest.raises(TimeoutError, match="timed out"):
            ollama_code.fetch_pr_diff(
                "prince-chovatiya01",
                "nutrition-diet-planner",
                2,
                "test_token"
            )

    @patch("requests.get")
    def test_fetch_pr_diff_other_http_error(self, mock_get):
        """Test handling of other HTTP errors (500, etc)"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            ollama_code.fetch_pr_diff(
                "prince-chovatiya01",
                "nutrition-diet-planner",
                2,
                "test_token"
            )


# Test cases for Ollama API interaction
class TestOllamaAPIInteraction:
    """Test suite for Ollama API code review generation"""

    @patch("requests.post")
    def test_ollama_request_with_correct_payload(self, mock_post, sample_pr_diff):
        """Test that Ollama API is called with correct payload"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "## Summary\\n"}',
            b'{"response": "Code looks good"}',
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        prompt = ollama_code.generate_review_prompt(sample_pr_diff)
        review = ollama_code.get_ollama_review(prompt)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["model"] == "codellama"
        assert "GitHub code reviewer" in call_args[1]["json"]["prompt"]
        assert call_args[1]["stream"] is True
        assert "## Summary" in review

    @patch("requests.post")
    def test_ollama_streaming_response_parsing(self, mock_post, sample_ollama_response):
        """Test parsing of streaming response from Ollama"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = sample_ollama_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        review = ollama_code.get_ollama_review("test prompt")

        assert "## Summary" in review
        assert "## Strengths" in review
        assert "## Issues / Suggestions" in review
        assert "## Final Verdict" in review
        assert "Needs Work" in review

    @patch("requests.post")
    def test_ollama_malformed_json_handling(self, mock_post):
        """Test handling of malformed JSON in streaming response"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "Valid line"}',
            b'{malformed json}',
            b'{"response": "Another valid line"}',
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        review = ollama_code.get_ollama_review("test prompt")

        assert "Valid line" in review
        assert "Another valid line" in review
        assert "malformed" not in review

    @patch("requests.post")
    def test_ollama_empty_response_handling(self, mock_post):
        """Test handling of empty lines in streaming response"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "Line 1"}',
            b"",
            b'{"response": "Line 2"}',
            b"",
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        review = ollama_code.get_ollama_review("test prompt")

        assert review == "Line 1Line 2"

    @patch("requests.post")
    def test_ollama_connection_error(self, mock_post):
        """Test handling of connection error to Ollama"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Cannot connect")

        with pytest.raises(ConnectionError, match="Failed to connect to Ollama"):
            ollama_code.get_ollama_review("test prompt")

    @patch("requests.post")
    def test_ollama_timeout_error(self, mock_post):
        """Test handling of timeout when calling Ollama"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(TimeoutError, match="Ollama request timed out"):
            ollama_code.get_ollama_review("test prompt")

    @patch("requests.post")
    def test_ollama_response_without_response_key(self, mock_post):
        """Test handling of response objects without 'response' key"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"model": "codellama"}',
            b'{"done": false}',
            b'{"response": "Actual content"}',
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        review = ollama_code.get_ollama_review("test prompt")

        assert review == "Actual content"

    @patch("requests.post")
    def test_ollama_custom_model(self, mock_post):
        """Test using custom Ollama model"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"response": "test"}']
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        ollama_code.get_ollama_review("test", model="llama2")

        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "llama2"

    @patch("requests.post")
    def test_ollama_custom_url(self, mock_post):
        """Test using custom Ollama URL"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"response": "test"}']
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        ollama_code.get_ollama_review("test", ollama_url="http://custom:11434/api/generate")

        call_args = mock_post.call_args
        assert call_args[0][0] == "http://custom:11434/api/generate"

    @patch("requests.post")
    def test_ollama_http_error(self, mock_post):
        """Test handling of HTTP errors from Ollama"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            ollama_code.get_ollama_review("test")


# Test cases for prompt generation
class TestPromptGeneration:
    """Test suite for prompt formatting"""

    def test_prompt_contains_required_sections(self, sample_pr_diff):
        """Test that generated prompt contains all required sections"""
        prompt = ollama_code.generate_review_prompt(sample_pr_diff)

        assert "## Summary" in prompt
        assert "## Strengths" in prompt
        assert "## Issues / Suggestions" in prompt
        assert "## Final Verdict" in prompt
        assert sample_pr_diff in prompt
        assert "GitHub code reviewer" in prompt

    def test_prompt_includes_diff_content(self):
        """Test that diff content is properly included in prompt"""
        test_diff = "diff --git a/test.py b/test.py\n+added line"
        prompt = ollama_code.generate_review_prompt(test_diff)

        assert test_diff in prompt
        assert "diff --git" in prompt
        assert "+added line" in prompt

    def test_prompt_with_empty_diff(self):
        """Test prompt generation with empty diff"""
        prompt = ollama_code.generate_review_prompt("")
        
        assert "## Summary" in prompt
        assert "Here is the diff:" in prompt

    def test_prompt_with_special_characters(self):
        """Test prompt generation with special characters in diff"""
        special_diff = "diff --git\n+line with 'quotes' and \"double quotes\"\n+line with $pecial ch@rs"
        prompt = ollama_code.generate_review_prompt(special_diff)
        
        assert special_diff in prompt
        assert "'quotes'" in prompt
        assert "$pecial" in prompt


# Integration test - review_pr function
class TestReviewPRFunction:
    """Test suite for review_pr function"""

    @patch("ollama_code_refactored.get_ollama_review")
    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("ollama_code_refactored.load_github_token")
    @patch("builtins.print")
    def test_review_pr_success(self, mock_print, mock_token, mock_fetch, mock_ollama, sample_pr_diff):
        """Test successful PR review workflow"""
        mock_token.return_value = "test_token"
        mock_fetch.return_value = sample_pr_diff
        mock_ollama.return_value = "## Summary\nLooks good"

        result = ollama_code.review_pr("owner", "repo", 1)

        assert result["diff"] == sample_pr_diff
        assert result["review"] == "## Summary\nLooks good"
        mock_fetch.assert_called_once_with("owner", "repo", 1, "test_token")
        mock_ollama.assert_called_once()
        
        # Check that print statements were called
        assert mock_print.call_count >= 3  # Should print fetching, fetched, generating, generated

    @patch("ollama_code_refactored.get_ollama_review")
    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("builtins.print")
    def test_review_pr_with_provided_token(self, mock_print, mock_fetch, mock_ollama, sample_pr_diff):
        """Test review_pr with explicitly provided token"""
        mock_fetch.return_value = sample_pr_diff
        mock_ollama.return_value = "Review text"

        result = ollama_code.review_pr("owner", "repo", 1, token="explicit_token")

        assert result["diff"] == sample_pr_diff
        mock_fetch.assert_called_once_with("owner", "repo", 1, "explicit_token")

    @patch("ollama_code_refactored.get_ollama_review")
    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("builtins.print")
    def test_review_pr_with_custom_model(self, mock_print, mock_fetch, mock_ollama, sample_pr_diff):
        """Test review_pr with custom model"""
        mock_fetch.return_value = sample_pr_diff
        mock_ollama.return_value = "Review"

        ollama_code.review_pr("owner", "repo", 1, token="token", model="llama2")

        call_args = mock_ollama.call_args
        assert call_args[1]["model"] == "llama2"

    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("ollama_code_refactored.load_github_token")
    def test_review_pr_fetch_failure(self, mock_token, mock_fetch):
        """Test review_pr when fetch fails"""
        mock_token.return_value = "test_token"
        mock_fetch.side_effect = ValueError("PR not found")

        with pytest.raises(ValueError, match="PR not found"):
            ollama_code.review_pr("owner", "repo", 1)

    @patch("ollama_code_refactored.get_ollama_review")
    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("ollama_code_refactored.load_github_token")
    def test_review_pr_ollama_failure(self, mock_token, mock_fetch, mock_ollama):
        """Test review_pr when Ollama fails"""
        mock_token.return_value = "test_token"
        mock_fetch.return_value = "diff"
        mock_ollama.side_effect = ConnectionError("Ollama not running")

        with pytest.raises(ConnectionError, match="Ollama not running"):
            ollama_code.review_pr("owner", "repo", 1)

    @patch("ollama_code_refactored.get_ollama_review")
    @patch("ollama_code_refactored.fetch_pr_diff")
    @patch("ollama_code_refactored.load_github_token")
    @patch("builtins.print")
    def test_review_pr_prints_progress(self, mock_print, mock_token, mock_fetch, mock_ollama):
        """Test that review_pr prints progress messages"""
        mock_token.return_value = "token"
        mock_fetch.return_value = "diff content"
        mock_ollama.return_value = "review"

        ollama_code.review_pr("owner", "repo", 1)

        # Verify progress messages
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Fetching PR" in str(call) for call in print_calls)
        assert any("Fetched" in str(call) for call in print_calls)
        assert any("Generating review" in str(call) for call in print_calls)
        assert any("Review generated" in str(call) for call in print_calls)


# Test main function
class TestMainFunction:
    """Test suite for main CLI function"""

    @patch("ollama_code_refactored.review_pr")
    @patch("builtins.print")
    def test_main_success(self, mock_print, mock_review):
        """Test successful main execution"""
        mock_review.return_value = {
            "diff": "diff content here that is longer than 500 chars " + "x" * 500,
            "review": "## Summary\nLooks good"
        }

        exit_code = ollama_code.main()

        assert exit_code == 0
        # Check that output contains expected sections
        print_calls = [str(call) for call in mock_print.call_args_list]
        output_str = " ".join(print_calls)
        assert "PR DIFF" in output_str or any("PR DIFF" in str(call) for call in print_calls)

    @patch("ollama_code_refactored.review_pr")
    def test_main_value_error(self, mock_review, capsys):
        """Test main with ValueError"""
        mock_review.side_effect = ValueError("Token not found")

        exit_code = ollama_code.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Token not found" in captured.err

    @patch("ollama_code_refactored.review_pr")
    def test_main_connection_error(self, mock_review, capsys):
        """Test main with ConnectionError"""
        mock_review.side_effect = ConnectionError("Cannot connect")

        exit_code = ollama_code.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Cannot connect" in captured.err

    @patch("ollama_code_refactored.review_pr")
    def test_main_timeout_error(self, mock_review, capsys):
        """Test main with TimeoutError"""
        mock_review.side_effect = TimeoutError("Request timed out")

        exit_code = ollama_code.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "timed out" in captured.err

    @patch("ollama_code_refactored.review_pr")
    def test_main_unexpected_error(self, mock_review, capsys):
        """Test main with unexpected error"""
        mock_review.side_effect = RuntimeError("Unexpected problem")

        exit_code = ollama_code.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err
        assert "Unexpected problem" in captured.err

    @patch("ollama_code_refactored.review_pr")
    def test_main_uses_correct_config(self, mock_review):
        """Test that main uses correct hardcoded configuration"""
        mock_review.return_value = {"diff": "d", "review": "r"}

        ollama_code.main()

        mock_review.assert_called_once_with(
            "prince-chovatiya01",
            "nutrition-diet-planner",
            2
        )

    @patch("ollama_code_refactored.review_pr")
    @patch("builtins.print")
    def test_main_displays_full_output(self, mock_print, mock_review):
        """Test that main displays all output sections"""
        mock_review.return_value = {
            "diff": "test diff content",
            "review": "test review content"
        }

        exit_code = ollama_code.main()

        assert exit_code == 0
        print_calls = [str(call) for call in mock_print.call_args_list]
        output_str = " ".join(print_calls)
        
        # Check for section headers
        assert any("PR DIFF" in str(call) for call in print_calls)
        assert any("AI REVIEW" in str(call) for call in print_calls)