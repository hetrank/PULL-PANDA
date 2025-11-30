"""
Ollama-powered GitHub PR reviewer.

This script fetches PR diffs from GitHub and uses a local Ollama instance
to generate AI-powered code reviews.
"""

import os
import json
import sys

import requests
from dotenv import load_dotenv


def load_github_token():
    """Load and validate GitHub token from environment."""
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("❌ GITHUB_TOKEN not found. Check your .env file.")
    return token


def fetch_pr_diff(owner, repo, pr_number, token):
    """
    Fetch PR diff from GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        token: GitHub authentication token
        
    Returns:
        str: PR diff content
        
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError(f"❌ Authentication failed. Check your GITHUB_TOKEN.") from e
        elif response.status_code == 404:
            raise ValueError(f"❌ PR #{pr_number} not found in {owner}/{repo}.") from e
        raise
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"❌ Failed to connect to GitHub API.") from e
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"❌ GitHub API request timed out.") from e


def generate_review_prompt(diff):
    """
    Generate prompt for Ollama code review.
    
    Args:
        diff: PR diff content
        
    Returns:
        str: Formatted prompt
    """
    return f"""
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


def get_ollama_review(prompt, model="codellama", ollama_url="http://localhost:11434/api/generate"):
    """
    Get code review from Ollama API.
    
    Args:
        prompt: Review prompt
        model: Ollama model to use
        ollama_url: Ollama API endpoint
        
    Returns:
        str: Generated review text
        
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    try:
        response = requests.post(
            ollama_url,
            json={"model": model, "prompt": prompt},
            stream=True,
            timeout=30,
        )
        response.raise_for_status()
        
        review_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    obj = json.loads(line.decode("utf-8"))
                    if "response" in obj:
                        review_text += obj["response"]
                except json.JSONDecodeError:
                    continue
        
        return review_text.strip()
        
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"❌ Failed to connect to Ollama. Is it running?") from e
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"❌ Ollama request timed out.") from e


def review_pr(owner, repo, pr_number, token=None, model="codellama"):
    """
    Complete workflow to review a PR.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        token: GitHub token (if None, loads from env)
        model: Ollama model to use
        
    Returns:
        dict: Contains 'diff' and 'review' keys
    """
    if token is None:
        token = load_github_token()
    
    print(f"📥 Fetching PR #{pr_number} from {owner}/{repo}...")
    diff = fetch_pr_diff(owner, repo, pr_number, token)
    print(f"✅ Fetched {len(diff)} characters of diff")
    
    print(f"\n🤖 Generating review with {model}...")
    prompt = generate_review_prompt(diff)
    review = get_ollama_review(prompt, model=model)
    print("✅ Review generated")
    
    return {
        "diff": diff,
        "review": review
    }


def main():
    """Main entry point for CLI usage."""
    try:
        # Configuration
        OWNER = "prince-chovatiya01"
        REPO = "nutrition-diet-planner"
        PR_NUMBER = 2
        
        # Run review
        result = review_pr(OWNER, REPO, PR_NUMBER)
        
        # Display results
        print("\n" + "="*60)
        print("=== PR DIFF (preview) ===")
        print("="*60)
        print(result["diff"][:500], "...")
        
        print("\n" + "="*60)
        print("=== AI REVIEW ===")
        print("="*60)
        print(result["review"])
        
        return 0
        
    except (ValueError, ConnectionError, TimeoutError) as e:
        print(f"\n{str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())