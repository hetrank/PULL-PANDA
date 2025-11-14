"""
Updated test suite for save_state method.
Each test is marked as KEEP, OBSOLETE, or REDUNDANT.
"""

import pytest
import json
import unittest
import numpy as np
from unittest.mock import patch, mock_open, MagicMock
from online_estimator_version import IterativePromptSelector


class TestSaveState(unittest.TestCase):

    def setUp(self):
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()

    # ------------------------------------------------------------
    # OBSOLETE — Updated to handle new fields & behavior
    # ------------------------------------------------------------
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_untrained(self, mock_file):
        """OBSOLETE: Updated to match new save_state fields"""

        # Arrange
        self.selector.is_scaler_fitted = False
        self.selector.sample_count = 2
        self.selector.feature_history = [np.array([1, 2]), np.array([3, 4])]
        self.selector.prompt_history = [0, 1]
        self.selector.score_history = [5.0, 7.5]

        result = self.selector.save_state("state.json")

        self.assertTrue(result)

        mock_file.assert_called_once_with("state.json", "w", encoding="utf-8")

        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written)

        self.assertEqual(data["feature_history"], [[1, 2], [3, 4]])
        self.assertEqual(data["prompt_history"], [0, 1])
        self.assertEqual(data["score_history"], [5.0, 7.5])
        self.assertEqual(data["sample_count"], 2)

        # New fields
        self.assertFalse(data["is_scaler_fitted"])
        self.assertIsNone(data["model_coef"])
        self.assertIsNone(data["model_intercept"])
        self.assertIsNone(data["scaler_mean"])
        self.assertIsNone(data["scaler_scale"])
        self.assertIn("timestamp", data)

    # ------------------------------------------------------------
    # OBSOLETE — Updated to match new trained model behavior
    # ------------------------------------------------------------
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_trained(self, mock_file):
        """OBSOLETE: Updated to match new save_state structure"""

        self.selector.is_scaler_fitted = True
        self.selector.sample_count = 1

        # Mock scaler
        self.selector.scaler.mean_ = np.array([0.5, 1.5])
        self.selector.scaler.scale_ = np.array([2.0, 4.0])

        # Mock model with coef/intercept
        self.selector.model.coef_ = np.array([[1.0, -1.0]])
        self.selector.model.intercept_ = np.array([0.25])

        self.selector.feature_history = [np.array([10, 20])]
        self.selector.prompt_history = [2]
        self.selector.score_history = [8.0]

        result = self.selector.save_state("trained_state.json")
        self.assertTrue(result)

        mock_file.assert_called_once_with("trained_state.json", "w", encoding="utf-8")

        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written)

        self.assertEqual(data["feature_history"], [[10, 20]])
        self.assertEqual(data["prompt_history"], [2])
        self.assertEqual(data["score_history"], [8.0])
        self.assertEqual(data["sample_count"], 1)

        self.assertEqual(data["scaler_mean"], [0.5, 1.5])
        self.assertEqual(data["scaler_scale"], [2.0, 4.0])
        self.assertEqual(data["model_coef"], [[1.0, -1.0]])
        self.assertEqual(data["model_intercept"], [0.25])

        self.assertIn("timestamp", data)

    # ------------------------------------------------------------
    # KEEP — still valid as-is
    # ------------------------------------------------------------
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_default_filename(self, mock_file):
        """KEEP: default filename behavior unchanged"""

        self.selector.feature_history = []
        self.selector.prompt_history = []
        self.selector.score_history = []

        self.selector.is_scaler_fitted = False
        self.selector.sample_count = 0

        self.selector.save_state()  # default name

        mock_file.assert_called_once_with(
            "selector_state.json", "w", encoding="utf-8"
        )

    # ------------------------------------------------------------
    # NEW TEST — save failure handling
    # ------------------------------------------------------------
    @patch("builtins.open", side_effect=IOError("disk error"))
    def test_save_state_error(self, mock_file):
        """NEW: verify save_state returns False on error"""

        result = self.selector.save_state("fail.json")
        self.assertFalse(result)

    # ------------------------------------------------------------
    # NEW TEST — timestamp validation
    # ------------------------------------------------------------
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_timestamp_format(self, mock_file):
        """NEW: verify timestamp is ISO format"""

        self.selector.save_state("file.json")

        handle = mock_file()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        data = json.loads(written)

        self.assertIn("timestamp", data)
        # crude check: ISO timestamps contain 'T'
        self.assertIn("T", data["timestamp"])
