"""
Updated test suite for load_state method.
Each test marked KEEP / OBSOLETE / REDUNDANT.
"""

import pytest
import json
import unittest
import numpy as np
from unittest.mock import patch, mock_open
from online_estimator_version import IterativePromptSelector


class TestLoadState(unittest.TestCase):

    def setUp(self):
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()


    # ============================================================
    # OBSOLETE — Updated version
    # ============================================================
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_success_trained(self, mock_file, mock_exists):
        """OBSOLETE: Updated to match new loader behavior."""

        mock_file_content = json.dumps({
            "feature_history": [[1, 2], [3, 4]],
            "prompt_history": [0, 1],
            "score_history": [5.0, 7.5],
            "sample_count": 2,
            "is_scaler_fitted": True,
            "scaler_mean": [0.5, 1.0],
            "scaler_scale": [2.0, 4.0],
            "model_coef": [[1.0, -1.0]],
            "model_intercept": [0.25]
        })

        mock_file.return_value.read.return_value = mock_file_content

        result = self.selector.load_state("custom_state.json")
        self.assertTrue(result)

        # data combined into empty state => simply loaded
        self.assertEqual(len(self.selector.feature_history), 2)
        self.assertEqual(self.selector.prompt_history, [0, 1])
        self.assertEqual(self.selector.score_history, [5.0, 7.5])

        # scaler restored
        self.assertTrue(self.selector.is_scaler_fitted)
        self.assertTrue(np.array_equal(self.selector.scaler.mean_, np.array([0.5, 1.0])))
        self.assertTrue(np.array_equal(self.selector.scaler.scale_, np.array([2.0, 4.0])))

        # model weights restored
        self.assertTrue(np.array_equal(self.selector.model.coef_, np.array([[1.0, -1.0]])))
        self.assertTrue(np.array_equal(self.selector.model.intercept_, np.array([0.25])))


    # ============================================================
    # OBSOLETE — Updated version
    # ============================================================
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_success_untrained(self, mock_file, mock_exists):
        """OBSOLETE: Updated to new untrained behavior."""

        mock_file_content = json.dumps({
            "feature_history": [[10, 20]],
            "prompt_history": [2],
            "score_history": [9.0],
            "is_scaler_fitted": False,
            "scaler_mean": None,
            "scaler_scale": None
        })

        mock_file.return_value.read.return_value = mock_file_content

        result = self.selector.load_state("state_untrained.json")
        self.assertTrue(result)

        self.assertEqual(self.selector.prompt_history, [2])
        self.assertEqual(self.selector.score_history, [9.0])
        self.assertTrue(np.array_equal(self.selector.feature_history[0], np.array([10, 20])))

        # scaler should not be restored
        self.assertFalse(self.selector.is_scaler_fitted)


    # ============================================================
    # OBSOLETE — Updated due to changed behavior (no reset, return False)
    # ============================================================
    @patch("os.path.exists", return_value=False)
    def test_load_state_file_not_found(self, mock_exists):
        """OBSOLETE: Updated to check return value only."""

        result = self.selector.load_state("missing.json")
        self.assertFalse(result)

        # content stays unchanged (empty initial state)
        self.assertEqual(self.selector.feature_history, [])


    # ============================================================
    # OBSOLETE — Updated: now returns False, does not clear state
    # ============================================================
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_corrupted_json(self, mock_file, mock_exists):
        """OBSOLETE: Updated for new error handling."""

        mock_file.return_value.read.return_value = "{bad json..."
        with patch("json.load", side_effect=json.JSONDecodeError("err", "doc", 1)):
            result = self.selector.load_state("bad.json")

        self.assertFalse(result)
        # internal state unchanged
        self.assertEqual(self.selector.feature_history, [])


    # ============================================================
    # REDUNDANT — kept for history but no longer applies
    # ============================================================
    @unittest.skip("REDUNDANT: load_state no longer resets state or enforces required keys.")
    def test_load_state_missing_keys(self):
        pass


    # ============================================================
    # KEEP — still correct
    # ============================================================
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_default_filename(self, mock_file, mock_exists):
        """KEEP: default filename behavior unchanged"""

        mock_file.return_value.read.return_value = json.dumps({
            "feature_history": [],
            "prompt_history": [],
            "score_history": []
        })

        self.selector.load_state()  # should use selector_state.json
        mock_file.assert_called_once_with("selector_state.json", "r", encoding="utf-8")


    # ============================================================
    # NEW — ensure combining logic works
    # ============================================================
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_combines_history(self, mock_file, mock_exists):
        """NEW: saved + existing feature histories should merge without duplicates."""

        # existing data
        self.selector.feature_history = [np.array([1, 2])]
        self.selector.prompt_history = [0]
        self.selector.score_history = [5.0]
        self.selector.sample_count = 1

        saved = json.dumps({
            "feature_history": [[1, 2], [3, 4]],  # duplicate + new
            "prompt_history": [0, 1],
            "score_history": [5.0, 7.5]
        })

        mock_file.return_value.read.return_value = saved

        result = self.selector.load_state("state.json")
        self.assertTrue(result)

        # 1 duplicate + 1 new → total = 2
        self.assertEqual(len(self.selector.feature_history), 2)
        self.assertIn(1, self.selector.prompt_history)
        self.assertIn(7.5, self.selector.score_history)
