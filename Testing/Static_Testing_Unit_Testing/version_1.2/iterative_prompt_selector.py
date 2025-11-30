"""
Iterative prompt selector for PR reviews.

Implements an iterative detection and estimation system for prompt selection.
Uses PR features to predict the best prompt, reducing API calls from 7 to 1.
Learns from each PR review to improve future predictions.
"""

import json
import re
import time
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from reviewer import fetch_pr_diff, llm, parser
from config import OWNER, REPO, PR_NUMBER, GITHUB_TOKEN
from prompts_v2 import get_prompts
from accuracy_checker import heuristic_metrics, meta_evaluate


class IterativePromptSelector:
    """Machine learning-based prompt selector that learns from PR reviews."""

    def __init__(self):
        self.prompts = get_prompts()
        self.prompt_names = list(self.prompts.keys())
        self.feature_history = []
        self.prompt_history = []
        self.score_history = []
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.min_samples_for_training = 5

    def extract_pr_features(self, diff_text):
        """Extract features from PR diff for model prediction."""
        features = {}

        # Basic size features
        features['num_lines'] = len(diff_text.split('\n'))
        features['num_files'] = len(
            re.findall(r'^diff --git', diff_text, re.MULTILINE)
        )
        features['additions'] = len(
            re.findall(r'^\+', diff_text, re.MULTILINE)
        )
        features['deletions'] = len(
            re.findall(r'^-', diff_text, re.MULTILINE)
        )
        features['net_changes'] = features['additions'] - features['deletions']

        # Code complexity features
        features['has_comments'] = int(bool(
            re.search(r'#.*|//.*|/\*.*?\*/', diff_text, re.DOTALL)
        ))
        features['has_functions'] = int(bool(
            re.search(r'def\s+\w+|\bfunction\b|\bfunc\b',
                      diff_text, re.IGNORECASE)
        ))
        features['has_imports'] = int(bool(
            re.search(r'^import\s|^from\s|^#include', diff_text, re.MULTILINE)
        ))

        # Content type features
        features['has_test'] = int(bool(
            re.search(r'test|spec|unittest', diff_text, re.IGNORECASE)
        ))
        features['has_docs'] = int(bool(
            re.search(r'readme|doc|comment|documentation',
                      diff_text, re.IGNORECASE)
        ))
        features['has_config'] = int(bool(
            re.search(r'\.json$|\.yml$|\.yaml$|\.xml$|\.conf',
                      diff_text, re.IGNORECASE)
        ))

        # Language detection (simplified)
        features['is_python'] = int(bool(
            re.search(r'\.py$', diff_text, re.IGNORECASE)
        ))
        features['is_js'] = int(bool(
            re.search(r'\.js$|\.ts$', diff_text, re.IGNORECASE)
        ))
        features['is_java'] = int(bool(
            re.search(r'\.java$', diff_text, re.IGNORECASE)
        ))

        return features

    def features_to_vector(self, features):
        """Convert features dict to numerical vector."""
        feature_order = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        return np.array([features.get(key, 0) for key in feature_order])

    def select_best_prompt(self, features_vector):
        """Select the best prompt based on current model prediction."""
        
        # FIX: Check for empty/malformed features_vector before proceeding
        # The 'or not features_vector.size' check ensures the array is not empty.
        if (not self.is_trained or
            len(self.feature_history) < self.min_samples_for_training or
            not features_vector.size):  # <-- ADDED CHECK
            
            # Not enough data yet OR invalid input vector, use round-robin selection
            # Note: If prompt_names is also empty, this will raise an IndexError,
            # but we assume prompt_names is always populated.
            return self.prompt_names[
                len(self.feature_history) % len(self.prompt_names)
            ]

        try:
            # Predict scores for all prompts
            features_matrix = np.tile(
                features_vector, (len(self.prompt_names), 1)
            )
            prompt_indices = np.arange(len(self.prompt_names)).reshape(-1, 1)
            x_with_prompt = np.hstack([features_matrix, prompt_indices])

            predicted_scores = self.model.predict(x_with_prompt)
            best_index = np.argmax(predicted_scores)
            return self.prompt_names[best_index]
        except (ValueError, IndexError) as e:
            # Fallback if model prediction fails
            print(f"Model prediction failed: {e}")
            return self.prompt_names[0]

    def update_model(self, features_vector, prompt_name, score):
        """Update the model with new training data."""
        # Store the new data point
        self.feature_history.append(features_vector)
        self.prompt_history.append(self.prompt_names.index(prompt_name))
        self.score_history.append(score)

        if len(self.feature_history) >= self.min_samples_for_training:
            try:
                # Prepare training data
                features_matrix = np.array(self.feature_history)
                prompt_indices = np.array(self.prompt_history).reshape(-1, 1)
                x_combined = np.hstack([features_matrix, prompt_indices])
                target_scores = np.array(self.score_history)

                # Train or retrain the model
                if not self.is_trained:
                    self.scaler.fit(x_combined)
                    self.is_trained = True

                x_scaled = self.scaler.transform(x_combined)
                self.model.fit(x_scaled, target_scores)
            except (ValueError, RuntimeError) as e:
                print(f"Model training failed: {e}")
                self.is_trained = False

    def generate_review(self, diff_text, selected_prompt):
        """Generate review using the selected prompt."""
        chain = self.prompts[selected_prompt] | llm | parser
        start = time.time()
        review_text = chain.invoke({"diff": diff_text[:4000]})
        elapsed = time.time() - start
        return review_text, elapsed

    def evaluate_review(self, diff_text, review_text):
        """Evaluate the generated review."""
        heur = heuristic_metrics(review_text)
        meta_parsed, _ = meta_evaluate(diff_text, review_text)

        # Calculate overall score
        if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
            weights = {
                "clarity": 0.18,
                "usefulness": 0.28,
                "depth": 0.2,
                "actionability": 0.24,
                "positivity": 0.1
            }
            meta_score = sum(
                meta_parsed.get(k, 5) * w for k, w in weights.items()
            )

            # Heuristic score
            sections = heur.get("sections_presence", {})
            sec_frac = sum(sections.values()) / max(1, len(sections))
            bullets_score = min(heur.get("bullet_points", 0), 10) / 10.0
            words = heur.get("length_words", 0)
            length_score = (1.0 if 80 <= words <= 800
                            else max(0.0, min(words/80, 1.0 - (words-800)/2000)))

            heur_score = (
                0.45 * sec_frac + 0.25 * bullets_score + 0.25 * length_score +
                0.05 * heur.get("mentions_bug", False) +
                0.05 * heur.get("mentions_suggest", False)
            ) * 10

            overall_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
        else:
            overall_score = 5.0  # Default score if evaluation fails

        return overall_score, heur, meta_parsed

    def process_pr(self, pr_number, owner=OWNER, repo=REPO, token=GITHUB_TOKEN):
        """Process a single PR using iterative prompt selection."""
        print(f"Processing PR #{pr_number}...")

        # Fetch PR diff
        diff_text = fetch_pr_diff(owner, repo, pr_number, token)

        # Extract features
        features = self.extract_pr_features(diff_text)
        features_vector = self.features_to_vector(features)

        # Select best prompt
        selected_prompt = self.select_best_prompt(features_vector)
        print(f"Selected prompt: {selected_prompt}")

        # Generate review
        review_text, elapsed = self.generate_review(diff_text, selected_prompt)
        print(f"Review generated in {elapsed:.2f}s")

        # Evaluate review
        score, heur, meta_parsed = self.evaluate_review(diff_text, review_text)
        print(f"Review score: {score}/10")

        # Update model with new data
        self.update_model(features_vector, selected_prompt, score)

        # Save results
        self.save_results(
            pr_number, features, selected_prompt,
            review_text, score, heur, meta_parsed
        )

        return {
            "pr_number": pr_number,
            "selected_prompt": selected_prompt,
            "review": review_text,
            "score": score,
            "features": features
        }

    def save_results(self, pr_number, features, prompt,
                     review, score, heur, meta_parsed):
        """Save results to file for analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"iterative_results_pr{pr_number}_{timestamp}.json"

        result = {
            "timestamp": timestamp,
            "pr_number": pr_number,
            "selected_prompt": prompt,
            "review_score": score,
            "features": features,
            "heuristics": heur,
            "meta_evaluation": meta_parsed,
            "training_data_size": len(self.feature_history),
            "model_trained": self.is_trained
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        # Also save the review itself
        review_filename = f"review_pr{pr_number}_{prompt.replace(' ', '_')}.txt"
        with open(review_filename, 'w', encoding='utf-8') as f:
            f.write(review)

        print(f"Results saved to {filename}")

    def get_stats(self):
        """Get current statistics about the model."""
        return {
            "training_samples": len(self.feature_history),
            "is_trained": self.is_trained,
            "average_score": (np.mean(self.score_history)
                              if self.score_history else 0),
            "prompt_distribution": {
                name: self.prompt_history.count(i)
                for i, name in enumerate(self.prompt_names)
            }
        }

    def save_state(self, filename="selector_state.json"):
        """Save learning state to file."""
        state = {
            "feature_history": [f.tolist() for f in self.feature_history],
            "prompt_history": self.prompt_history,
            "score_history": self.score_history,
            "is_trained": self.is_trained,
            "scaler_mean": (self.scaler.mean_.tolist()
                            if self.is_trained else None),
            "scaler_scale": (self.scaler.scale_.tolist()
                             if self.is_trained else None)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(state, f)

    def load_state(self, filename="selector_state.json"):
        """Load learning state from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.feature_history = [
                np.array(f) for f in state["feature_history"]
            ]
            self.prompt_history = state["prompt_history"]
            self.score_history = state["score_history"]
            self.is_trained = state["is_trained"]

            # Restore scaler state if trained
            if self.is_trained and state["scaler_mean"]:
                self.scaler.mean_ = np.array(state["scaler_mean"])
                self.scaler.scale_ = np.array(state["scaler_scale"])
                self.scaler.n_features_in_ = len(state["scaler_mean"])
                self.scaler.var_ = self.scaler.scale_ ** 2

            print(f"Loaded state with {len(self.feature_history)} "
                  f"training samples")
        except FileNotFoundError:
            print("No saved state found. Starting fresh.")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"Error loading state: {e}. Starting fresh.")
            self.feature_history = []
            self.prompt_history = []
            self.score_history = []
            self.is_trained = False


def run_iterative_selector(pr_numbers, load_previous=True):
    """Run the iterative prompt selector on multiple PRs."""
    selector_instance = IterativePromptSelector()

    if load_previous:
        selector_instance.load_state()  # Load previous learning

    results_list = []

    for pr_number in pr_numbers:
        try:
            result = selector_instance.process_pr(pr_number)
            results_list.append(result)

            # Print current stats
            stats = selector_instance.get_stats()
            print(f"\nCurrent stats: {stats}\n")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except (ValueError, KeyError, RuntimeError) as e:
            print(f"Failed to process PR #{pr_number}: {e}")
            continue

    # Final report
    print("\n" + "="*50)
    print("FINAL ITERATIVE SELECTOR REPORT")
    print("="*50)

    for result in results_list:
        print(f"PR #{result['pr_number']}: {result['selected_prompt']} -> "
              f"Score: {result['score']}")

    final_stats = selector_instance.get_stats()

    print(f"\nFinal statistics: {final_stats}")

    selector_instance.save_state()

    return results_list, selector_instance


if __name__ == "__main__":
    # Example usage: process multiple PRs
    pr_list = [PR_NUMBER]  # Start with your current PR
    # You can extend this list with more PR numbers

    results, selector = run_iterative_selector(pr_list)
