"""
Test suite for select_best_prompt method.
Tests prompt selection logic with and without trained model.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestSelectBestPrompt(unittest.TestCase):
    """Tests for select_best_prompt method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts') as mock_get:
            mock_get.return_value = {
                'prompt1': Mock(), 'prompt2': Mock(), 'prompt3': Mock()
            }
            self.selector = IterativePromptSelector()

    def test_select_best_prompt_untrained_round_robin(self):
        """Test round-robin selection when model is not trained"""
        features = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
        
        # First call should return first prompt
        prompt1 = self.selector.select_best_prompt(features)
        self.assertEqual(prompt1, 'prompt1')
        
        # Add to history to move to next
        self.selector.feature_history.append(features)
        
        # Second call should return second prompt
        prompt2 = self.selector.select_best_prompt(features)
        self.assertEqual(prompt2, 'prompt2')

    def test_select_best_prompt_insufficient_data(self):
        """Test selection with insufficient training data"""
        self.selector.is_trained = True
        self.selector.feature_history = [np.zeros(14)] * 3  # Less than min
        
        features = np.zeros(14)
        prompt = self.selector.select_best_prompt(features)
        
        # Should still use round-robin
        self.assertIn(prompt, self.selector.prompt_names)

    def test_select_best_prompt_trained_model(self):
        """Test selection with trained model"""
        # Set up as trained
        self.selector.is_trained = True
        self.selector.feature_history = [np.zeros(14)] * 10
        
        # Mock model prediction
        self.selector.model.predict = Mock(return_value=np.array([5.0, 8.0, 6.0]))
        
        features = np.ones(14)
        prompt = self.selector.select_best_prompt(features)
        
        # Should select prompt with highest predicted score (prompt2, index 1)
        self.assertEqual(prompt, 'prompt2')
        self.selector.model.predict.assert_called_once()

    def test_select_best_prompt_model_prediction_failure(self):
        """Test fallback when model prediction fails"""
        self.selector.is_trained = True
        self.selector.feature_history = [np.zeros(14)] * 10
        self.selector.model.predict = Mock(side_effect=ValueError("Prediction error"))
        
        features = np.ones(14)
        prompt = self.selector.select_best_prompt(features)
        
        # Should fall back to first prompt
        self.assertEqual(prompt, 'prompt1')

    def test_select_best_prompt_index_error(self):
        """Test fallback when IndexError occurs"""
        self.selector.is_trained = True
        self.selector.feature_history = [np.zeros(14)] * 10
        self.selector.model.predict = Mock(side_effect=IndexError("Index error"))
        
        features = np.ones(14)
        prompt = self.selector.select_best_prompt(features)
        
        self.assertEqual(prompt, 'prompt1')
