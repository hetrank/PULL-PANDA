"""
Test suite for features_to_vector method.
Tests conversion of feature dictionaries to numerical vectors.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from online_estimator_version import IterativePromptSelector


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
