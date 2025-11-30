import pytest
import json
from unittest.mock import patch, MagicMock
import requests


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

    @patch("ollama_code.load_dotenv")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_github_token_loads_successfully(self, mock_load_dotenv):
        """Test that GITHUB_TOKEN is loaded from environment"""
        import os
        from dotenv import load_dotenv

        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")

        assert token == "test_token"
        mock_load_dotenv.assert_called_once()

    @patch("ollama_code.load_dotenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_github_token_raises_error(self, mock_load_dotenv):
        """Test that missing GITHUB_TOKEN raises ValueError"""
        import os

        with pytest.raises(ValueError, match="GITHUB_TOKEN not found"):
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise ValueError("❌ GITHUB_TOKEN not found. Check your .env file.")


# Test cases for GitHub API interaction
class TestGitHubAPIFetching:
    """Test suite for GitHub API PR diff fetching"""

    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_fetch_pr_diff_success(self, mock_get, sample_pr_diff):
        """Test successful PR diff fetching"""
        mock_response = MagicMock()
        mock_response.text = sample_pr_diff
        mock_get.return_value = mock_response

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 2
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        headers = {
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3.diff",
        }

        response = requests.get(url, headers=headers)
        diff = response.text

        assert diff == sample_pr_diff
        mock_get.assert_called_once_with(url, headers=headers)

    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_fetch_pr_diff_with_correct_headers(self, mock_get):
        """Test that correct headers are sent to GitHub API"""
        mock_response = MagicMock()
        mock_response.text = "diff content"
        mock_get.return_value = mock_response

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 2
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        headers = {
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3.diff",
        }

        requests.get(url, headers=headers)

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "token test_token"
        assert call_args[1]["headers"]["Accept"] == "application/vnd.github.v3.diff"

    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_fetch_pr_diff_network_error(self, mock_get):
        """Test handling of network errors when fetching PR diff"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 2
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get(
                url,
                headers={
                    "Authorization": "token test_token",
                    "Accept": "application/vnd.github.v3.diff",
                },
            )

    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_fetch_pr_diff_401_unauthorized(self, mock_get):
        """Test handling of 401 unauthorized response"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_get.return_value = mock_response

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 2
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        response = requests.get(
            url,
            headers={
                "Authorization": "token test_token",
                "Accept": "application/vnd.github.v3.diff",
            },
        )

        assert response.status_code == 401
        with pytest.raises(requests.exceptions.HTTPError):
            response.raise_for_status()

    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_fetch_pr_diff_404_not_found(self, mock_get):
        """Test handling of 404 not found response"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 9999
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

        response = requests.get(
            url,
            headers={
                "Authorization": "token test_token",
                "Accept": "application/vnd.github.v3.diff",
            },
        )

        assert response.status_code == 404


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
        mock_post.return_value = mock_response

        prompt = f"""
You are a strict GitHub code reviewer. Review the following pull request diff.

Return your feedback **in Markdown format** with the following sections:

## Summary
- Briefly explain what the code does.

## Strengths
- List positive aspects in bullet points.

## Issues / Suggestions
- List code issues, potential bugs, or improvements.

## Final Verdict
- Give a short overall statement (e.g., LGTM ✅ or Needs Work ❌).

Here is the diff:
{sample_pr_diff}
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": prompt},
            stream=True,
        )

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["model"] == "codellama"
        assert "GitHub code reviewer" in call_args[1]["json"]["prompt"]
        assert call_args[1]["stream"] is True

    @patch("requests.post")
    def test_ollama_streaming_response_parsing(self, mock_post, sample_ollama_response):
        """Test parsing of streaming response from Ollama"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = sample_ollama_response
        mock_post.return_value = mock_response

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": "test"},
            stream=True,
        )

        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue

        assert "## Summary" in review_text
        assert "## Strengths" in review_text
        assert "## Issues / Suggestions" in review_text
        assert "## Final Verdict" in review_text
        assert "Needs Work" in review_text


    @patch("requests.post")
    def test_ollama_malformed_json_handling(self, mock_post):
        """Test handling of malformed JSON in streaming response"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "Valid line"}',
            b'{malformed json}',
            b'{"response": "Another valid line"}',
        ]
        mock_post.return_value = mock_response

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": "test"},
            stream=True,
        )

        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue

        assert "Valid line" in review_text
        assert "Another valid line" in review_text
        assert "malformed" not in review_text


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
        mock_post.return_value = mock_response

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": "test"},
            stream=True,
        )

        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue

        assert review_text == "Line 1Line 2"


    @patch("requests.post")
    def test_ollama_connection_error(self, mock_post):
        """Test handling of connection error to Ollama"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Cannot connect to Ollama")

        with pytest.raises(requests.exceptions.ConnectionError):
            requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "codellama", "prompt": "test"},
                stream=True,
            )


    @patch("requests.post")
    def test_ollama_timeout_error(self, mock_post):
        """Test handling of timeout when calling Ollama"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "codellama", "prompt": "test"},
                stream=True,
            )


    @patch("requests.post")
    def test_ollama_response_without_response_key(self, mock_post):
        """Test handling of response objects without 'response' key"""
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"model": "codellama"}',
            b'{"done": false}',
            b'{"response": "Actual content"}',
        ]
        mock_post.return_value = mock_response

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": "test"},
            stream=True,
        )

        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue

        assert review_text == "Actual content"


# Integration test
class TestEndToEndIntegration:
    """Integration tests for the complete workflow"""

    @patch("requests.post")
    @patch("requests.get")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_complete_workflow(self, mock_get, mock_post, sample_pr_diff, sample_ollama_response):
        """Test complete workflow from fetching PR to generating review"""
        github_response = MagicMock()
        github_response.text = sample_pr_diff
        mock_get.return_value = github_response

        ollama_response = MagicMock()
        ollama_response.iter_lines.return_value = sample_ollama_response
        mock_post.return_value = ollama_response

        owner = "prince-chovatiya01"
        repo = "nutrition-diet-planner"
        pr_number = 2

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Authorization": "token test_token", "Accept": "application/vnd.github.v3.diff"}
        diff = requests.get(url, headers=headers).text

        prompt = f"""
You are a strict GitHub code reviewer. Review the following pull request diff.

Return your feedback **in Markdown format** with the following sections:

## Summary
- Briefly explain what the code does.

## Strengths
- List positive aspects in bullet points.

## Issues / Suggestions
- List code issues, potential bugs, or improvements.

## Final Verdict
- Give a short overall statement (e.g., LGTM ✅ or Needs Work ❌).

Here is the diff:
{diff}
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "codellama", "prompt": prompt},
            stream=True,
        )

        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue

        assert diff == sample_pr_diff
        assert "## Summary" in review_text
        assert "## Final Verdict" in review_text
        mock_get.assert_called_once()
        mock_post.assert_called_once()


# Test for prompt generation
class TestPromptGeneration:
    """Test suite for prompt formatting"""

    def test_prompt_contains_required_sections(self, sample_pr_diff):
        """Test that generated prompt contains all required sections"""
        prompt = f"""
You are a strict GitHub code reviewer. Review the following pull request diff.

Return your feedback **in Markdown format** with the following sections:

## Summary
- Briefly explain what the code does.

## Strengths
- List positive aspects in bullet points.

## Issues / Suggestions
- List code issues, potential bugs, or improvements.

## Final Verdict
- Give a short overall statement (e.g., LGTM ✅ or Needs Work ❌).

Here is the diff:
{sample_pr_diff}
"""

        assert "## Summary" in prompt
        assert "## Strengths" in prompt
        assert "## Issues / Suggestions" in prompt
        assert "## Final Verdict" in prompt
        assert sample_pr_diff in prompt
        assert "GitHub code reviewer" in prompt

    def test_prompt_includes_diff_content(self):
        """Test that diff content is properly included in prompt"""
        test_diff = "diff --git a/test.py b/test.py\n+added line"
        prompt = f"""
You are a strict GitHub code reviewer. Review the following pull request diff.

Return your feedback **in Markdown format** with the following sections:

## Summary
- Briefly explain what the code does.

## Strengths
- List positive aspects in bullet points.

## Issues / Suggestions
- List code issues, potential bugs, or improvements.

## Final Verdict
- Give a short overall statement (e.g., LGTM ✅ or Needs Work ❌).

Here is the diff:
{test_diff}
"""

        assert test_diff in prompt
        assert "diff --git" in prompt
        assert "+added line" in prompt
