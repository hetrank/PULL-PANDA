"""
Test suite for features_to_vector method.
Tests conversion of feature dictionaries to numerical vectors.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestFeaturesToVector(unittest.TestCase):
    """Tests for features_to_vector method"""

    def setUp(self):
        self.selector = IterativePromptSelector()

    def test_features_to_vector_complete_features(self):
        """Test conversion with all features present"""
        features = {
            'num_lines': 100, 'num_files': 5, 'additions': 50,
            'deletions': 20, 'net_changes': 30, 'has_comments': 1,
            'has_functions': 1, 'has_imports': 1, 'has_test': 0,
            'has_docs': 1, 'has_config': 0, 'is_python': 1,
            'is_js': 0, 'is_java': 0
        }
        
        vector = self.selector.features_to_vector(features)
        
        self.assertIsInstance(vector, np.ndarray)
        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 100)  # num_lines
        self.assertEqual(vector[1], 5)    # num_files
        self.assertEqual(vector[-1], 0)   # is_java

    def test_features_to_vector_missing_features(self):
        """Test conversion with missing features (should default to 0)"""
        features = {'num_lines': 50}
        
        vector = self.selector.features_to_vector(features)
        
        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 50)
        # All other values should be 0
        self.assertTrue(all(v == 0 for v in vector[1:]))

    def test_features_to_vector_empty_dict(self):
        """Test conversion with empty features dict"""
        vector = self.selector.features_to_vector({})
        
        self.assertEqual(len(vector), 14)
        self.assertTrue(all(v == 0 for v in vector))

    def test_features_to_vector_extra_features(self):
        """Test that extra features are ignored"""
        features = {
            'num_lines': 10,
            'extra_feature': 999,
            'another_extra': 'should be ignored'
        }
        
        vector = self.selector.features_to_vector(features)
        
        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 10)


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