"""
Updated test suite for get_stats.
Each test labeled KEEP / OBSOLETE / NEW.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import patch
from online_estimator_version import IterativePromptSelector


class TestGetStats(unittest.TestCase):

    def setUp(self):
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()


    # ============================================================
    # OBSOLETE — Updated for new stats structure
    # ============================================================
    def test_get_stats_empty_histories(self):
        """OBSOLETE: Updated to include new fields and remove is_trained"""

        # Arrange
        self.selector.feature_history = []
        self.selector.score_history = []
        self.selector.prompt_history = []
        self.selector.prompt_names = ["p1", "p2", "p3"]
        self.selector.sample_count = 0
        self.selector.is_scaler_fitted = False

        # Act
        stats = self.selector.get_stats()

        # Assert updated structure
        self.assertEqual(stats["training_samples"], 0)
        self.assertEqual(stats["average_score"], 0)

        expected_dist = {"p1": 0, "p2": 0, "p3": 0}
        self.assertEqual(stats["prompt_distribution"], expected_dist)

        # new fields
        self.assertEqual(stats["unique_prompts_used"], 0)
        self.assertFalse(stats["is_scaler_fitted"])


    # ============================================================
    # OBSOLETE — Updated to match new fields + sample_count
    # ============================================================
    def test_get_stats_with_data(self):
        """OBSOLETE: Updated for new stats"""

        # Arrange
        self.selector.feature_history = [1, 2, 3, 4]
        self.selector.score_history = [5.0, 7.0, 9.0]
        self.selector.prompt_history = [0, 2, 2, 1, 0]
        self.selector.prompt_names = ["promptA", "promptB", "promptC"]
        self.selector.sample_count = 4
        self.selector.is_scaler_fitted = True

        # Act
        stats = self.selector.get_stats()

        # Assert sample count now uses sample_count field
        self.assertEqual(stats["training_samples"], 4)

        # Assert average score
        self.assertAlmostEqual(stats["average_score"], np.mean([5.0, 7.0, 9.0]))

        expected_dist = {
            "promptA": 2,
            "promptB": 1,
            "promptC": 2
        }
        self.assertEqual(stats["prompt_distribution"], expected_dist)

        # new field: unique prompts used
        self.assertEqual(stats["unique_prompts_used"], 3)

        # new field
        self.assertTrue(stats["is_scaler_fitted"])


    # ============================================================
    # OBSOLETE — Updated to include new fields
    # ============================================================
    def test_get_stats_score_average_zero_safe(self):
        """OBSOLETE: updated to validate new fields"""

        self.selector.score_history = []
        self.selector.prompt_history = []
        self.selector.prompt_names = ["x"]
        self.selector.sample_count = 0
        self.selector.is_scaler_fitted = False

        stats = self.selector.get_stats()

        self.assertEqual(stats["average_score"], 0)
        self.assertEqual(stats["unique_prompts_used"], 0)
        self.assertFalse(stats["is_scaler_fitted"])


    # ============================================================
    # NEW — unique_prompts_used must reflect unique values
    # ============================================================
    def test_unique_prompts_used_counts_correctly(self):
        """NEW: ensure unique prompt count is correct"""

        self.selector.prompt_history = [0, 0, 1, 2, 2, 2]
        self.selector.sample_count = 6
        self.selector.prompt_names = ["A", "B", "C"]

        stats = self.selector.get_stats()

        # unique prompt indices present = {0,1,2} = 3
        self.assertEqual(stats["unique_prompts_used"], 3)


    # ============================================================
    # NEW — test is_scaler_fitted reported correctly
    # ============================================================
    def test_is_scaler_fitted_reflected_in_stats(self):
        """NEW: ensure scaler state is properly reported"""

        self.selector.is_scaler_fitted = True
        self.selector.sample_count = 0
        self.selector.prompt_history = []
        self.selector.prompt_names = []

        stats = self.selector.get_stats()
        self.assertTrue(stats["is_scaler_fitted"])
