"""
Iterative prompt selector with meta-evaluation for PR reviews.

This module implements a machine learning-based prompt selection system
that learns from review quality scores to optimize PR review generation.
"""

import json
import re
import time
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core import (run_prompt, fetch_pr_diff, save_text_to_file,
                  post_review_comment, llm)
from evaluation import heuristic_metrics, meta_to_score, heuristics_to_score
from prompts import get_prompts
from config import OWNER, REPO, GITHUB_TOKEN
from utils import safe_truncate

# --- MODIFIED: Meta-evaluator prompt template now includes {static} and
# {context} ---
evaluator_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an objective senior software engineer who judges review "
     "quality."),
    ("human",
     "You will evaluate a Pull Request review based on the diff, static "
     "analysis, and retrieved context provided.\n"
     "Judge if the review properly used the static analysis and context.\n"
     "Produce ONLY a JSON object (no extra commentary).\n\n"
     "Fields (1-10 integers): clarity, usefulness, depth, actionability, "
     "positivity.\n"
     "Also include a short `explain` string (1-2 sentences).\n\n"
     "Output JSON (exact format):\n"
     "{{\n"
     '  "clarity": <int 1-10>,\n'
     '  "usefulness": <int 1-10>,\n'
     '  "depth": <int 1-10>,\n'
     '  "actionability": <int 1-10>,\n'
     '  "positivity": <int 1-10>,\n'
     '  "explain": "short explanation"\n'
     "}}\n\n"
     "PR Diff (truncated):\n{diff}\n\n"
     "Static Analysis Results:\n{static}\n\n"
     "Retrieved Context:\n{context}\n\n"
     "Review to evaluate:\n{review}\n")
])


def meta_evaluate(diff: str, review: str, static_output: str, context: str):
    """
    Calls the evaluator LLM chain and returns parsed JSON (dict) and raw
    output. Returns (parsed_dict, raw_text). parsed_dict may contain 'error'
    key on problems.
    """
    chain = evaluator_prompt | llm | StrOutputParser()
    try:
        # Truncate inputs for the evaluator
        truncated_diff = safe_truncate(diff, 4000)
        truncated_review = safe_truncate(review, 4000)
        truncated_static = safe_truncate(static_output, 2000)
        truncated_context = safe_truncate(context, 2000)

        raw = chain.invoke({
            "diff": truncated_diff,
            "review": truncated_review,
            "static": truncated_static,
            "context": truncated_context
        })
    except (RuntimeError, ValueError, ConnectionError) as error:
        return {"error": f"evaluator invoke failed: {error}"}, None

    # parse JSON robustly
    parsed = None
    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {"error": "could not parse JSON", "raw": raw}
        else:
            parsed = {"error": "no JSON in evaluator output", "raw": raw}
    return parsed, raw


class IterativePromptSelector:
    """
    Selects and optimizes prompts for PR review generation using
    machine learning.
    """

    def __init__(self, min_samples_for_training: int = 5):
        self.prompts = get_prompts()
        self.prompt_names = list(self.prompts.keys())
        self.feature_history = []  # list of numpy arrays
        self.prompt_history = []  # list of prompt index ints
        self.score_history = []  # list of floats
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.min_samples_for_training = min_samples_for_training

    def extract_pr_features(self, diff_text: str):
        """Extract features from PR diff text."""
        features = {}
        features['num_lines'] = len(diff_text.splitlines())
        features['num_files'] = len(
            re.findall(r'^diff --git', diff_text, re.MULTILINE)
        )
        features['additions'] = len(
            re.findall(r'^\+', diff_text, re.MULTILINE)
        )
        features['deletions'] = len(
            re.findall(r'^-', diff_text, re.MULTILINE)
        )
        features['net_changes'] = (features['additions'] -
                                    features['deletions'])
        features['has_comments'] = int(bool(
            re.search(r'#.*|//.*|/\*.*?\*/', diff_text, re.DOTALL)
        ))
        features['has_functions'] = int(bool(
            re.search(r'\bdef\s+\w+|\bfunction\b|\bfunc\b', diff_text,
                      re.IGNORECASE)
        ))
        features['has_imports'] = int(bool(
            re.search(r'^\s*import\s|^\s*from\s|#include', diff_text,
                      re.MULTILINE)
        ))
        features['has_test'] = int(bool(
            re.search(r'\btest\b|\bspec\b|\bunittest\b', diff_text,
                      re.IGNORECASE)
        ))
        features['has_docs'] = int(bool(
            re.search(r'\breadme\b|\bdoc\b|\bdocumentation\b', diff_text,
                      re.IGNORECASE)
        ))
        features['has_config'] = int(bool(
            re.search(r'\.json\b|\.yml\b|\.yaml\b|\.xml\b|\.conf\b',
                      diff_text, re.IGNORECASE)
        ))
        features['is_python'] = int(bool(
            re.search(r'\.py\b', diff_text, re.IGNORECASE)
        ))
        features['is_js'] = int(bool(
            re.search(r'\.js\b|\.ts\b', diff_text, re.IGNORECASE)
        ))
        features['is_java'] = int(bool(
            re.search(r'\.java\b', diff_text, re.IGNORECASE)
        ))
        return features

    def features_to_vector(self, features: dict):
        """Convert feature dict to numpy array."""
        order = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        return np.array([features.get(k, 0) for k in order], dtype=float)

    def select_best_prompt(self, features_vector: np.ndarray):
        """Select the best prompt based on learned patterns."""
        # If not enough data, do round-robin selection
        if (not self.is_trained or
                len(self.feature_history) < self.min_samples_for_training):
            return self.prompt_names[
                len(self.feature_history) % len(self.prompt_names)
            ]

        try:
            # For each prompt, append prompt index as an extra feature and
            # predict score
            features_matrix = np.tile(
                features_vector, (len(self.prompt_names), 1)
            )
            prompt_indices = np.arange(len(self.prompt_names)).reshape(-1, 1)
            x_with_prompt = np.hstack([features_matrix, prompt_indices])
            x_scaled = self.scaler.transform(x_with_prompt)
            preds = self.model.predict(x_scaled)
            best_idx = int(np.argmax(preds))
            return self.prompt_names[best_idx]
        except (ValueError, AttributeError):
            # fallback
            return self.prompt_names[0]

    def update_model(self, features_vector: np.ndarray, prompt_name: str,
                     score: float):
        """Update the model with new training data."""
        self.feature_history.append(features_vector)
        prompt_idx = self.prompt_names.index(prompt_name)
        self.prompt_history.append(prompt_idx)
        self.score_history.append(score)

        if len(self.feature_history) >= self.min_samples_for_training:
            try:
                features_matrix = np.array(self.feature_history)
                prompt_indices = np.array(self.prompt_history).reshape(-1, 1)
                x_combined = np.hstack([features_matrix, prompt_indices])
                target_values = np.array(self.score_history)
                # Fit scaler and model
                self.scaler.fit(x_combined)
                x_scaled = self.scaler.transform(x_combined)
                self.model.fit(x_scaled, target_values)
                self.is_trained = True
            except (ValueError, AttributeError) as error:
                print(f"Model training failed: {error}")
                self.is_trained = False

    def generate_review(self, diff_text: str, selected_prompt: str,
                        diff_truncate: int = 4000):
        """Generate a review using the selected prompt."""
        prompt = self.prompts[selected_prompt]
        start = time.time()
        # run_prompt now returns review, static_output, and context
        review, static_output, context = run_prompt(
            prompt, diff_text, diff_truncate=diff_truncate
        )
        elapsed = time.time() - start
        return review, static_output, elapsed, context

    def evaluate_review(self, diff_text: str, review_text: str,
                        static_output: str, context: str):
        """Evaluate the quality of a generated review."""
        heur = heuristic_metrics(review_text)
        meta_parsed, _ = meta_evaluate(
            diff_text, review_text, static_output=static_output,
            context=context
        )

        final_score, meta_score, heur_score = None, None, None
        if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
            meta_score = meta_to_score(meta_parsed)
            heur_score = heuristics_to_score(heur)
            final_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
        else:
            heur_score = heuristics_to_score(heur)
            final_score = round(heur_score, 2)
        return final_score, heur, meta_parsed

    def save_results(self, pr_number: int, features: dict, prompt_name: str,
                     review: str, score: float, heur: dict, meta_parsed: dict,
                     static_output: str, context: str):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"iterative_results_pr{pr_number}_{timestamp}.json"

        # Add context summary to payload
        static_summary = (static_output[:100] + "..." if
                          len(static_output) > 100 else static_output)
        context_summary = (context[:100] + "..." if len(context) > 100
                           else context)

        payload = {
            "timestamp": timestamp,
            "pr_number": pr_number,
            "selected_prompt": prompt_name,
            "review_score": score,
            "features": features,
            "heuristics": heur,
            "meta_evaluation": meta_parsed,
            "static_output_summary": static_summary,
            "retrieved_context_summary": context_summary,
            "training_data_size": len(self.feature_history),
            "model_trained": self.is_trained
        }

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        # also save the review text
        review_fname = (f"review_pr{pr_number}_"
                        f"{prompt_name.replace('/', '_').replace(' ', '_')}"
                        f".md")
        # Include static analysis AND context in the individual review file
        content = (
            f"# Review (prompt={prompt_name})\n\n{review}\n\n"
            f"---\n## Static Analysis Output:\n{static_output}\n\n"
            f"---\n## Retrieved Context:\n{context}\n"
        )
        save_text_to_file(review_fname, content)

    def save_state(self, filename: str = "selector_state.json"):
        """Save the selector state to a JSON file."""
        state = {
            "feature_history": [f.tolist() for f in self.feature_history],
            "prompt_history": self.prompt_history,
            "score_history": self.score_history,
            "is_trained": self.is_trained,
            "scaler_mean": (self.scaler.mean_.tolist() if self.is_trained
                            else None),
            "scaler_scale": (self.scaler.scale_.tolist() if self.is_trained
                             else None)
        }
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(state, file)

    def load_state(self, filename: str = "selector_state.json"):
        """Load the selector state from a JSON file."""
        try:
            with open(filename, "r", encoding="utf-8") as file:
                state = json.load(file)
            self.feature_history = [
                np.array(f) for f in state.get("feature_history", [])
            ]
            self.prompt_history = state.get("prompt_history", [])
            self.score_history = state.get("score_history", [])
            self.is_trained = state.get("is_trained", False)
            if self.is_trained and state.get("scaler_mean") is not None:
                self.scaler.mean_ = np.array(state["scaler_mean"])
                self.scaler.scale_ = np.array(state["scaler_scale"])
                self.scaler.n_features_in_ = len(state["scaler_mean"])
                self.scaler.var_ = self.scaler.scale_ ** 2
            print(f"Loaded selector state: {len(self.feature_history)} "
                  f"samples, trained={self.is_trained}")
        except FileNotFoundError:
            print("No selector state found; starting fresh.")
        except (json.JSONDecodeError, KeyError, ValueError) as error:
            print(f"Failed to load state: {error}; starting fresh.")
            self.feature_history = []
            self.prompt_history = []
            self.score_history = []
            self.is_trained = False


def process_pr_with_selector(selector: IterativePromptSelector,
                              pr_number: int, owner=OWNER, repo=REPO,
                              token=GITHUB_TOKEN,
                              post_to_github: bool = True):
    """Process a PR using the selector and persist outputs."""
    print(f"Processing PR #{pr_number}...")
    diff_text = fetch_pr_diff(owner, repo, pr_number, token)
    features = selector.extract_pr_features(diff_text)
    features_vector = selector.features_to_vector(features)
    chosen = selector.select_best_prompt(features_vector)
    print(f"Selected prompt: {chosen}")

    # Get static_output, elapsed, and context
    review, static_output, elapsed, context = selector.generate_review(
        diff_text, chosen
    )

    print(f"Review generated in {elapsed:.2f}s")

    # Pass context to evaluate_review
    score, heur, meta_parsed = selector.evaluate_review(
        diff_text, review, static_output, context
    )

    print(f"Score: {score}/10")
    selector.update_model(features_vector, chosen, score)

    # Pass static_output and context to save_results
    selector.save_results(
        pr_number, features, chosen, review, score, heur, meta_parsed,
        static_output, context
    )

    if post_to_github:
        print(f"Posting review to GitHub PR #{pr_number}...")
        try:
            github_body = (
                f"**AI-Powered Review** (Prompt: `{chosen}` | "
                f"Score: **{score}/10**)\n\n"
                f"---\n\n"
                f"{review}"
            )

            post_review_comment(owner, repo, pr_number, github_body, token)
            print("Successfully posted comment to GitHub.")
        except (ConnectionError, TimeoutError) as error:
            print(f"FAILED to post comment to GitHub: {error}")

    return {
        "pr_number": pr_number,
        "chosen_prompt": chosen,
        "review": review,
        "score": score,
        "features": features
    }
