"""
Updated test suite for features_to_vector method.

Matches structure:
- unittest.TestCase
- setUp with patched get_prompts
- class-level usage of self.selector
"""

import unittest
import numpy as np
from unittest.mock import patch
from online_estimator_version import IterativePromptSelector


class TestFeaturesToVector(unittest.TestCase):
    """Tests for features_to_vector method."""

    def setUp(self):
        # Same setup structure used across all rewritten suites
        with patch("online_estimator_version.get_prompts"):
            self.selector = IterativePromptSelector()

    # ============================================================
    # COMPLETE FEATURES → CORRECT VECTOR
    # ============================================================
    def test_complete_features_conversion(self):
        features = {
            "num_lines": 100,
            "num_files": 5,
            "additions": 50,
            "deletions": 20,
            "net_changes": 30,
            "has_comments": 1,
            "has_functions": 1,
            "has_imports": 1,
            "has_test": 0,
            "has_docs": 0,
            "has_config": 0,
            "is_python": 1,
            "is_js": 0,
            "is_java": 0,
        }

        vector = self.selector.features_to_vector(features)

        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 100)
        self.assertEqual(vector[1], 5)
        self.assertIsInstance(vector, np.ndarray)

    # ============================================================
    # MISSING FEATURES DEFAULT TO ZERO
    # ============================================================
    def test_missing_features_default_to_zero(self):
        features = {"num_lines": 50}
        vector = self.selector.features_to_vector(features)

        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 50)
        self.assertEqual(vector[1], 0)
        self.assertEqual(np.sum(vector[2:]), 0)

    # ============================================================
    # EMPTY FEATURE DICT
    # ============================================================
    def test_empty_features_dict(self):
        vector = self.selector.features_to_vector({})

        self.assertEqual(len(vector), 14)
        self.assertTrue(np.all(vector == 0))

    # ============================================================
    # EXTRA FEATURES IGNORED
    # ============================================================
    def test_extra_features_ignored(self):
        features = {
            "num_lines": 10,
            "extra_feature": 999,
            "another_extra": "ignored",
        }

        vector = self.selector.features_to_vector(features)

        self.assertEqual(len(vector), 14)
        self.assertEqual(vector[0], 10)
