"""
Synthetic PR data generator using Groq LLM.

This script generates synthetic GitHub Pull Request data including titles,
descriptions, code diffs, and reviews for training purposes.
"""

import json
import os
from dotenv import load_dotenv
from groq import Groq

# Load API key from .env
load_dotenv()
client = Groq(api_key=os.getenv("API_KEY"))


def generate_pr_and_review(n=20, output_file="train.jsonl"):
    """
    Generate synthetic PR data with reviews.

    Args:
        n: Number of samples to generate (default: 20)
        output_file: Output JSONL file path (default: "train.jsonl")

    Returns:
        None: Writes data to the specified file
    """
    data = []
    for _ in range(n):
        prompt = """
        Generate a synthetic GitHub Pull Request with:
        1. PR Title
        2. PR Description
        3. Code Diff (use Python code with +/- like git diff format, keep short 5-15 lines)
        4. A short Review comment (1-2 sentences).

        Format strictly as:
        PR Title: <title>
        PR Description: <description>
        Code Diff:
        <diff here>
        Review: <review text>
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400,
        )

        text = response.choices[0].message.content.strip()

        try:
            # Normalize formatting (remove bold **)
            normalized = [
                line.replace("**", "").strip() for line in text.splitlines()
            ]

            title = next(
                line.replace("PR Title:", "").strip()
                for line in normalized
                if line.startswith("PR Title:")
            )
            desc = next(
                line.replace("PR Description:", "").strip()
                for line in normalized
                if line.startswith("PR Description:")
            )

            # Extract diff block (between ``` ... ```)
            diff_start = text.find("```")
            diff_end = text.find("```", diff_start + 3)
            diff = (
                text[diff_start : diff_end + 3]
                if diff_start != -1 and diff_end != -1
                else ""
            )

            review = next(
                line.replace("Review:", "").strip()
                for line in normalized
                if line.startswith("Review:")
            )

            data.append(
                {
                    "prompt": (
                        f"PR Title: {title}\n"
                        f"PR Description: {desc}\n"
                        f"Code Diff:\n{diff}\n"
                        f"Review:"
                    ),
                    "completion": " " + review,
                }
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # If parsing fails, still save the raw text
            data.append(
                {
                    "prompt": text + "\nReview:",
                    "completion": " ",  # leave review blank if not parsed
                }
            )

    # Write data to file
    with open(output_file, "w", encoding="utf-8") as f:
        for ex in data:
            f.write(json.dumps(ex) + "\n")
    print(
        f"✅ Generated {len(data)} samples with code diffs → {output_file}"
    )


if __name__ == "__main__":
    generate_pr_and_review()
