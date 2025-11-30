"""
Comprehensive unit tests for iterative_prompt_selector.py

Tests cover all functions with normal flows, edge cases, and boundary conditions.
All external dependencies are mocked.
"""

import json
import os
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime

import pytest
import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler


# Mock all external imports before importing the module under test
@pytest.fixture(autouse=True)
def mock_external_modules():
    """Mock all external dependencies."""
    with patch.dict('sys.modules', {
        'reviewer': MagicMock(),
        'config': MagicMock(OWNER='test-owner', REPO='test-repo', 
                           GITHUB_TOKEN='test-token', PR_NUMBER=123),
        'prompts': MagicMock(),
        'accuracy_checker': MagicMock(),
        'static_analysis': MagicMock(),
        'rag_core': MagicMock(),
        'utils': MagicMock(),
    }):
        yield


@pytest.fixture
def mock_dependencies():
    """Create mock objects for dependencies."""
    mocks = {
        'fetch_pr_diff': Mock(return_value="def foo():\n    pass\n+    return True"),
        'save_text_to_file': Mock(),
        'llm': Mock(),
        'parser': Mock(),
        'post_review_comment': Mock(),
        'get_prompts': Mock(return_value={
            'detailed': Mock(),
            'concise': Mock(),
            'security': Mock()
        }),
        'heuristic_metrics': Mock(return_value={
            'sections_presence': {'summary': True, 'issues': True, 'suggestions': True},
            'bullet_points': 5,
            'length_words': 250,
            'mentions_bug': True,
            'mentions_suggest': True
        }),
        'meta_evaluate': Mock(return_value=(
            {'clarity': 8, 'usefulness': 7, 'depth': 8, 'actionability': 9, 'positivity': 7},
            "Meta evaluation text"
        )),
        'run_static_analysis': Mock(return_value="No issues found"),
        'get_retriever': Mock(return_value=Mock(invoke=Mock(return_value=[
            Mock(page_content="Best practice 1"),
            Mock(page_content="Best practice 2")
        ]))),
        'safe_truncate': Mock(side_effect=lambda text, limit: text[:limit])
    }
    return mocks


@pytest.fixture
def selector_instance(mock_dependencies):
    """Create IterativePromptSelector instance with mocked dependencies."""
    with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
         patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
         patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']), \
         patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
         patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
         patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
         patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
         patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
         patch('iterative_prompt_selector.post_review_comment', mock_dependencies['post_review_comment']):
        
        from iterative_prompt_selector import IterativePromptSelector
        return IterativePromptSelector()


class TestIterativePromptSelectorInit:
    """Tests for __init__ method."""
    
    def test_initialization_creates_all_components(self, mock_dependencies):
        """Test that initialization creates all required components."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']):
            from iterative_prompt_selector import IterativePromptSelector
            selector = IterativePromptSelector()
            
            assert selector.prompts is not None
            assert len(selector.prompt_names) == 3
            assert isinstance(selector.model, SGDRegressor)
            assert isinstance(selector.scaler, StandardScaler)
            assert selector.is_scaler_fitted is False
            assert selector.sample_count == 0
    
    def test_initialization_creates_empty_histories(self, selector_instance):
        """Test that histories are initialized as empty lists."""
        assert selector_instance.feature_history == []
        assert selector_instance.prompt_history == []
        assert selector_instance.score_history == []
    
    def test_retriever_initialization(self, mock_dependencies):
        """Test that retriever is properly initialized."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']) as mock_retriever:
            from iterative_prompt_selector import IterativePromptSelector
            selector = IterativePromptSelector()
            
            mock_retriever.assert_called_once()
            assert selector.retriever is not None


class TestExtractPRFeatures:
    """Tests for extract_pr_features method."""
    
    def test_basic_diff_features(self, selector_instance):
        """Test feature extraction from basic diff."""
        diff = "diff --git a/file.py b/file.py\n+added line\n-removed line"
        features = selector_instance.extract_pr_features(diff)
        
        assert 'num_lines' in features
        assert 'num_files' in features
        assert 'additions' in features
        assert 'deletions' in features
        assert features['num_files'] == 1
    
    def test_empty_diff(self, selector_instance):
        """Test feature extraction from empty diff."""
        features = selector_instance.extract_pr_features("")
        
        assert features['num_lines'] == 1  # Empty string has 1 line
        assert features['num_files'] == 0
        assert features['additions'] == 0
        assert features['deletions'] == 0
    
    def test_multiple_files_detection(self, selector_instance):
        """Test detection of multiple files in diff."""
        diff = """diff --git a/file1.py b/file1.py
+code
diff --git a/file2.js b/file2.js
+more code"""
        features = selector_instance.extract_pr_features(diff)
        
        assert features['num_files'] == 2
    
    def test_python_file_detection(self, selector_instance):
        """Test Python file detection."""
        diff = "diff --git a/script.py b/script.py"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['is_python'] == 1
        assert features['is_js'] == 0
        assert features['is_java'] == 0
    
    def test_javascript_file_detection(self, selector_instance):
        """Test JavaScript file detection."""
        diff = "diff --git a/app.js b/app.js"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['is_js'] == 1
        assert features['is_python'] == 0
    
    def test_typescript_file_detection(self, selector_instance):
        """Test TypeScript file detection."""
        diff = "diff --git a/component.ts b/component.ts"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['is_js'] == 1
    
    def test_java_file_detection(self, selector_instance):
        """Test Java file detection."""
        diff = "diff --git a/Main.java b/Main.java"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['is_java'] == 1
    
    def test_function_detection(self, selector_instance):
        """Test function definition detection."""
        diff = "def my_function():\n    pass"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_functions'] == 1
    
    def test_import_detection(self, selector_instance):
        """Test import statement detection."""
        diff = "import os\nfrom datetime import datetime"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_imports'] == 1
    
    def test_comment_detection(self, selector_instance):
        """Test comment detection."""
        diff = "# This is a comment\n// Another comment\n/* Block comment */"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_comments'] == 1
    
    def test_test_file_detection(self, selector_instance):
        """Test test file detection."""
        diff = "diff --git a/test_module.py b/test_module.py"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_test'] == 1
    
    def test_documentation_detection(self, selector_instance):
        """Test documentation detection."""
        diff = "README.md updated with new documentation"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_docs'] == 1
    
    def test_config_file_detection(self, selector_instance):
        """Test config file detection."""
        diff = "diff --git a/config.json b/config.json"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['has_config'] == 1
    
    def test_net_changes_calculation(self, selector_instance):
        """Test net changes calculation."""
        diff = "+line1\n+line2\n+line3\n-line4"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['additions'] == 3
        assert features['deletions'] == 1
        assert features['net_changes'] == 2
    
    def test_large_diff_handling(self, selector_instance):
        """Test handling of large diff with many lines."""
        diff = "\n".join([f"+line{i}" for i in range(1000)])
        features = selector_instance.extract_pr_features(diff)
        
        assert features['num_lines'] == 1000
        assert features['additions'] == 1000


class TestFeaturesToVector:
    """Tests for features_to_vector method."""
    
    def test_complete_features_conversion(self, selector_instance):
        """Test conversion of complete feature dict to vector."""
        features = {
            'num_lines': 100,
            'num_files': 5,
            'additions': 50,
            'deletions': 20,
            'net_changes': 30,
            'has_comments': 1,
            'has_functions': 1,
            'has_imports': 1,
            'has_test': 0,
            'has_docs': 0,
            'has_config': 0,
            'is_python': 1,
            'is_js': 0,
            'is_java': 0
        }
        vector = selector_instance.features_to_vector(features)
        
        assert len(vector) == 14
        assert vector[0] == 100
        assert vector[1] == 5
        assert isinstance(vector, np.ndarray)
    
    def test_missing_features_default_to_zero(self, selector_instance):
        """Test that missing features default to zero."""
        features = {'num_lines': 50}
        vector = selector_instance.features_to_vector(features)
        
        assert len(vector) == 14
        assert vector[0] == 50
        assert vector[1] == 0
        assert np.sum(vector[2:]) == 0
    
    def test_empty_features_dict(self, selector_instance):
        """Test conversion of empty features dict."""
        vector = selector_instance.features_to_vector({})
        
        assert len(vector) == 14
        assert np.all(vector == 0)
    
    def test_extra_features_ignored(self, selector_instance):
        """Test that extra features in dict are ignored."""
        features = {
            'num_lines': 10,
            'extra_feature': 999,
            'another_extra': 'ignored'
        }
        vector = selector_instance.features_to_vector(features)
        
        assert len(vector) == 14
        assert vector[0] == 10


class TestSelectBestPrompt:
    """Tests for select_best_prompt method."""
    
    def test_first_sample_selection(self, selector_instance):
        """Test prompt selection for first sample."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        prompt = selector_instance.select_best_prompt(features)
        
        assert prompt in selector_instance.prompt_names
        assert prompt == selector_instance.prompt_names[0]
    
    def test_second_sample_selection(self, selector_instance):
        """Test prompt selection for second sample."""
        selector_instance.sample_count = 1
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        prompt = selector_instance.select_best_prompt(features)
        
        assert prompt == selector_instance.prompt_names[1]
    
    def test_selection_with_fitted_scaler(self, selector_instance):
        """Test prompt selection when scaler is fitted."""
        selector_instance.sample_count = 5
        selector_instance.is_scaler_fitted = True
        selector_instance.scaler.mean_ = np.zeros(14)
        selector_instance.scaler.scale_ = np.ones(14)
        selector_instance.model.coef_ = np.array([0.1, 0.2, 0.3])
        selector_instance.model.intercept_ = np.array([0.5])
        
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        with patch.object(selector_instance.scaler, 'transform', return_value=[features]):
            with patch.object(selector_instance.model, 'predict', return_value=[7.5]):
                prompt = selector_instance.select_best_prompt(features)
                
                assert prompt in selector_instance.prompt_names
    
    def test_exploration_policy_early_samples(self, selector_instance):
        """Test exploration policy for early samples."""
        selector_instance.sample_count = 3
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        with patch('numpy.random.random', return_value=0.2):
            prompt = selector_instance.select_best_prompt(features)
            assert prompt in selector_instance.prompt_names
    
    def test_prediction_failure_handling(self, selector_instance):
        """Test handling of prediction failures."""
        selector_instance.sample_count = 5
        selector_instance.is_scaler_fitted = True
        selector_instance.scaler.mean_ = np.zeros(14)
        selector_instance.scaler.scale_ = np.ones(14)
        
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        with patch.object(selector_instance.model, 'predict', side_effect=ValueError("Prediction error")):
            prompt = selector_instance.select_best_prompt(features)
            assert prompt in selector_instance.prompt_names
    
    def test_scaler_transform_failure(self, selector_instance):
        """Test handling when scaler transform fails."""
        selector_instance.sample_count = 5
        selector_instance.is_scaler_fitted = True
        
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        with patch.object(selector_instance.scaler, 'transform', side_effect=ValueError("Transform error")):
            prompt = selector_instance.select_best_prompt(features)
            assert prompt in selector_instance.prompt_names


class TestUpdateModel:
    """Tests for update_model method."""
    
    def test_first_update(self, selector_instance):
        """Test first model update."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        selector_instance.update_model(features, 'detailed', 8.5)
        
        assert selector_instance.sample_count == 1
        assert len(selector_instance.feature_history) == 1
        assert len(selector_instance.score_history) == 1
        assert selector_instance.score_history[0] == 8.5
    
    def test_scaler_fitting_after_two_samples(self, selector_instance):
        """Test that scaler is fitted after two samples."""
        features1 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        features2 = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        
        selector_instance.update_model(features1, 'detailed', 7.0)
        selector_instance.update_model(features2, 'concise', 8.0)
        
        assert selector_instance.is_scaler_fitted is True
        assert selector_instance.sample_count == 2
    
    def test_multiple_updates(self, selector_instance):
        """Test multiple sequential updates."""
        for i in range(10):
            features = np.random.rand(14)
            prompt = selector_instance.prompt_names[i % 3]
            score = 5.0 + np.random.rand() * 5
            selector_instance.update_model(features, prompt, score)
        
        assert selector_instance.sample_count == 10
        assert len(selector_instance.feature_history) == 10
    
    def test_model_reinitialization_on_failure(self, selector_instance):
        """Test model reinitialization when partial_fit fails."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        selector_instance.feature_history = [features]
        selector_instance.prompt_history = [0]
        selector_instance.score_history = [7.0]
        selector_instance.sample_count = 1
        
        with patch.object(selector_instance.model, 'partial_fit', side_effect=ValueError("Fit error")):
            selector_instance.update_model(features, 'detailed', 8.0)
            
            assert selector_instance.sample_count == 2
    
    def test_scaler_refit_on_transform_failure(self, selector_instance):
        """Test scaler refitting when transform fails."""
        features1 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        features2 = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
        
        selector_instance.update_model(features1, 'detailed', 7.0)
        selector_instance.update_model(features2, 'concise', 8.0)
        
        assert selector_instance.is_scaler_fitted
        
        with patch.object(selector_instance.scaler, 'transform', side_effect=ValueError("Transform error")):
            features3 = np.array([3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
            selector_instance.update_model(features3, 'security', 7.5)


class TestGenerateReview:
    """Tests for generate_review method."""
    
    def test_successful_review_generation(self, selector_instance, mock_dependencies):
        """Test successful review generation."""
        diff_text = "def foo():\n    pass"
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Great code review!")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']):
            
            review, elapsed, static, context = selector_instance.generate_review(diff_text, 'detailed')
            
            assert review == "Great code review!"
            assert isinstance(elapsed, float)
            assert static == "No issues found"
            assert "Best practice" in context
    
    def test_static_analysis_failure_handling(self, selector_instance, mock_dependencies):
        """Test handling of static analysis failure."""
        diff_text = "def foo():\n    pass"
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.run_static_analysis', side_effect=ValueError("Static analysis error")), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']):
            
            review, elapsed, static, context = selector_instance.generate_review(diff_text, 'detailed')
            
            assert "Static analysis failed" in static
    
    def test_rag_retrieval_failure_handling(self, selector_instance, mock_dependencies):
        """Test handling of RAG retrieval failure."""
        diff_text = "def foo():\n    pass"
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['concise'].__or__ = Mock(return_value=mock_chain)
        selector_instance.retriever.invoke = Mock(side_effect=RuntimeError("RAG error"))
        
        with patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']):
            
            review, elapsed, static, context = selector_instance.generate_review(diff_text, 'concise')
            
            assert "RAG retrieval failed" in context
    
    def test_llm_invocation_failure_handling(self, selector_instance, mock_dependencies):
        """Test handling of LLM invocation failure."""
        diff_text = "def foo():\n    pass"
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(side_effect=RuntimeError("LLM error"))
        selector_instance.prompts['security'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']):
            
            review, elapsed, static, context = selector_instance.generate_review(diff_text, 'security')
            
            assert "LLM invocation failed" in review
    
    def test_truncation_applied(self, selector_instance, mock_dependencies):
        """Test that truncation is applied to inputs."""
        diff_text = "x" * 10000
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']) as mock_truncate:
            
            selector_instance.generate_review(diff_text, 'detailed')
            
            assert mock_truncate.call_count >= 3


class TestEvaluateReview:
    """Tests for evaluate_review method."""
    
    def test_successful_evaluation(self, selector_instance, mock_dependencies):
        """Test successful review evaluation."""
        diff = "def foo(): pass"
        review = "Good code structure. Consider adding docstrings."
        static = "No issues"
        context = "Best practices"
        
        with patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']):
            
            score, heur, meta = selector_instance.evaluate_review(diff, review, static, context)
            
            assert isinstance(score, (int, float))
            assert 0 <= score <= 10
            assert isinstance(heur, dict)
            assert isinstance(meta, dict)
    
    def test_evaluation_with_meta_error(self, selector_instance, mock_dependencies):
        """Test evaluation when meta-evaluation returns error."""
        with patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', return_value=({'error': 'Failed'}, "")):
            
            score, heur, meta = selector_instance.evaluate_review("diff", "review", "static", "context")
            
            assert score == 5.0
    
    def test_evaluation_score_calculation(self, selector_instance, mock_dependencies):
        """Test score calculation logic."""
        heur_data = {
            'sections_presence': {'summary': True, 'issues': True, 'suggestions': True},
            'bullet_points': 8,
            'length_words': 150,
            'mentions_bug': True,
            'mentions_suggest': True
        }
        meta_data = {
            'clarity': 9,
            'usefulness': 8,
            'depth': 7,
            'actionability': 8,
            'positivity': 6
        }
        
        with patch('iterative_prompt_selector.heuristic_metrics', return_value=heur_data), \
             patch('iterative_prompt_selector.meta_evaluate', return_value=(meta_data, "text")):
            
            score, _, _ = selector_instance.evaluate_review("diff", "review", "static", "context")
            
            assert isinstance(score, float)
            assert score > 0
    
    def test_evaluation_with_short_review(self, selector_instance, mock_dependencies):
        """Test evaluation with very short review."""
        heur_data = {
            'sections_presence': {},
            'bullet_points': 0,
            'length_words': 20,
            'mentions_bug': False,
            'mentions_suggest': False
        }
        
        with patch('iterative_prompt_selector.heuristic_metrics', return_value=heur_data), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']):
            
            score, _, _ = selector_instance.evaluate_review("diff", "short review", "static", "context")
            
            assert isinstance(score, float)
    
    def test_evaluation_with_long_review(self, selector_instance, mock_dependencies):
        """Test evaluation with very long review."""
        heur_data = {
            'sections_presence': {'summary': True, 'issues': True},
            'bullet_points': 15,
            'length_words': 1500,
            'mentions_bug': True,
            'mentions_suggest': True
        }
        
        with patch('iterative_prompt_selector.heuristic_metrics', return_value=heur_data), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']):
            
            score, _, _ = selector_instance.evaluate_review("diff", "x" * 10000, "static", "context")
            
            assert isinstance(score, float)


class TestSaveState:
    """Tests for save_state method."""
    
    def test_save_state_success(self, selector_instance):
        """Test successful state save."""
        selector_instance.feature_history = [np.array([1, 2, 3])]
        selector_instance.prompt_history = [0]
        selector_instance.score_history = [7.5]
        selector_instance.sample_count = 1
        
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            result = selector_instance.save_state('test_state.json')
            
            assert result is True
            mock_file.assert_called_once()
    
    def test_save_state_with_fitted_model(self, selector_instance):
        """Test save state with fitted model."""
        selector_instance.model.coef_ = np.array([0.1, 0.2, 0.3])
        selector_instance.model.intercept_ = np.array([0.5])
        selector_instance.is_scaler_fitted = True
        selector_instance.scaler.mean_ = np.array([1, 2, 3])
        selector_instance.scaler.scale_ = np.array([0.5, 0.5, 0.5])
        
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            result = selector_instance.save_state('test_state.json')
            
            assert result is True
    
    def test_save_state_io_error(self, selector_instance):
        """Test save state handles IO error."""
        with patch('builtins.open', side_effect=IOError("Write error")):
            result = selector_instance.save_state('test_state.json')
            
            assert result is False
    
    def test_save_state_with_empty_history(self, selector_instance):
        """Test save state with no training history."""
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            result = selector_instance.save_state('test_state.json')
            
            assert result is True


class TestLoadState:
    """Tests for load_state method."""
    
    def test_load_state_file_not_found(self, selector_instance):
        """Test load state when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = selector_instance.load_state('nonexistent.json')
            
            assert result is False
    
    def test_load_state_success(self, selector_instance):
        """Test successful state load."""
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': False
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True
            assert selector_instance.sample_count >= 1
    
    def test_load_state_with_scaler(self, selector_instance):
        """Test load state with fitted scaler."""
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': True,
            'scaler_mean': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            'scaler_scale': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True
            assert selector_instance.is_scaler_fitted is True
    
    def test_load_state_with_model_weights(self, selector_instance):
        """Test load state with model weights."""
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': False,
            'model_coef': [0.1, 0.2, 0.3],
            'model_intercept': [0.5]
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True
    
    def test_load_state_combines_with_existing(self, selector_instance):
        """Test that load state combines with existing data."""
        # Add some existing data
        existing_features = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23])
        selector_instance.feature_history = [existing_features]
        selector_instance.prompt_history = [1]
        selector_instance.score_history = [9.0]
        selector_instance.sample_count = 1
        
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': False
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True
            assert selector_instance.sample_count == 2
    
    def test_load_state_avoids_duplicates(self, selector_instance):
        """Test that load state doesn't add duplicate samples."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        selector_instance.feature_history = [features]
        selector_instance.prompt_history = [0]
        selector_instance.score_history = [8.0]
        selector_instance.sample_count = 1
        
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': False
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True
            assert selector_instance.sample_count == 1
    
    def test_load_state_invalid_json(self, selector_instance):
        """Test load state with invalid JSON."""
        mock_file = mock_open(read_data="invalid json{{{")
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is False
    
    def test_load_state_corrupted_scaler_data(self, selector_instance):
        """Test load state with corrupted scaler data."""
        saved_state = {
            'feature_history': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]],
            'prompt_history': [0],
            'score_history': [8.0],
            'sample_count': 1,
            'is_scaler_fitted': True,
            'scaler_mean': "corrupted",
            'scaler_scale': None
        }
        
        mock_file = mock_open(read_data=json.dumps(saved_state))
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file):
            result = selector_instance.load_state('test_state.json')
            
            assert result is True


class TestProcessPR:
    """Tests for process_pr method."""
    
    def test_process_pr_success(self, selector_instance, mock_dependencies):
        """Test successful PR processing."""
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']), \
             patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
             patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
             patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
             patch('iterative_prompt_selector.post_review_comment', mock_dependencies['post_review_comment']):
            
            result = selector_instance.process_pr(123, post_to_github=False)
            
            assert result['pr_number'] == 123
            assert result['selected_prompt'] in selector_instance.prompt_names
            assert result['score'] > 0
    
    def test_process_pr_posts_to_github(self, selector_instance, mock_dependencies):
        """Test PR processing posts to GitHub."""
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']), \
             patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
             patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
             patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
             patch('iterative_prompt_selector.post_review_comment', mock_dependencies['post_review_comment']) as mock_post:
            
            result = selector_instance.process_pr(123, post_to_github=True)
            
            mock_post.assert_called_once()
            assert result['pr_number'] == 123
    
    def test_process_pr_github_post_failure(self, selector_instance, mock_dependencies):
        """Test PR processing handles GitHub post failure."""
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']), \
             patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
             patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
             patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
             patch('iterative_prompt_selector.post_review_comment', side_effect=ValueError("Post failed")):
            
            result = selector_instance.process_pr(123, post_to_github=True)
            
            assert result['pr_number'] == 123
    
    def test_process_pr_fetch_diff_failure(self, selector_instance):
        """Test PR processing handles diff fetch failure."""
        with patch('iterative_prompt_selector.fetch_pr_diff', side_effect=RuntimeError("Fetch failed")):
            result = selector_instance.process_pr(123)
            
            assert result['pr_number'] == 123
            assert result['selected_prompt'] is None
            assert result['score'] == 0
    
    def test_process_pr_saves_state_periodically(self, selector_instance, mock_dependencies):
        """Test that PR processing saves state periodically."""
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        selector_instance.sample_count = 2
        
        with patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']), \
             patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
             patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
             patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
             patch('iterative_prompt_selector.post_review_comment', mock_dependencies['post_review_comment']), \
             patch.object(selector_instance, 'save_state') as mock_save_state:
            
            selector_instance.process_pr(123, post_to_github=False)
            
            mock_save_state.assert_called_once()
    
    def test_process_pr_with_custom_params(self, selector_instance, mock_dependencies):
        """Test PR processing with custom owner/repo/token."""
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="Review text")
        selector_instance.prompts['detailed'].__or__ = Mock(return_value=mock_chain)
        
        with patch('iterative_prompt_selector.fetch_pr_diff', mock_dependencies['fetch_pr_diff']) as mock_fetch, \
             patch('iterative_prompt_selector.run_static_analysis', mock_dependencies['run_static_analysis']), \
             patch('iterative_prompt_selector.safe_truncate', mock_dependencies['safe_truncate']), \
             patch('iterative_prompt_selector.heuristic_metrics', mock_dependencies['heuristic_metrics']), \
             patch('iterative_prompt_selector.meta_evaluate', mock_dependencies['meta_evaluate']), \
             patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']), \
             patch('iterative_prompt_selector.post_review_comment', mock_dependencies['post_review_comment']):
            
            result = selector_instance.process_pr(
                456,
                owner='custom-owner',
                repo='custom-repo',
                token='custom-token',
                post_to_github=False
            )
            
            mock_fetch.assert_called_with('custom-owner', 'custom-repo', 456, 'custom-token')


class TestSaveResults:
    """Tests for save_results method."""
    
    def test_save_results_success(self, selector_instance, mock_dependencies):
        """Test successful results save."""
        features = {'num_lines': 100, 'num_files': 2}
        heur = {'sections_presence': {}, 'bullet_points': 5}
        meta = {'clarity': 8}
        
        with patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']) as mock_save:
            selector_instance.save_results(
                123,
                features,
                'detailed',
                'Review text',
                8.5,
                heur,
                meta,
                'Static output',
                'RAG context'
            )
            
            assert mock_save.call_count == 2
    
    def test_save_results_creates_proper_filenames(self, selector_instance, mock_dependencies):
        """Test that save_results creates proper filenames."""
        with patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']) as mock_save:
            selector_instance.save_results(
                999,
                {},
                'security focused',
                'Review',
                7.0,
                {},
                {},
                'Static',
                'Context'
            )
            
            calls = mock_save.call_args_list
            json_filename = calls[0][0][0]
            md_filename = calls[1][0][0]
            
            assert 'pr999' in json_filename
            assert json_filename.endswith('.json')
            assert 'pr999' in md_filename
            assert md_filename.endswith('.md')
    
    def test_save_results_includes_all_data(self, selector_instance, mock_dependencies):
        """Test that saved results include all required data."""
        with patch('iterative_prompt_selector.save_text_to_file', mock_dependencies['save_text_to_file']) as mock_save:
            selector_instance.save_results(
                123,
                {'num_lines': 50},
                'detailed',
                'Review text',
                8.0,
                {'bullet_points': 3},
                {'clarity': 9},
                'Static analysis',
                'RAG context'
            )
            
            json_content = mock_save.call_args_list[0][0][1]
            data = json.loads(json_content)
            
            assert 'pr_number' in data
            assert 'selected_prompt' in data
            assert 'review_score' in data
            assert 'static_output' in data
            assert 'retrieved_context' in data


class TestGetStats:
    """Tests for get_stats method."""
    
    def test_get_stats_empty_history(self, selector_instance):
        """Test get_stats with no training history."""
        stats = selector_instance.get_stats()
        
        assert stats['training_samples'] == 0
        assert stats['average_score'] == 0
        assert stats['unique_prompts_used'] == 0
    
    def test_get_stats_with_data(self, selector_instance):
        """Test get_stats with training data."""
        selector_instance.feature_history = [np.array([1]*14), np.array([2]*14)]
        selector_instance.prompt_history = [0, 1]
        selector_instance.score_history = [7.0, 8.5]
        selector_instance.sample_count = 2
        
        stats = selector_instance.get_stats()
        
        assert stats['training_samples'] == 2
        assert stats['average_score'] == 7.75
        assert stats['unique_prompts_used'] == 2
    
    def test_get_stats_prompt_distribution(self, selector_instance):
        """Test prompt distribution calculation."""
        selector_instance.prompt_history = [0, 0, 1, 2, 1]
        selector_instance.sample_count = 5
        selector_instance.score_history = [7, 8, 6, 9, 7]
        
        stats = selector_instance.get_stats()
        
        dist = stats['prompt_distribution']
        assert dist['detailed'] == 2
        assert dist['concise'] == 2
        assert dist['security'] == 1
    
    def test_get_stats_scaler_status(self, selector_instance):
        """Test scaler fitted status in stats."""
        selector_instance.is_scaler_fitted = True
        
        stats = selector_instance.get_stats()
        
        assert stats['is_scaler_fitted'] is True


class TestRunIterativeSelector:
    """Tests for run_iterative_selector function."""
    
    def test_run_iterative_selector_single_pr(self, mock_dependencies):
        """Test run_iterative_selector with single PR."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class:
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(return_value={
                'pr_number': 123,
                'selected_prompt': 'detailed',
                'score': 8.0
            })
            mock_selector.get_stats = Mock(return_value={'training_samples': 1})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            results, selector = run_iterative_selector([123], load_previous=False, post_to_github=False)
            
            assert len(results) == 1
            assert results[0]['pr_number'] == 123
    
    def test_run_iterative_selector_multiple_prs(self, mock_dependencies):
        """Test run_iterative_selector with multiple PRs."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class:
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(side_effect=[
                {'pr_number': 1, 'selected_prompt': 'detailed', 'score': 8.0},
                {'pr_number': 2, 'selected_prompt': 'concise', 'score': 7.5},
                {'pr_number': 3, 'selected_prompt': 'security', 'score': 9.0}
            ])
            mock_selector.get_stats = Mock(return_value={'training_samples': 3})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            results, selector = run_iterative_selector([1, 2, 3], post_to_github=False)
            
            assert len(results) == 3
    
    def test_run_iterative_selector_loads_previous_state(self, mock_dependencies):
        """Test run_iterative_selector loads previous state."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class:
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(return_value={
                'pr_number': 1,
                'selected_prompt': 'dummy',
                'score': 8.0
            })
            mock_selector.get_stats = Mock(return_value={})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            run_iterative_selector([1], load_previous=True, post_to_github=False)
            
            mock_selector.load_state.assert_called_once()
    
    def test_run_iterative_selector_periodic_saves(self, mock_dependencies):
        """Test run_iterative_selector performs periodic saves."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class, \
             patch('time.sleep'):
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(side_effect=[
                {'pr_number': 1, 'selected_prompt': 'dummy', 'score': 8.0},
                {'pr_number': 2, 'selected_prompt': 'dummy', 'score': 7.5}
            ])
            mock_selector.get_stats = Mock(return_value={})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            run_iterative_selector([1, 2], save_frequency=2, post_to_github=False)
            
            # Should save once after processing both PRs, plus final save
            assert mock_selector.save_state.call_count >= 1
    
    def test_run_iterative_selector_handles_pr_failure(self, mock_dependencies):
        """Test run_iterative_selector continues after PR failure."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class, \
             patch('time.sleep'):
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(side_effect=[
                RuntimeError("PR 1 failed"),
                {'pr_number': 2, 'selected_prompt': 'dummy', 'score': 8.0}
            ])
            mock_selector.get_stats = Mock(return_value={})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            results, selector = run_iterative_selector([1, 2], post_to_github=False)
            
            assert len(results) == 1
            assert results[0]['pr_number'] == 2
    
    def test_run_iterative_selector_final_save(self, mock_dependencies):
        """Test run_iterative_selector performs final save."""
        with patch('iterative_prompt_selector.get_prompts', mock_dependencies['get_prompts']), \
             patch('iterative_prompt_selector.get_retriever', mock_dependencies['get_retriever']), \
             patch('iterative_prompt_selector.IterativePromptSelector') as mock_selector_class, \
             patch('time.sleep'):
            
            mock_selector = Mock()
            mock_selector.process_pr = Mock(return_value={
                'pr_number': 1,
                'selected_prompt': 'dummy',
                'score': 8.0
            })
            mock_selector.get_stats = Mock(return_value={'training_samples': 1})
            mock_selector.load_state = Mock()
            mock_selector.save_state = Mock()
            mock_selector_class.return_value = mock_selector
            
            from iterative_prompt_selector import run_iterative_selector
            run_iterative_selector([1], post_to_github=False)
            
            # Should save at least once (final save)
            assert mock_selector.save_state.called


class TestEdgeCasesAndBoundaries:
    """Tests for edge cases and boundary conditions."""
    
    def test_very_large_diff(self, selector_instance):
        """Test handling of very large diff."""
        large_diff = "\n".join([f"+line{i}" for i in range(100000)])
        features = selector_instance.extract_pr_features(large_diff)
        
        assert features['num_lines'] == 100000
        assert features['additions'] == 100000
    
    def test_diff_with_special_characters(self, selector_instance):
        """Test handling of diff with special characters."""
        diff = "diff --git a/file.py b/file.py\n+line with unicode: 你好世界 🌍\n-old line"
        features = selector_instance.extract_pr_features(diff)
        
        assert features['num_files'] == 1
        assert features['additions'] >= 1
    
    def test_zero_features_vector(self, selector_instance):
        """Test handling of zero features vector."""
        vector = np.zeros(14)
        prompt = selector_instance.select_best_prompt(vector)
        
        assert prompt in selector_instance.prompt_names
    
    def test_negative_score_update(self, selector_instance):
        """Test model update with negative score."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        selector_instance.update_model(features, 'detailed', -5.0)
        
        assert selector_instance.score_history[0] == -5.0
    
    def test_very_high_score_update(self, selector_instance):
        """Test model update with very high score."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        selector_instance.update_model(features, 'concise', 100.0)
        
        assert selector_instance.score_history[0] == 100.0
    
    def test_nan_in_features(self, selector_instance):
        """Test handling of NaN in features."""
        features = np.array([np.nan, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        # Should not crash
        prompt = selector_instance.select_best_prompt(features)
        assert prompt in selector_instance.prompt_names
    
    def test_empty_prompt_name(self, selector_instance):
        """Test update with empty prompt name raises error."""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        with pytest.raises(ValueError):
            selector_instance.update_model(features, '', 7.0)
    
    def test_concurrent_updates_simulation(self, selector_instance):
        """Test multiple rapid updates."""
        for i in range(100):
            features = np.random.rand(14)
            prompt = selector_instance.prompt_names[i % 3]
            score = 5 + np.random.rand() * 5
            selector_instance.update_model(features, prompt, score)
        
        assert selector_instance.sample_count == 100
        assert len(selector_instance.feature_history) == 100

