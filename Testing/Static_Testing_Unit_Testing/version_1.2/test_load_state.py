"""
Test suite for load_state method.
Tests model state restoration and error handling.
"""

import pytest
import json
import unittest
import numpy as np
from unittest.mock import patch, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestLoadState(unittest.TestCase):
    """Tests for load_state method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()

    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_success_trained(self, mock_file):
        """Test loading a fully trained saved state"""

        mock_file_content = json.dumps({
            "feature_history": [[1, 2], [3, 4]],
            "prompt_history": [0, 1],
            "score_history": [5.0, 7.5],
            "is_trained": True,
            "scaler_mean": [0.5, 1.0],
            "scaler_scale": [2.0, 4.0]
        })

        mock_file.return_value.read.return_value = mock_file_content

        self.selector.load_state("custom_state.json")

        # Assert correct restoration
        self.assertEqual(len(self.selector.feature_history), 2)
        self.assertTrue(self.selector.is_trained)
        self.assertEqual(self.selector.prompt_history, [0, 1])
        self.assertEqual(self.selector.score_history, [5.0, 7.5])

        # Check correct numpy conversions
        self.assertTrue(np.array_equal(self.selector.feature_history[0], np.array([1, 2])))
        self.assertTrue(np.array_equal(self.selector.scaler.mean_, np.array([0.5, 1.0])))
        self.assertTrue(np.array_equal(self.selector.scaler.scale_, np.array([2.0, 4.0])))

        # Scaler must compute these fields
        self.assertEqual(self.selector.scaler.n_features_in_, 2)
        self.assertTrue(np.array_equal(self.selector.scaler.var_, np.array([4.0, 16.0])))

        # Assert correct filename
        mock_file.assert_called_once_with("custom_state.json", "r", encoding="utf-8")

    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_success_untrained(self, mock_file):
        """Test loading state where model is not trained"""

        mock_file_content = json.dumps({
            "feature_history": [[10, 20]],
            "prompt_history": [2],
            "score_history": [9.0],
            "is_trained": False,
            "scaler_mean": None,
            "scaler_scale": None
        })

        mock_file.return_value.read.return_value = mock_file_content

        self.selector.load_state("state_untrained.json")

        # Assert basic restored values
        self.assertFalse(self.selector.is_trained)
        self.assertEqual(self.selector.prompt_history, [2])
        self.assertEqual(self.selector.score_history, [9.0])

        # Feature history should be numpy arrays
        self.assertTrue(np.array_equal(self.selector.feature_history[0], np.array([10, 20])))

        # Scaler should not be restored
        self.assertFalse(hasattr(self.selector.scaler, "mean_"))

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_state_file_not_found(self, mock_file):
        """Test fallback when state file does not exist"""

        # Act (should not raise)
        self.selector.load_state("missing.json")

        # Should fall back to default empty state
        self.assertEqual(self.selector.feature_history, [])
        self.assertEqual(self.selector.prompt_history, [])
        self.assertEqual(self.selector.score_history, [])
        self.assertFalse(self.selector.is_trained)

    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_corrupted_json(self, mock_file):
        """Test fallback when JSON cannot be parsed"""

        mock_file.return_value.read.return_value = "{not valid json..."

        with patch("json.load", side_effect=json.JSONDecodeError("err", "doc", 1)):
            self.selector.load_state("bad.json")

        # Fallback state
        self.assertEqual(self.selector.feature_history, [])
        self.assertEqual(self.selector.prompt_history, [])
        self.assertEqual(self.selector.score_history, [])
        self.assertFalse(self.selector.is_trained)

    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_missing_keys(self, mock_file):
        """Test fallback when keys are missing in saved file"""

        # Missing score_history, prompt_history, etc.
        mock_file_content = json.dumps({
            "feature_history": [[1, 2]],
            # all other keys missing
        })
        mock_file.return_value.read.return_value = mock_file_content

        self.selector.load_state("incomplete.json")

        self.assertEqual(self.selector.feature_history, [])
        self.assertEqual(self.selector.prompt_history, [])
        self.assertEqual(self.selector.score_history, [])
        self.assertFalse(self.selector.is_trained)

    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_default_filename(self, mock_file):
        """Test that default filename is used if none provided"""

        mock_file.return_value.read.return_value = json.dumps({
            "feature_history": [],
            "prompt_history": [],
            "score_history": [],
            "is_trained": False,
            "scaler_mean": None,
            "scaler_scale": None
        })

        self.selector.load_state()  # should use default selector_state.json

        mock_file.assert_called_once_with("selector_state.json", "r", encoding="utf-8")
