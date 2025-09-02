import json
import os
from dotenv import load_dotenv
from groq import Groq

# Load API key from .env
load_dotenv()
client = Groq(api_key=os.getenv("API_KEY"))

def generate_pr_and_review(n=20, output_file="train.jsonl"):
    data = []
    for i in range(n):
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
            normalized = [l.replace("**", "").strip() for l in text.splitlines()]

            title = next(l.replace("PR Title:", "").strip() for l in normalized if l.startswith("PR Title:"))
            desc = next(l.replace("PR Description:", "").strip() for l in normalized if l.startswith("PR Description:"))

            # Extract diff block (between ``` ... ```)
            diff_start = text.find("```")
            diff_end = text.find("```", diff_start + 3)
            diff = text[diff_start:diff_end+3] if diff_start != -1 and diff_end != -1 else ""

            review = next(l.replace("Review:", "").strip() for l in normalized if l.startswith("Review:"))

            data.append({
                "prompt": f"PR Title: {title}\nPR Description: {desc}\nCode Diff:\n{diff}\nReview:",
                "completion": " " + review
            })
        except Exception:
            # If parsing fails, still save the raw text
            data.append({
                "prompt": text + "\nReview:",
                "completion": " "  # leave review blank if not parsed
            })

    # Write data to file
    with open(output_file, "w", encoding="utf-8") as f:
        for ex in data:
            f.write(json.dumps(ex) + "\n")

    print(f"✅ Generated {len(data)} samples with code diffs → {output_file}")

if __name__ == "__main__":
    generate_pr_and_review()
