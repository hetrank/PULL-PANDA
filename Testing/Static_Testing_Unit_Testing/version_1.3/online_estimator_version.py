"""
Iterative Prompt Selector Module
FIXED VERSION - Proper state updating and file generation
"""

# Standard library imports
import json
import os
import re
import time
from datetime import datetime

# Third-party imports
import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import NotFittedError

# Local imports
from reviewer import fetch_pr_diff, save_text_to_file, llm, parser
from config import OWNER, REPO, GITHUB_TOKEN
from prompts_v2 import get_prompts
from accuracy_checker import heuristic_metrics, meta_evaluate


class IterativePromptSelector:
    """Online learning system for selecting optimal prompts based on PR features"""

    def __init__(self):
        self.prompts = get_prompts()
        self.prompt_names = list(self.prompts.keys())

        # Online learning components
        self.model = SGDRegressor(
            random_state=42,
            warm_start=True,
            learning_rate='constant',
            eta0=0.01,
            alpha=0.0001,
            max_iter=1000,
            tol=1e-3
        )
        self.scaler = StandardScaler()
        self.is_scaler_fitted = False
        self.sample_count = 0

        # For persistence and stats
        self.feature_history = []
        self.prompt_history = []
        self.score_history = []

    def extract_pr_features(self, diff_text):
        """Extract features from PR diff for model prediction"""
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
        features['has_comments'] = int(
            bool(re.search(r'#.*|//.*|/\*.*?\*/', diff_text, re.DOTALL))
        )
        features['has_functions'] = int(
            bool(re.search(r'def\s+\w+|\bfunction\b|\bfunc\b',
                          diff_text, re.IGNORECASE))
        )
        features['has_imports'] = int(
            bool(re.search(r'^import\s|^from\s|^#include',
                          diff_text, re.MULTILINE))
        )

        # Content type features
        features['has_test'] = int(
            bool(re.search(r'test|spec|unittest', diff_text, re.IGNORECASE))
        )
        features['has_docs'] = int(
            bool(re.search(r'readme|doc|comment|documentation',
                          diff_text, re.IGNORECASE))
        )
        features['has_config'] = int(
            bool(re.search(r'\.json$|\.yml$|\.yaml$|\.xml$|\.conf',
                          diff_text, re.IGNORECASE))
        )

        # Language detection (simplified)
        features['is_python'] = int(
            bool(re.search(r'\.py$', diff_text, re.IGNORECASE))
        )
        features['is_js'] = int(
            bool(re.search(r'\.js$|\.ts$', diff_text, re.IGNORECASE))
        )
        features['is_java'] = int(
            bool(re.search(r'\.java$', diff_text, re.IGNORECASE))
        )

        return features

    def features_to_vector(self, features):
        """Convert features dict to numerical vector"""
        feature_order = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        return np.array([features.get(key, 0) for key in feature_order])

    def select_best_prompt(self, features_vector):
        """Select the best prompt using online model prediction"""
        if self.sample_count < 2:
            # Use round-robin for first few samples to explore
            return self.prompt_names[self.sample_count % len(self.prompt_names)]

        # Scale features
        if self.is_scaler_fitted:
            try:
                scaled_features = self.scaler.transform([features_vector])
            except (ValueError, AttributeError, Exception): #pylint: disable=broad-except
                scaled_features = [features_vector]
        else:
            scaled_features = [features_vector]

        # Predict for all prompts and select best
        best_score = -float('inf')
        best_prompt = self.prompt_names[0]

        for i, prompt_name in enumerate(self.prompt_names):
            # Combine features with prompt index
            x_pred = np.hstack([scaled_features, [[i]]])

            try:
                score = self.model.predict(x_pred)[0]
                print(f"  {prompt_name}: predicted score = {score:.2f}")
                if score > best_score:
                    best_score = score
                    best_prompt = prompt_name
            except (ValueError, AttributeError, Exception): #pylint: disable=broad-except
                continue

        # Add exploration - sometimes choose random prompt to explore
        if self.sample_count < len(self.prompt_names) * 2:
            if np.random.random() < 0.3:
                explore_prompt = self.prompt_names[
                    self.sample_count % len(self.prompt_names)
                ]
                print(
                    f"  Exploring: choosing {explore_prompt} "
                    f"instead of {best_prompt}"
                )
                return explore_prompt

        return best_prompt

    def update_model(self, features_vector, prompt_name, score):
        """Online update with new data"""
        prompt_index = self.prompt_names.index(prompt_name)

        print(
            f"Updating model with prompt '{prompt_name}' "
            f"(index {prompt_index}), score: {score}"
        )

        # FIXED: Always append to history FIRST before any processing
        self.feature_history.append(features_vector)
        self.prompt_history.append(prompt_index)
        self.score_history.append(score)
        self.sample_count += 1

        # Now handle scaling and model updates
        if not self.is_scaler_fitted and len(self.feature_history) >= 2:
            # Initialize scaler with all available features
            self.scaler.fit(self.feature_history)
            self.is_scaler_fitted = True
            print("  Scaler fitted with all available data")

        if self.is_scaler_fitted:
            try:
                scaled_features = self.scaler.transform([features_vector])
            except (ValueError, AttributeError):
                # If transform fails, refit scaler
                self.scaler.fit(self.feature_history)
                scaled_features = self.scaler.transform([features_vector])
        else:
            scaled_features = [features_vector]

        # Prepare training sample
        x_train = np.hstack([scaled_features, [[prompt_index]]])
        y_train = [score]

        # Online learning
        try:
            if len(self.feature_history) == 1:
                # First sample
                self.model.partial_fit(x_train, y_train)
            else:
                # Update with current sample
                self.model.partial_fit(x_train, y_train)
        except (ValueError, AttributeError) as error:
            print(f"Model update failed: {error}. Reinitializing model.")
            self.model = SGDRegressor(
                random_state=42,
                warm_start=True,
                learning_rate='constant',
                eta0=0.01,
                alpha=0.0001
            )
            # Retrain with all data
            if len(self.feature_history) > 0:
                all_x = []
                all_y = []
                for feat, prompt_idx, scr in zip(
                    self.feature_history, self.prompt_history,
                    self.score_history
                ):
                    if self.is_scaler_fitted:
                        scaled_feat = self.scaler.transform([feat])
                    else:
                        scaled_feat = [feat]
                    x_sample = np.hstack([scaled_feat, [[prompt_idx]]])
                    all_x.append(x_sample[0])
                    all_y.append(scr)

                self.model.partial_fit(all_x, all_y)

    def generate_review(self, diff_text, selected_prompt):
        """Generate review using the selected prompt"""
        chain = self.prompts[selected_prompt] | llm | parser
        start = time.time()
        review_text = chain.invoke({"diff": diff_text[:4000]})
        elapsed = time.time() - start
        return review_text, elapsed

    def evaluate_review(self, diff_text, review_text):
        """Evaluate the generated review"""
        heur = heuristic_metrics(review_text)
        meta_parsed, _ = meta_evaluate(diff_text, review_text)

        # Calculate overall score
        if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
            weights = {
                "clarity": 0.18, "usefulness": 0.28, "depth": 0.2,
                "actionability": 0.24, "positivity": 0.1
            }
            meta_score = sum(
                meta_parsed.get(k, 5) * w for k, w in weights.items()
            )

            # Heuristic score
            sections = heur.get("sections_presence", {})
            sec_frac = sum(sections.values()) / max(1, len(sections))
            bullets_score = min(heur.get("bullet_points", 0), 10) / 10.0
            words = heur.get("length_words", 0)
            if 80 <= words <= 800:
                length_score = 1.0
            else:
                length_score = max(
                    0.0, min(words/80, 1.0 - (words-800)/2000)
                )

            heur_score = (
                0.45 * sec_frac + 0.25 * bullets_score +
                0.25 * length_score +
                0.05 * heur.get("mentions_bug", False) +
                0.05 * heur.get("mentions_suggest", False)
            ) * 10

            overall_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
        else:
            overall_score = 5.0

        return overall_score, heur, meta_parsed

    def save_state(self, filename="selector_state.json"):
        """Save learning state to file"""
        try:
            state = {
                "feature_history": [f.tolist() for f in self.feature_history],
                "prompt_history": self.prompt_history,
                "score_history": self.score_history,
                "sample_count": self.sample_count,
                "is_scaler_fitted": self.is_scaler_fitted,
                "model_coef": (
                    self.model.coef_.tolist()
                    if hasattr(self.model, 'coef_') else None
                ),
                "model_intercept": (
                    self.model.intercept_.tolist()
                    if hasattr(self.model, 'intercept_') else None
                ),
                "scaler_mean": (
                    self.scaler.mean_.tolist()
                    if self.is_scaler_fitted else None
                ),
                "scaler_scale": (
                    self.scaler.scale_.tolist()
                    if self.is_scaler_fitted else None
                ),
                "timestamp": datetime.now().isoformat()
            }

            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(state, file, indent=2)

            print(f"State saved with {self.sample_count} samples")
            return True

        except (IOError, OSError) as error:
            print(f"Error saving state: {error}")
            return False

    def load_state(self, filename="selector_state.json"):
        """FIXED: Load state and COMBINE with current data"""
        try:
            if not os.path.exists(filename):
                print("No saved state file found.")
                return False

            with open(filename, 'r', encoding='utf-8') as file:
                saved_state = json.load(file)

            print(
                f"Found saved state with "
                f"{saved_state.get('sample_count', 0)} samples"
            )

            # FIXED: COMBINE saved data with current data
            saved_features = [
                np.array(f) for f in saved_state.get("feature_history", [])
            ]
            saved_prompts = saved_state.get("prompt_history", [])
            saved_scores = saved_state.get("score_history", [])

            # Combine with current data (avoid duplicates)
            current_feature_hashes = [
                hash(tuple(f)) for f in self.feature_history
            ]

            for feat, prompt, score in zip(
                saved_features, saved_prompts, saved_scores
            ):
                feat_hash = hash(tuple(feat))
                if feat_hash not in current_feature_hashes:
                    self.feature_history.append(feat)
                    self.prompt_history.append(prompt)
                    self.score_history.append(score)
                    self.sample_count += 1

            print(
                f"Combined state: now have {self.sample_count} total samples"
            )

            # Load model and scaler state if available
            if saved_state.get("is_scaler_fitted", False):
                if "scaler_mean" in saved_state and saved_state["scaler_mean"]:
                    try:
                        self.scaler.mean_ = np.array(
                            saved_state["scaler_mean"]
                        )
                        self.scaler.scale_ = np.array(
                            saved_state["scaler_scale"]
                        )
                        self.scaler.n_features_in_ = len(
                            saved_state["scaler_mean"]
                        )
                        self.is_scaler_fitted = True
                        print("Loaded scaler state")
                    except (ValueError, KeyError) as error:
                        print(f"Failed to load scaler: {error}")

            if "model_coef" in saved_state and saved_state["model_coef"]:
                try:
                    self.model.coef_ = np.array(saved_state["model_coef"])
                    self.model.intercept_ = np.array(
                        saved_state["model_intercept"]
                    )
                    print("Loaded model weights")
                except (ValueError, KeyError) as error:
                    print(f"Failed to load model weights: {error}")

            return True

        except (IOError, OSError, json.JSONDecodeError) as error:
            print(f"Error loading state: {error}. Continuing with current data.")
            return False

    def process_pr(self, pr_number, owner=OWNER, repo=REPO, token=GITHUB_TOKEN):
        """Process a single PR using iterative prompt selection"""
        print(f"Processing PR #{pr_number}...")

        # Fetch PR diff
        diff_text = fetch_pr_diff(owner, repo, pr_number, token)

        # Extract features
        features = self.extract_pr_features(diff_text)
        features_vector = self.features_to_vector(features)
        print(f"PR features: {features}")

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

        # FIXED: Save results using the proper save_text_to_file function
        self.save_results(
            pr_number, features, selected_prompt,
            review_text, score, heur, meta_parsed
        )

        # Auto-save state
        if self.sample_count % 3 == 0:
            self.save_state()

        return {
            "pr_number": pr_number,
            "selected_prompt": selected_prompt,
            "review": review_text,
            "score": score,
            "features": features,
            "generation_time": elapsed
        }

    def save_results(
        self, pr_number, features, prompt,
        review, score, heur, meta_parsed
    ):
        """FIXED: Save results using proper file saving"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        result = {
            "timestamp": timestamp,
            "pr_number": pr_number,
            "selected_prompt": prompt,
            "review_score": score,
            "features": features,
            "heuristics": heur,
            "meta_evaluation": meta_parsed,
            "training_samples": self.sample_count
        }

        json_filename = f"iterative_results_pr{pr_number}_{timestamp}.json"
        save_text_to_file(json_filename, json.dumps(result, indent=2))

        # FIXED: Save review text using proper function
        safe_prompt_name = prompt.replace(' ', '_').replace('/', '_')
        review_filename = f"review_pr{pr_number}_{safe_prompt_name}.txt"
        save_text_to_file(review_filename, review)

        print(f"Results saved to {json_filename} and {review_filename}")

    def get_stats(self):
        """Get current statistics about the model"""
        prompt_distribution = {}
        for i, name in enumerate(self.prompt_names):
            prompt_distribution[name] = self.prompt_history.count(i)

        return {
            "training_samples": self.sample_count,
            "average_score": (
                np.mean(self.score_history) if self.score_history else 0
            ),
            "prompt_distribution": prompt_distribution,
            "unique_prompts_used": len(set(self.prompt_history)),
            "is_scaler_fitted": self.is_scaler_fitted
        }


def run_iterative_selector(pr_numbers, load_previous=True, save_frequency=2):
    """Run the iterative prompt selector on multiple PRs"""
    selector_instance = IterativePromptSelector()

    if load_previous:
        print("Attempting to load previous state...")
        selector_instance.load_state()

    results_list = []

    for i, pr_number in enumerate(pr_numbers):
        try:
            print(f"\n{'='*50}")
            print(f"Processing PR #{pr_number} ({i+1}/{len(pr_numbers)})")
            print(f"{'='*50}")

            result = selector_instance.process_pr(pr_number)
            results_list.append(result)

            # Print current stats
            stats = selector_instance.get_stats()
            print(f"\nCurrent stats: {stats}")

            # Save state periodically
            if (i + 1) % save_frequency == 0:
                print("Periodic state save...")
                selector_instance.save_state()

            time.sleep(1)

        except (IOError, OSError, ValueError) as error:
            print(f"Failed to process PR #{pr_number}: {error}")
            continue

    # Final save
    print("\nFinal state save...")
    selector_instance.save_state()

    # Final report
    print("\n" + "="*60)
    print("FINAL ITERATIVE SELECTOR REPORT")
    print("="*60)

    for result in results_list:
        print(
            f"PR #{result['pr_number']}: {result['selected_prompt']} -> "
            f"Score: {result['score']}"
        )

    final_stats = selector_instance.get_stats()
    print(f"\nFinal statistics: {final_stats}")

    return results_list, selector_instance


if __name__ == "__main__":
    # You can specify multiple PRs here
    pr_list = [3]  # Example PR numbers
    results, selector = run_iterative_selector(pr_list)