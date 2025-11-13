"""
Test suite for update_model method.
Tests training logic, data accumulation, and error handling.
"""

import pytest
import unittest
import numpy as np
from unittest.mock import patch, MagicMock
from iterative_prompt_selector import IterativePromptSelector


class TestUpdateModel(unittest.TestCase):
    """Tests for update_model method"""

    def setUp(self):
        with patch("iterative_prompt_selector.get_prompts") as mock_prompts:
            mock_prompts.return_value = {"p1": MagicMock(), "p2": MagicMock()}
            self.selector = IterativePromptSelector()

    def test_update_model_appends_history(self):
        """Test that update_model correctly appends to history lists"""

        features = np.array([1.0, 2.0])
        score = 8.5
        prompt = "p1"

        self.selector.update_model(features, prompt, score)

        self.assertEqual(len(self.selector.feature_history), 1)
        self.assertTrue(np.array_equal(self.selector.feature_history[0], features))

        self.assertEqual(self.selector.prompt_history, [0])  # p1 index
        self.assertEqual(self.selector.score_history, [8.5])

    @patch("iterative_prompt_selector.RandomForestRegressor.fit")
    @patch("iterative_prompt_selector.StandardScaler.transform")
    @patch("iterative_prompt_selector.StandardScaler.fit")
    def test_update_model_trains_at_threshold(
        self, mock_scaler_fit, mock_scaler_transform, mock_model_fit
    ):
        """Test model starts training exactly when min_samples_for_training is met"""

        # Add samples below threshold
        for _ in range(self.selector.min_samples_for_training - 1):
            self.selector.update_model(np.array([1, 2]), "p1", 5.0)

        # Pre-training checks
        self.assertFalse(self.selector.is_trained)
        mock_scaler_fit.assert_not_called()
        mock_model_fit.assert_not_called()

        # Add the final sample to reach training point
        self.selector.update_model(np.array([1, 2]), "p1", 6.0)

        # Scaler should fit ONCE at first training
        mock_scaler_fit.assert_called_once()
        mock_scaler_transform.assert_called()
        mock_model_fit.assert_called()

        self.assertTrue(self.selector.is_trained)

    @patch("iterative_prompt_selector.RandomForestRegressor.fit")
    @patch("iterative_prompt_selector.StandardScaler.transform")
    @patch("iterative_prompt_selector.StandardScaler.fit")
    def test_update_model_retrain_after_threshold(
        self, mock_scaler_fit, mock_scaler_transform, mock_model_fit
    ):
        """Test that retraining occurs on additional samples but scaler.fit() does not repeat"""

        # Fill exactly threshold samples
        for _ in range(self.selector.min_samples_for_training):
            self.selector.update_model(np.array([0.5, 1.5]), "p1", 7.0)

        # First training happened — now add extra sample
        mock_scaler_fit.reset_mock()
        mock_model_fit.reset_mock()

        self.selector.update_model(np.array([2.0, 3.0]), "p2", 9.0)

        # scaler.fit() should NOT run again
        mock_scaler_fit.assert_not_called()

        # But scaler.transform + model.fit SHOULD run
        mock_scaler_transform.assert_called()
        mock_model_fit.assert_called()

    @patch("iterative_prompt_selector.RandomForestRegressor.fit", side_effect=ValueError("bad data"))
    @patch("iterative_prompt_selector.StandardScaler.transform")
    @patch("iterative_prompt_selector.StandardScaler.fit")
    def test_update_model_training_failure_sets_untrained(
        self, mock_scaler_fit, mock_scaler_transform, mock_model_fit
    ):
        """Test that training errors reset is_trained to False"""

        # Fill enough samples to trigger training
        for _ in range(self.selector.min_samples_for_training - 1):
            self.selector.update_model(np.array([1, 1]), "p1", 5.0)

        # Next update triggers training failure
        self.selector.update_model(np.array([2, 2]), "p1", 5.0)

        self.assertFalse(self.selector.is_trained)

    @patch("iterative_prompt_selector.StandardScaler.transform", side_effect=RuntimeError("transform fail"))
    @patch("iterative_prompt_selector.StandardScaler.fit")
    def test_update_model_transform_failure(
        self, mock_scaler_fit, mock_scaler_transform
    ):
        """Test scaler.transform errors also reset training state"""

        # Fill enough to train
        for _ in range(self.selector.min_samples_for_training - 1):
            self.selector.update_model(np.array([0, 0]), "p1", 4.0)

        # Trigger training
        self.selector.update_model(np.array([1, 1]), "p1", 4.0)

        self.assertFalse(self.selector.is_trained)
