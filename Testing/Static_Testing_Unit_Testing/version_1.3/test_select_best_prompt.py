import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from online_estimator_version import IterativePromptSelector


class TestSelectBestPrompt:
    """Test cases for select_best_prompt method with maximum coverage"""
    
    @pytest.fixture
    def selector(self):
        """Create a selector instance with mocked components"""
        selector = IterativePromptSelector.__new__(IterativePromptSelector)
        selector.prompt_names = ['prompt_a', 'prompt_b', 'prompt_c']
        selector.is_scaler_fitted = True
        selector.scaler = MagicMock()
        selector.model = MagicMock()
        return selector
    
    # ========== Early Exploration Phase ==========
    
    def test_first_sample_returns_first_prompt(self, selector):
        """Sample 0: Should return first prompt via round-robin"""
        selector.sample_count = 0
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_a'
    
    def test_second_sample_returns_second_prompt(self, selector):
        """Sample 1: Should return second prompt via round-robin"""
        selector.sample_count = 1
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'
    
    # ========== Scaler Behavior ==========
    
    def test_scaler_fitted_transforms_features(self, selector):
        """Scaler fitted: Should transform features"""
        selector.sample_count = 5
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.return_value = [0.7]
        
        selector.select_best_prompt([1.0, 2.0])
        
        selector.scaler.transform.assert_called_once_with([[1.0, 2.0]])
    
    def test_scaler_not_fitted_uses_raw_features(self, selector):
        """Scaler not fitted: Should use raw features"""
        selector.sample_count = 5
        selector.is_scaler_fitted = False
        selector.model.predict.return_value = [0.7]
        
        result = selector.select_best_prompt([1.0, 2.0])
        
        selector.scaler.transform.assert_not_called()
        assert result in selector.prompt_names
    
    def test_scaler_transform_error_fallback(self, selector):
        """Scaler throws error: Should fallback to raw features"""
        selector.sample_count = 5
        selector.scaler.transform.side_effect = ValueError("Transform failed")
        selector.model.predict.return_value = [0.7]
        
        result = selector.select_best_prompt([1.0, 2.0])
        
        assert result in selector.prompt_names  # Should not crash
    
    # ========== Model Prediction ==========
    
    def test_selects_highest_scoring_prompt(self, selector):
        """Should select prompt with highest predicted score"""
        selector.sample_count = 10
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        
        # prompt_a: 0.3, prompt_b: 0.9, prompt_c: 0.5
        selector.model.predict.side_effect = [
            [0.3],  # prompt_a
            [0.9],  # prompt_b (highest)
            [0.5]   # prompt_c
        ]
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'
    
    def test_handles_negative_scores(self, selector):
        """Should handle negative scores correctly"""
        selector.sample_count = 10
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        
        # All negative scores
        selector.model.predict.side_effect = [
            [-0.5],
            [-0.2],  # Highest (least negative)
            [-0.8]
        ]
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'
    
    def test_model_predict_partial_failure(self, selector):
        """Model fails on some prompts: Should skip and continue"""
        selector.sample_count = 10
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        
        def predict_side_effect(x):
            # Fail on second prompt, succeed on others
            prompt_idx = int(x[0][-1])
            if prompt_idx == 1:
                raise ValueError("Prediction failed")
            return [0.5 if prompt_idx == 0 else 0.8]
        
        selector.model.predict.side_effect = predict_side_effect
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_c'  # Should select prompt_c (0.8)
    
    def test_model_all_predictions_fail(self, selector):
        """All predictions fail: Should return first prompt"""
        selector.sample_count = 10
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = ValueError("Always fails")
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_a'  # Falls back to first prompt
    
    # ========== Exploration Phase ==========
    
    @patch('numpy.random.random')
    def test_exploration_phase_respects_threshold(self, mock_random, selector):
        """Exploration random > 0.3: Should use best prompt"""
        selector.sample_count = 4
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = [[0.3], [0.9], [0.5]]
        
        # Random above threshold - no exploration
        mock_random.return_value = 0.5
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'  # Best prompt, not exploration
    
    @patch('numpy.random.random')
    def test_post_exploration_always_uses_best(self, mock_random, selector):
        """After exploration phase: Should always use best prompt"""
        selector.sample_count = 10  # Beyond exploration (>= 6)
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = [[0.3], [0.9], [0.5]]
        
        # Even with low random, should not explore
        mock_random.return_value = 0.1
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'  # Always best, no exploration
    
    # ========== Feature Vector Edge Cases ==========
    
    def test_empty_feature_vector(self, selector):
        """Empty features: Should handle gracefully"""
        selector.sample_count = 5
        selector.scaler.transform.return_value = [[]]
        selector.model.predict.return_value = [0.5]
        
        result = selector.select_best_prompt([])
        assert result in selector.prompt_names
    
    def test_single_prompt_available(self, selector):
        """Only one prompt: Should always return it"""
        selector.prompt_names = ['only_prompt']
        selector.sample_count = 5
        selector.scaler.transform.return_value = [[0.5]]
        selector.model.predict.return_value = [0.5]
        
        result = selector.select_best_prompt([1.0])
        assert result == 'only_prompt'
    
    def test_identical_scores(self, selector):
        """All prompts have same score: Should return first"""
        selector.sample_count = 10
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = [[0.7], [0.7], [0.7]]
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_a'  # First prompt wins ties
    
    # ========== Boundary Conditions ==========
    
    @patch('numpy.random.random')
    def test_exploration_boundary_last_sample(self, mock_random, selector):
        """Sample 5 (last exploration): Should still allow exploration"""
        selector.sample_count = 5  # Last sample in exploration (< 6)
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = [[0.9], [0.3], [0.5]]
        
        mock_random.return_value = 0.2
        
        result = selector.select_best_prompt([1.0, 2.0])
        # Should explore (sample 5 < 6 = len(prompts) * 2)
        assert result == 'prompt_c'  # 5 % 3 = 2
    
    @patch('numpy.random.random')
    def test_exploration_boundary_first_non_exploration(self, mock_random, selector):
        """Sample 6: Should NOT explore"""
        selector.sample_count = 6  # First non-exploration sample
        selector.scaler.transform.return_value = [[0.5, 0.8]]
        selector.model.predict.side_effect = [[0.3], [0.9], [0.5]]
        
        mock_random.return_value = 0.1
        
        result = selector.select_best_prompt([1.0, 2.0])
        assert result == 'prompt_b'  # Always best, no exploration