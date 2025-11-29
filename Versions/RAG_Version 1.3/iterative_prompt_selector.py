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
from reviewer import fetch_pr_diff, save_text_to_file, llm, parser, post_review_comment, fetch_pr_metadata
from config import OWNER, REPO, GITHUB_TOKEN, PR_NUMBER
from prompts import get_prompts
from accuracy_checker import heuristic_metrics, meta_evaluate

# NEW IMPORTS
from static_analysis import run_static_analysis
from rag_core import get_retriever
from utils import safe_truncate

import sys    # added to receive shared repo path

class IterativePromptSelector:
    def __init__(self):
        self.prompts = get_prompts()
        self.prompt_names = list(self.prompts.keys())
        
        print("Initializing RAG retriever...")
        self.retriever = get_retriever()
        print("✅ Retriever ready.")
        
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
        
        self.feature_history = []
        self.prompt_history = []
        self.score_history = []

        if len(sys.argv) > 1:
            self.shared_repo_path = sys.argv[1]
            print(f"🔄 Shared repo path for static analysis: {self.shared_repo_path}")
        else:
            self.shared_repo_path = None


    # Feature Extraction 
    def extract_pr_features(self, diff_text):
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
        feature_order = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        return np.array([features.get(key, 0) for key in feature_order])

    # Online selection logic 
    def select_best_prompt(self, features_vector):
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
            except:
                continue
        
        if self.sample_count < len(self.prompt_names) * 2:
            if np.random.random() < 0.3:
                explore_prompt = self.prompt_names[self.sample_count % len(self.prompt_names)]
                print(f"  Exploring: choosing {explore_prompt} instead of {best_prompt}")
                return explore_prompt
                
        return best_prompt
    

    # Model Update
    def update_model(self, features_vector, prompt_name, score):
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
        except:
            print("Model update failed, reinitializing model.")
            self.model = SGDRegressor(
                random_state=42, warm_start=True, learning_rate='constant',
                eta0=0.01, alpha=0.0001
            )
    
    #  MODIFIED: pass shared repo into static analyzer
        def generate_review(self, diff_text, selected_prompt):
        """Generate review using RAG + static analysis + LLM"""

        if self.shared_repo_path:
            print(f"🔄 Passing shared repo path → Static Analysis: {self.shared_repo_path}")
            sys.argv = [sys.argv[0], self.shared_repo_path]  # override CLI args
        else:
            print("⚠ No shared repo path. Static analyzer will clone.")

        static_output = run_static_analysis(diff_text, OWNER, REPO, PR_NUMBER)

        chain = self.prompts[selected_prompt] | llm | parser
        start = time.time()

        print("  Running RAG retrieval...")
        retrieval_query = (
            f"How to review this code?\nDiff: {safe_truncate(diff_text, 1000)}\n"
            f"Static: {safe_truncate(static_output, 1000)}"
        )

        retrieved_docs = self.retriever.invoke(retrieval_query)
        retrieved_context = "\n---\n".join([doc.page_content for doc in retrieved_docs])

        truncated_diff = safe_truncate(diff_text, 4000)
        truncated_static = safe_truncate(static_output, 2000)
        truncated_context = safe_truncate(retrieved_context, 2000)

        review_text = chain.invoke({
            "diff": truncated_diff,
            "static": truncated_static,
            "context": truncated_context
        })
        elapsed = time.time() - start

        return review_text, elapsed, static_output, retrieved_context
    

    # Evaluation
    def evaluate_review(self, diff_text, review_text, static_output, context):
        heur = heuristic_metrics(review_text)
        meta_parsed, meta_raw = meta_evaluate(diff_text, review_text, static_output, context)

        if isinstance(meta_parsed, dict) and "error" not in meta_parsed:
            weights = {"clarity": 0.18, "usefulness": 0.28, "depth": 0.2, 
                       "actionability": 0.24, "positivity": 0.1}
            meta_score = sum(meta_parsed.get(k, 5) * w for k, w in weights.items())
            overall_score = round(meta_score, 2)
        else:
            overall_score = 5.0
        return overall_score, heur, meta_parsed
    

    # Save Review Results 
    def save_results(self, pr_number, features, prompt, review, score, heur, meta_parsed, static_output, context):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result = {
            "timestamp": timestamp,
            "pr_number": pr_number,
            "selected_prompt": prompt,
            "review_score": score,
            "features": features,
            "heuristics": heur,
            "meta_evaluation": meta_parsed,
            "training_samples": self.sample_count,
            "static_output": static_output,
            "retrieved_context": context
        }
        
        json_filename = f"iterative_results_pr{pr_number}_{timestamp}.json"
        save_text_to_file(json_filename, json.dumps(result, indent=2))
        
        safe_prompt_name = prompt.replace(' ', '_').replace('/', '_')
        review_filename = f"review_pr{pr_number}_{safe_prompt_name}.md"
        
        content = (
            f"# Review for PR #{pr_number} (Prompt: {prompt})\n"
            f"**Score:** {score}/10\n\n---\n\n"
            f"## 🤖 AI Review\n\n{review}\n\n---\n\n"
            f"## 🔍 Static Analysis Output\n\n{static_output}\n\n---\n\n"
            f"## 🧠 Retrieved RAG Context\n\n<details><summary>Expand</summary>\n\n```\n{context}\n```\n</details>"
        )
        save_text_to_file(review_filename, content)
    

    # Process PR (slight modification: pass repo)
        def process_pr(self, pr_number, owner=OWNER, repo=REPO, token=GITHUB_TOKEN, post_to_github=True):
        print(f"Processing PR #{pr_number}...")

        pr_meta = fetch_pr_metadata(owner, repo, pr_number, token)

        if pr_meta is None or ("message" in pr_meta and pr_meta["message"] == "Not Found"):
            print(f"⚠️ PR #{pr_number} not found. Skipping.")
            return {
                "pr_number": pr_number,
                "selected_prompt": None,
                "review": None,
                "score": None,
                "features": None,
                "generation_time": 0
            }
        
        diff_text = fetch_pr_diff(owner, repo, pr_number, token)
        features = self.extract_pr_features(diff_text)
        features_vector = self.features_to_vector(features)

        selected_prompt = self.select_best_prompt(features_vector)
        
        review_text, elapsed, static_output, context = self.generate_review(diff_text, selected_prompt)
        
        score, heur, meta_parsed = self.evaluate_review(diff_text, review_text, static_output, context)
        
        self.update_model(features_vector, selected_prompt, score)

        self.save_results(pr_number, features, selected_prompt, review_text, score, heur, meta_parsed, static_output, context)

        if post_to_github:
            github_body = (
                f"🤖 **AI Review**\n\n"
                f"Prompt: `{selected_prompt}` | Score: **{score}/10**\n\n"
                f"---\n{review_text}"
            )
            post_review_comment(owner, repo, pr_number, token, github_body)

        return {
            "pr_number": pr_number,
            "selected_prompt": selected_prompt,
            "review": review_text,
            "score": score,
            "features": features,
            "generation_time": elapsed
        }


# Multi-PR runner (unchanged)
def run_iterative_selector(pr_numbers, load_previous=True, save_frequency=2, post_to_github=True):
    selector = IterativePromptSelector()
    
    results = []

    for i, pr_number in enumerate(pr_numbers):
        result = selector.process_pr(pr_number, post_to_github=post_to_github)
        results.append(result)
        time.sleep(1)

    print("\nSaving final selector state...")
    return results, selector


# main
    if __name__ == "__main__":
    if PR_NUMBER <= 0:
        print("PR_NUMBER invalid in .env")
    else:
        run_iterative_selector([PR_NUMBER]
