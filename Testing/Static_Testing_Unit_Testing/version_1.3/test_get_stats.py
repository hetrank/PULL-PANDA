"""
Updated test suite for get_stats.

Matches structure used across all updated suites:
- unittest.TestCase
- setUp() with patched get_prompts
"""

import unittest
import numpy as np
from unittest.mock import patch
from online_estimator_version import IterativePromptSelector


class TestGetStats(unittest.TestCase):
    """Tests for get_stats method."""

    def setUp(self):
        # EXACT setup style matching TestProcessPR and others
        with patch("online_estimator_version.get_prompts"):
            self.selector = IterativePromptSelector()

    # ============================================================
    # EMPTY HISTORY
    # ============================================================
    def test_get_stats_empty_history(self):
        """Test get_stats with no training history."""

        stats = self.selector.get_stats()

        self.assertEqual(stats["training_samples"], 0)
        self.assertEqual(stats["average_score"], 0)
        self.assertEqual(stats["unique_prompts_used"], 0)

    # ============================================================
    # WITH TRAINING DATA
    # ============================================================
    def test_get_stats_with_data(self):
        """Test get_stats with training data."""

        self.selector.feature_history = [
            np.array([1] * 14),
            np.array([2] * 14),
        ]
        self.selector.prompt_history = [0, 1]
        self.selector.score_history = [7.0, 8.5]
        self.selector.sample_count = 2

        stats = self.selector.get_stats()

        self.assertEqual(stats["training_samples"], 2)
        self.assertEqual(stats["average_score"], 7.75)
        self.assertEqual(stats["unique_prompts_used"], 2)

    # ============================================================
    # PROMPT DISTRIBUTION
    # ============================================================
    def test_get_stats_prompt_distribution(self):
        """Test prompt distribution calculation."""

        self.selector.prompt_history = [0, 0, 1, 2, 1]
        self.selector.score_history = [7, 8, 6, 9, 7]
        self.selector.sample_count = 5

        stats = self.selector.get_stats()

        dist = stats["prompt_distribution"]

        self.assertEqual(dist["detailed"], 2)
        self.assertEqual(dist["concise"], 2)
        self.assertEqual(dist["security"], 1)

    # ============================================================
    # SCALER STATUS
    # ============================================================
    def test_get_stats_scaler_status(self):
        """Test scaler fitted status in stats."""

        self.selector.is_scaler_fitted = True

        stats = self.selector.get_stats()

        self.assertTrue(stats["is_scaler_fitted"])
