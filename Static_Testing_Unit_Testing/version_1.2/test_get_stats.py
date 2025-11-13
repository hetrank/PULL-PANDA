"""
Test suite for get_stats method.
Tests statistics computation and output structure.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import patch
from iterative_prompt_selector import IterativePromptSelector


class TestGetStats(unittest.TestCase):
    """Tests for get_stats method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()

    def test_get_stats_empty_histories(self):
        """Test stats returned correctly when no training has occurred"""

        # Arrange
        self.selector.feature_history = []
        self.selector.score_history = []
        self.selector.prompt_history = []
        self.selector.prompt_names = ["p1", "p2", "p3"]
        self.selector.is_trained = False

        # Act
        stats = self.selector.get_stats()

        # Assert structure and default values
        self.assertEqual(stats["training_samples"], 0)
        self.assertFalse(stats["is_trained"])
        self.assertEqual(stats["average_score"], 0)

        expected_dist = {"p1": 0, "p2": 0, "p3": 0}
        self.assertEqual(stats["prompt_distribution"], expected_dist)

    def test_get_stats_with_data(self):
        """Test stats computed correctly with populated history"""

        # Arrange
        self.selector.feature_history = [1, 2, 3, 4]
        self.selector.score_history = [5.0, 7.0, 9.0]
        self.selector.prompt_history = [0, 2, 2, 1, 0]   # index into prompt_names
        self.selector.prompt_names = ["promptA", "promptB", "promptC"]
        self.selector.is_trained = True

        # Act
        stats = self.selector.get_stats()

        # Assert training sample count
        self.assertEqual(stats["training_samples"], 4)

        # Assert model state
        self.assertTrue(stats["is_trained"])

        # Assert average score
        self.assertAlmostEqual(stats["average_score"], np.mean([5.0, 7.0, 9.0]))

        # Assert prompt distribution counts
        expected_dist = {
            "promptA": 2,   # history has two 0s
            "promptB": 1,   # one 1
            "promptC": 2    # two 2s
        }
        self.assertEqual(stats["prompt_distribution"], expected_dist)

    def test_get_stats_score_average_zero_safe(self):
        """Test that average_score is 0 when score_history is empty"""

        self.selector.score_history = []
        self.selector.prompt_history = []
        self.selector.prompt_names = []

        stats = self.selector.get_stats()
        self.assertEqual(stats["average_score"], 0)
