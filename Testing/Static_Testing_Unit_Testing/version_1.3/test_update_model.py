"""
Test suite for IterativePromptSelector.update_model method.
Covers scaler fitting, transform fallback, model updates,
error recovery, and history correctness.
"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from sklearn.linear_model import SGDRegressor
from online_estimator_version import IterativePromptSelector


class TestUpdateModel(unittest.TestCase):
    """Tests for update_model method"""

    def setUp(self):
        # Bypass __init__ and manually set required fields
        self.selector = IterativePromptSelector.__new__(IterativePromptSelector)
        self.selector.prompt_names = ["A", "B"]
        self.selector.feature_history = []
        self.selector.prompt_history = []
        self.selector.score_history = []
        self.selector.sample_count = 0

        # Mock scaler & model
        self.selector.scaler = MagicMock()
        self.selector.model = MagicMock()
        self.selector.is_scaler_fitted = False

    # ---------------------------------------------------------
    # BASIC HISTORY + PROMPT INDEX
    # ---------------------------------------------------------

    def test_history_updated_correctly(self):
        """Ensure feature, prompt, score histories and sample_count update."""

        self.selector.update_model(
            features_vector=[1, 2],
            prompt_name="A",
            score=0.8
        )

        self.assertEqual(self.selector.feature_history, [[1, 2]])
        self.assertEqual(self.selector.prompt_history, [0])
        self.assertEqual(self.selector.score_history, [0.8])
        self.assertEqual(self.selector.sample_count, 1)

    # ---------------------------------------------------------
    # SCALER FITTING
    # ---------------------------------------------------------

    def test_scaler_fits_on_second_sample(self):
        """Scaler should fit once there are 2+ samples and was not fitted before."""

        self.selector.feature_history = [[1, 2]]
        self.selector.prompt_history = [0]
        self.selector.score_history = [0.5]
        self.selector.sample_count = 1
        self.selector.is_scaler_fitted = False

        self.selector.scaler.fit = MagicMock()
        self.selector.scaler.transform = MagicMock(return_value=[[9, 9]])

        self.selector.update_model(
            features_vector=[3, 4],
            prompt_name="B",
            score=1.0
        )

        self.selector.scaler.fit.assert_called_once()
        self.selector.scaler.transform.assert_called_once()
        self.assertTrue(self.selector.is_scaler_fitted)

    def test_no_scaler_fit_on_first_sample(self):
        """Scaler must not fit on the very first sample."""

        self.selector.update_model(
            features_vector=[5, 6],
            prompt_name="A",
            score=1.0
        )

        self.selector.scaler.fit.assert_not_called()
        self.assertFalse(self.selector.is_scaler_fitted)

    # ---------------------------------------------------------
    # SCALER TRANSFORM FAILURE → REFIT
    # ---------------------------------------------------------

    def test_scaler_transform_failure_refits(self):
        """If scaler.transform fails, scaler should refit and retry."""

        self.selector.feature_history = [[1, 2]]
        self.selector.prompt_history = [0]
        self.selector.score_history = [0.5]
        self.selector.sample_count = 1

        self.selector.is_scaler_fitted = True

        self.selector.scaler.transform.side_effect = [
            ValueError("bad transform"),
            [[7, 7]],  # second call after refit
        ]

        self.selector.update_model(
            features_vector=[9, 9],
            prompt_name="B",
            score=1.0
        )

        # Expect: transform fails → fit() → transform() retries
        self.selector.scaler.fit.assert_called_once()
        self.assertEqual(self.selector.scaler.transform.call_count, 2)

    # ---------------------------------------------------------
    # MODEL UPDATE LOGIC
    # ---------------------------------------------------------

    def test_model_partial_fit_called_with_correct_data(self):
        """Check correct formation of x_train using hstack(features + prompt_index)."""

        self.selector.is_scaler_fitted = False
        self.selector.model.partial_fit = MagicMock()

        self.selector.update_model(
            features_vector=[10, 20],
            prompt_name="A",
            score=2.0
        )

        # The expected input
        expected_x = np.hstack([[10, 20], [0]])  # prompt index 0

        args, _ = self.selector.model.partial_fit.call_args
        received_x = args[0][0]  # first (only) row

        np.testing.assert_array_equal(received_x, expected_x)

    # ---------------------------------------------------------
    # MODEL FAILURE & REINITIALIZATION
    # ---------------------------------------------------------

    # @patch("online_estimator_version.SGDRegressor")
    # def test_model_failure_triggers_reinitialize(self, mock_sgd):
    #     """If model.partial_fit raises an error, model should be reset & retrained."""

    #     self.selector.is_scaler_fitted = False

    #     # Make model.partial_fit fail
    #     self.selector.model.partial_fit.side_effect = ValueError("test failure")

    #     # Mock new model returned by SGDRegressor()
    #     new_model = MagicMock()
    #     mock_sgd.return_value = new_model

    #     # Add multiple samples to retrain on
    #     self.selector.feature_history = [[1, 2], [3, 4]]
    #     self.selector.prompt_history = [0, 1]
    #     self.selector.score_history = [0.5, 0.9]

    #     self.selector.sample_count = 2

    #     self.selector.update_model(
    #         features_vector=[5, 6],
    #         prompt_name="A",
    #         score=1.0
    #     )

    #     # Verify new model was created
    #     mock_sgd.assert_called_once()

    #     # New model must be trained on ALL past data
    #     self.assertTrue(new_model.partial_fit.called)
    #     self.assertGreaterEqual(new_model.partial_fit.call_count, 1)

    # ---------------------------------------------------------
    # FIRST-SAMPLE SPECIAL CASE HANDLING
    # ---------------------------------------------------------

    def test_first_sample_calls_partial_fit_once(self):
        """First sample should call model.partial_fit exactly once."""

        self.selector.is_scaler_fitted = False
        self.selector.model.partial_fit = MagicMock()

        self.selector.update_model(
            features_vector=[1, 1],
            prompt_name="A",
            score=1.0
        )

        self.selector.model.partial_fit.assert_called_once()

