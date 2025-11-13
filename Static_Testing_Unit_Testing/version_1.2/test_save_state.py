"""
Test suite for save_state method.
Tests serialization of model learning state.
"""

import pytest
import json
import unittest
import numpy as np
from unittest.mock import patch, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestSaveState(unittest.TestCase):
    """Tests for save_state method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()

    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_untrained(self, mock_file):
        """Test state saving when model is not trained"""

        # Arrange (untrained scenario)
        self.selector.is_trained = False
        self.selector.feature_history = [np.array([1, 2]), np.array([3, 4])]
        self.selector.prompt_history = [0, 1]
        self.selector.score_history = [5.0, 7.5]

        # Act
        self.selector.save_state("state.json")

        # Assert file opened with filename
        mock_file.assert_called_once_with("state.json", "w", encoding="utf-8")

        # Extract JSON written
        handle = mock_file()
        written = "".join(
            call.args[0] for call in handle.write.call_args_list if call.args
        )
        data = json.loads(written)

        # Assert state structure
        self.assertEqual(data["feature_history"], [[1, 2], [3, 4]])
        self.assertEqual(data["prompt_history"], [0, 1])
        self.assertEqual(data["score_history"], [5.0, 7.5])
        self.assertFalse(data["is_trained"])

        # Scaler should be None because model not trained
        self.assertIsNone(data["scaler_mean"])
        self.assertIsNone(data["scaler_scale"])

    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_trained(self, mock_file):
        """Test state saving when model is trained and scaler exists"""

        # Arrange (trained scenario)
        self.selector.is_trained = True

        # Fake scaler setup
        self.selector.scaler.mean_ = np.array([0.5, 1.5])
        self.selector.scaler.scale_ = np.array([2.0, 4.0])

        self.selector.feature_history = [np.array([10, 20])]
        self.selector.prompt_history = [2]
        self.selector.score_history = [8.0]

        # Act
        self.selector.save_state("trained_state.json")

        # Assert filename
        mock_file.assert_called_once_with("trained_state.json", "w", encoding="utf-8")

        # Extract JSON written
        handle = mock_file()
        written = "".join(
            call.args[0] for call in handle.write.call_args_list if call.args
        )
        data = json.loads(written)

        # Assert fields
        self.assertEqual(data["feature_history"], [[10, 20]])
        self.assertEqual(data["prompt_history"], [2])
        self.assertEqual(data["score_history"], [8.0])

        self.assertTrue(data["is_trained"])
        self.assertEqual(data["scaler_mean"], [0.5, 1.5])
        self.assertEqual(data["scaler_scale"], [2.0, 4.0])

    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_default_filename(self, mock_file):
        """Test the default filename is used when none is provided"""

        self.selector.feature_history = []
        self.selector.prompt_history = []
        self.selector.score_history = []

        self.selector.is_trained = False

        self.selector.save_state()  # should use default "selector_state.json"

        mock_file.assert_called_once_with(
            "selector_state.json", "w", encoding="utf-8"
        )
