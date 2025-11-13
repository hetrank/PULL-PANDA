# iterative_prompt_selector.py
# MODIFIED VERSION - RAG + Static Analysis + Online Learning

import json
import time
import numpy as np
import os
import re
from datetime import datetime
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from reviewer import fetch_pr_diff, save_text_to_file, llm, parser, post_review_comment
from config import OWNER, REPO, GITHUB_TOKEN, PR_NUMBER
from prompts import get_prompts
from accuracy_checker import heuristic_metrics, meta_evaluate

# --- NEW IMPORTS ---
from static_analysis import run_static_analysis
from rag_core import get_retriever
from utils import safe_truncate
# ---------------------

class IterativePromptSelector:
    def __init__(self):
        self.prompts = get_prompts()
        self.prompt_names = list(self.prompts.keys())
        
        # --- NEW: Initialize Retriever ---
        print("Initializing RAG retriever...")
        self.retriever = get_retriever()
        print("✅ Retriever ready.")
        # ---------------------------------
        
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
        
    # ... (extract_pr_features and features_to_vector methods are unchanged) ...
    def extract_pr_features(self, diff_text):
        """Extract features from PR diff for model prediction"""
        features = {}
        features['num_lines'] = len(diff_text.split('\n'))
        features['num_files'] = len(re.findall(r'^diff --git', diff_text, re.MULTILINE))
        features['additions'] = len(re.findall(r'^\+', diff_text, re.MULTILINE))
        features['deletions'] = len(re.findall(r'^-', diff_text, re.MULTILINE))
        features['net_changes'] = features['additions'] - features['deletions']
        features['has_comments'] = int(bool(re.search(r'#.*|//.*|/\*.*?\*/', diff_text, re.DOTALL)))
        features['has_functions'] = int(bool(re.search(r'def\s+\w+|\bfunction\b|\bfunc\b', diff_text, re.IGNORECASE)))
        features['has_imports'] = int(bool(re.search(r'^import\s|^from\s|^#include', diff_text, re.MULTILINE)))
        features['has_test'] = int(bool(re.search(r'test|spec|unittest', diff_text, re.IGNORECASE)))
        features['has_docs'] = int(bool(re.search(r'readme|doc|comment|documentation', diff_text, re.IGNORECASE)))
        features['has_config'] = int(bool(re.search(r'\.json$|\.yml$|\.yaml$|\.xml$|\.conf', diff_text, re.IGNORECASE)))
        features['is_python'] = int(bool(re.search(r'\.py$', diff_text, re.IGNORECASE)))
        features['is_js'] = int(bool(re.search(r'\.js$|\.ts$', diff_text, re.IGNORECASE)))
        features['is_java'] = int(bool(re.search(r'\.java$', diff_text, re.IGNORECASE)))
        return features
    
    def features_to_vector(self, features):
        """Convert features dict to numerical vector"""
        feature_order = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        return np.array([features.get(key, 0) for key in feature_order])

    # ... (select_best_prompt and update_model methods are unchanged) ...
    def select_best_prompt(self, features_vector):
        """Select the best prompt using online model prediction"""
        if self.sample_count < 2:
            return self.prompt_names[self.sample_count % len(self.prompt_names)]
        
        if self.is_scaler_fitted:
            try:
                scaled_features = self.scaler.transform([features_vector])
            except:
                scaled_features = [features_vector]
        else:
            scaled_features = [features_vector]
        
        best_score = -float('inf')
        best_prompt = self.prompt_names[0]
        
        for i, prompt_name in enumerate(self.prompt_names):
            X_pred = np.hstack([scaled_features, [[i]]])
            
            try:
                score = self.model.predict(X_pred)[0]
                print(f"  {prompt_name}: predicted score = {score:.2f}")
                if score > best_score:
                    best_score = score
                    best_prompt = prompt_name
            except Exception as e:
                continue
        
        if self.sample_count < len(self.prompt_names) * 2:
            if np.random.random() < 0.3:
                explore_prompt = self.prompt_names[self.sample_count % len(self.prompt_names)]
                print(f"  Exploring: choosing {explore_prompt} instead of {best_prompt}")
                return explore_prompt
                
        return best_prompt
    
    def update_model(self, features_vector, prompt_name, score):
        """Online update with new data"""
        prompt_index = self.prompt_names.index(prompt_name)
        
        print(f"Updating model with prompt '{prompt_name}' (index {prompt_index}), score: {score}")
        
        self.feature_history.append(features_vector)
        self.prompt_history.append(prompt_index)
        self.score_history.append(score)
        self.sample_count += 1
        
        if not self.is_scaler_fitted and len(self.feature_history) >= 2:
            self.scaler.fit(self.feature_history)
            self.is_scaler_fitted = True
            print("  Scaler fitted with all available data")
        
        if self.is_scaler_fitted:
            try:
                scaled_features = self.scaler.transform([features_vector])
            except:
                self.scaler.fit(self.feature_history)
                scaled_features = self.scaler.transform([features_vector])
        else:
            scaled_features = [features_vector]
        
        X_train = np.hstack([scaled_features, [[prompt_index]]])
        y_train = [score]
        
        try:
            self.model.partial_fit(X_train, y_train)
        except Exception as e:
            print(f"Model update failed: {e}. Reinitializing model.")
            self.model = SGDRegressor(
                random_state=42, warm_start=True, learning_rate='constant',
                eta0=0.01, alpha=0.0001
            )
            if len(self.feature_history) > 0:
                all_X = []
                all_y = []
                for i, (feat, prompt_idx, scr) in enumerate(zip(
                    self.feature_history, self.prompt_history, self.score_history
                )):
                    if self.is_scaler_fitted:
                        scaled_feat = self.scaler.transform([feat])
                    else:
                        scaled_feat = [feat]
                    X_sample = np.hstack([scaled_feat, [[prompt_idx]]])
                    all_X.append(X_sample[0])
                    all_y.append(scr)
                self.model.partial_fit(all_X, all_y)

    # --- MODIFIED: generate_review now runs RAG and Static Analysis ---
    def generate_review(self, diff_text, selected_prompt):
        """Generate review using RAG, static analysis, and the selected prompt"""
        chain = self.prompts[selected_prompt] | llm | parser
        start = time.time()

        # 1. Run Static Analysis
        print("  Running static analysis...")
        static_output = run_static_analysis(diff_text)
        
        # 2. Run RAG
        print("  Running RAG retrieval...")
        retrieval_query = f"How to review this code? Diff: {safe_truncate(diff_text, 1000)}\nStatic Analysis: {safe_truncate(static_output, 1000)}"
        retrieved_docs = self.retriever.invoke(retrieval_query)
        retrieved_context = "\n---\n".join([doc.page_content for doc in retrieved_docs])
        
        # 3. Truncate inputs
        truncated_diff = safe_truncate(diff_text, 4000)
        truncated_static = safe_truncate(static_output, 2000)
        truncated_context = safe_truncate(retrieved_context, 2000)

        # 4. Invoke LLM with all context
        print("  Generating review...")
        review_text = chain.invoke({
            "diff": truncated_diff,
            "static": truncated_static,
            "context": truncated_context
        })
        elapsed = time.time() - start
        
        # Return all generated artifacts
        return review_text, elapsed, static_output, retrieved_context

    # --- MODIFIED: evaluate_review now accepts static/context ---
    def evaluate_review(self, diff_text, review_text, static_output, context):
        """Evaluate the generated review"""
        heur = heuristic_metrics(review_text)
        
        # Pass all context to the meta-evaluator
        meta_parsed, meta_raw = meta_evaluate(diff_text, review_text, static_output, context)
        
        if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
            weights = {"clarity": 0.18, "usefulness": 0.28, "depth": 0.2, 
                       "actionability": 0.24, "positivity": 0.1}
            meta_score = sum(meta_parsed.get(k, 5) * w for k, w in weights.items())
            
            sections = heur.get("sections_presence", {})
            sec_frac = sum(sections.values()) / max(1, len(sections))
            bullets_score = min(heur.get("bullet_points", 0), 10) / 10.0
            words = heur.get("length_words", 0)
            length_score = 1.0 if 80 <= words <= 800 else max(0.0, min(words/80, 1.0 - (words-800)/2000))
            
            heur_score = (0.45 * sec_frac + 0.25 * bullets_score + 0.25 * length_score + 
                          0.05 * heur.get("mentions_bug", False) + 0.05 * heur.get("mentions_suggest", False)) * 10
            
            overall_score = round(0.7 * meta_score + 0.3 * heur_score, 2)
        else:
            overall_score = 5.0 # Default score if meta-eval fails
        
        return overall_score, heur, meta_parsed
    
    # ... (save_state and load_state methods are unchanged) ...
    def save_state(self, filename="selector_state.json"):
        """Save learning state to file"""
        try:
            state = {
                "feature_history": [f.tolist() for f in self.feature_history],
                "prompt_history": self.prompt_history,
                "score_history": self.score_history,
                "sample_count": self.sample_count,
                "is_scaler_fitted": self.is_scaler_fitted,
                "model_coef": self.model.coef_.tolist() if hasattr(self.model, 'coef_') else None,
                "model_intercept": self.model.intercept_.tolist() if hasattr(self.model, 'intercept_') else None,
                "scaler_mean": self.scaler.mean_.tolist() if self.is_scaler_fitted else None,
                "scaler_scale": self.scaler.scale_.tolist() if self.is_scaler_fitted else None,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            
            print(f"State saved with {self.sample_count} samples")
            return True
            
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def load_state(self, filename="selector_state.json"):
        """FIXED: Load state and COMBINE with current data instead of overwriting"""
        try:
            if not os.path.exists(filename):
                print("No saved state file found.")
                return False
                
            with open(filename, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)
            
            print(f"Found saved state with {saved_state.get('sample_count', 0)} samples")
            
            saved_features = [np.array(f) for f in saved_state.get("feature_history", [])]
            saved_prompts = saved_state.get("prompt_history", [])
            saved_scores = saved_state.get("score_history", [])
            
            current_feature_hashes = [hash(tuple(f)) for f in self.feature_history]
            
            for feat, prompt, score in zip(saved_features, saved_prompts, saved_scores):
                feat_hash = hash(tuple(feat))
                if feat_hash not in current_feature_hashes:
                    self.feature_history.append(feat)
                    self.prompt_history.append(prompt)
                    self.score_history.append(score)
                    self.sample_count += 1
            
            print(f"Combined state: now have {self.sample_count} total samples")
            
            if saved_state.get("is_scaler_fitted", False):
                if "scaler_mean" in saved_state and saved_state["scaler_mean"]:
                    try:
                        self.scaler.mean_ = np.array(saved_state["scaler_mean"])
                        self.scaler.scale_ = np.array(saved_state["scaler_scale"])
                        self.scaler.n_features_in_ = len(saved_state["scaler_mean"])
                        self.is_scaler_fitted = True
                        print("Loaded scaler state")
                    except Exception as e:
                        print(f"Failed to load scaler: {e}")
            
            if "model_coef" in saved_state and saved_state["model_coef"]:
                try:
                    self.model.coef_ = np.array(saved_state["model_coef"])
                    self.model.intercept_ = np.array(saved_state["model_intercept"])
                    print("Loaded model weights")
                except Exception as e:
                    print(f"Failed to load model weights: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error loading state: {e}. Continuing with current data.")
            return False

    # --- MODIFIED: process_pr now handles the full RAG/static pipeline ---
    def process_pr(self, pr_number, owner=OWNER, repo=REPO, token=GITHUB_TOKEN, post_to_github: bool = True):
        """Process a single PR using iterative prompt selection"""
        print(f"Processing PR #{pr_number}...")
        
        diff_text = fetch_pr_diff(owner, repo, pr_number, token)
        
        features = self.extract_pr_features(diff_text)
        features_vector = self.features_to_vector(features)
        print(f"PR features: {features}")
        
        selected_prompt = self.select_best_prompt(features_vector)
        print(f"Selected prompt: {selected_prompt}")
        
        # Generate review (now returns 4 items)
        review_text, elapsed, static_output, context = self.generate_review(diff_text, selected_prompt)
        print(f"Review generated in {elapsed:.2f}s")
        
        # Evaluate review (now takes 4 items)
        score, heur, meta_parsed = self.evaluate_review(diff_text, review_text, static_output, context)
        print(f"Review score: {score}/10")
        
        self.update_model(features_vector, selected_prompt, score)
        
        # Save results (now takes 8 items)
        self.save_results(pr_number, features, selected_prompt, review_text, score, heur, meta_parsed, static_output, context)
        
        if self.sample_count % 3 == 0:
            self.save_state()
        if post_to_github:
            print(f"Posting review to GitHub PR #{pr_number}...")
            try:
                # Format a nice message for GitHub
                github_body = (
                    f"🤖 **AI-Powered Review** 🤖\n\n"
                    f"*(Prompt: `{selected_prompt}` | Score: **{score}/10**)*\n\n"
                    f"---\n\n"
                    f"{review_text}"
                )
                
                # Call the function from reviewer.py
                post_review_comment(owner, repo, pr_number, token, github_body)
                print("✅ Successfully posted comment to GitHub.")
            except Exception as e:
                print(f"❌ FAILED to post comment to GitHub: {e}")
        return {
            "pr_number": pr_number,
            "selected_prompt": selected_prompt,
            "review": review_text,
            "score": score,
            "features": features,
            "generation_time": elapsed
        }
    
    # --- MODIFIED: save_results now saves the static/context ---
    def save_results(self, pr_number, features, prompt, review, score, heur, meta_parsed, static_output, context):
        """Save all results, including static analysis and RAG context"""
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
            "training_samples": self.sample_count,
            "static_output": static_output, # NEW
            "retrieved_context": context    # NEW
        }
        
        json_filename = f"iterative_results_pr{pr_number}_{timestamp}.json"
        save_text_to_file(json_filename, json.dumps(result, indent=2))
        
        # Save review text as a markdown file
        safe_prompt_name = prompt.replace(' ', '_').replace('/', '_')
        review_filename = f"review_pr{pr_number}_{safe_prompt_name}.md"
        
        # Create rich markdown report
        content = (
            f"# Review for PR #{pr_number} (Prompt: {prompt})\n"
            f"**Score:** {score}/10\n\n"
            f"---\n\n"
            f"## 🤖 AI Review\n\n{review}\n\n"
            f"---\n\n"
            f"## 🔍 Static Analysis Output\n\n"
            f"```\n{static_output}\n```\n\n"
            f"---\n\n"
            f"## 🧠 Retrieved RAG Context\n\n{context}\n"
        )
        save_text_to_file(review_filename, content)
        
        print(f"Results saved to {json_filename} and {review_filename}")
    
    # ... (get_stats method is unchanged) ...
    def get_stats(self):
        """Get current statistics about the model"""
        prompt_distribution = {}
        for i, name in enumerate(self.prompt_names):
            prompt_distribution[name] = self.prompt_history.count(i)
        
        return {
            "training_samples": self.sample_count,
            "average_score": np.mean(self.score_history) if self.score_history else 0,
            "prompt_distribution": prompt_distribution,
            "unique_prompts_used": len(set(self.prompt_history)),
            "is_scaler_fitted": self.is_scaler_fitted
        }


def run_iterative_selector(pr_numbers, load_previous=True, save_frequency=2,post_to_github: bool = True):
    """Run the iterative prompt selector on multiple PRs"""
    selector = IterativePromptSelector()
    
    if load_previous:
        print("Attempting to load previous state...")
        selector.load_state()
    
    results = []
    
    for i, pr_number in enumerate(pr_numbers):
        try:
            print(f"\n{'='*50}")
            print(f"Processing PR #{pr_number} ({i+1}/{len(pr_numbers)})")
            print(f"{'='*50}")
            
            result = selector.process_pr(pr_number, post_to_github=post_to_github)
            results.append(result)
            
            stats = selector.get_stats()
            print(f"\nCurrent stats: {stats}")
            
            if (i + 1) % save_frequency == 0:
                print("Periodic state save...")
                selector.save_state()
            
            time.sleep(1) 
            
        except Exception as e:
            print(f"Failed to process PR #{pr_number}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\nFinal state save...")
    selector.save_state()
    
    print("\n" + "="*60)
    print("FINAL ITERATIVE SELECTOR REPORT")
    print("="*60)
    
    for result in results:
        print(f"PR #{result['pr_number']}: {result['selected_prompt']} -> Score: {result['score']}")
    
    final_stats = selector.get_stats()
    print(f"\nFinal statistics: {final_stats}")
    
    return results, selector


if __name__ == "__main__":
    # Check if the PR_NUMBER from config (via .env) is valid
    if PR_NUMBER <= 0:
        print("Error: PR_NUMBER is not set or is invalid in your .env file.")
        print("Please set PR_NUMBER in .env to the PR you want to review.")
    else:
        # The run_iterative_selector function expects a list of PRs.
        # We create a list containing just the one PR from our config.
        pr_list = [PR_NUMBER] 
        
        print(f"🚀 Starting agent to process PR #{PR_NUMBER} from .env file...")
        results, selector = run_iterative_selector(pr_list)