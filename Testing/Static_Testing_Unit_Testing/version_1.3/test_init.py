"""
Regression + Full Coverage Test Suite for IterativePromptSelector.__init__

Status labels:
- KEEP      (works as-is)
- OBSOLETE  (needs update)
- REDUNDANT (kept only for historical trace)
"""

import unittest
from unittest.mock import patch, MagicMock
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDRegressor

from online_estimator_version import IterativePromptSelector


# ------------------------------------------------------------
# OLD TESTS (kept with regression labels)
# ------------------------------------------------------------
class TestInitLegacy(unittest.TestCase):

    @patch("online_estimator_version.get_prompts")
    def test_init_initializes_correct_fields(self, mock_get_prompts):  # OBSOLETE
        """
        OBSOLETE:
        This test belongs to the old implementation.
        It checks RandomForestRegressor, is_trained, min_samples_for_training.
        These do not exist in the new implementation.
        Left unchanged for regression history.
        """

        # Arrange
        mock_get_prompts.return_value = {
            "promptA": MagicMock(),
            "promptB": MagicMock()
        }

        # Act
        selector = IterativePromptSelector()

        # Assert prompts loaded
        mock_get_prompts.assert_called_once()
        self.assertEqual(selector.prompts, mock_get_prompts.return_value)

        # Assert prompt names
        self.assertEqual(selector.prompt_names, ["promptA", "promptB"])

        # Assert histories start empty
        self.assertEqual(selector.feature_history, [])
        self.assertEqual(selector.prompt_history, [])
        self.assertEqual(selector.score_history, [])

        # These assertions are now invalid:
        # (kept only for regression trace, WILL FAIL IF RUN)
        # self.assertIsInstance(selector.model, RandomForestRegressor)
        # self.assertFalse(selector.is_trained)
        # self.assertEqual(selector.min_samples_for_training, 5)

    @patch("online_estimator_version.get_prompts")
    def test_init_model_configuration(self, mock_get_prompts):  # REDUNDANT
        """
        REDUNDANT:
        This test validated old RandomForestRegressor parameters.
        No longer relevant.
        Kept only for historical trace.
        """

        pass
        # Old code left as comment:
        # selector = IterativePromptSelector()
        # self.assertEqual(selector.model.n_estimators, 50)
        # self.assertEqual(selector.model.random_state, 42)


# ------------------------------------------------------------
# NEW TEST SUITE (100% coverage of new __init__)
# ------------------------------------------------------------
class TestInitNew(unittest.TestCase):

    @patch("online_estimator_version.get_prompts")
    def test_init_loads_prompts_and_names(self, mock_get_prompts):  # NEW – KEEP
        """Ensure prompts and prompt_names initialize correctly."""
        mock_get_prompts.return_value = {"a": 1, "b": 2}

        selector = IterativePromptSelector()

        self.assertEqual(selector.prompts, {"a": 1, "b": 2})
        self.assertEqual(selector.prompt_names, ["a", "b"])
        mock_get_prompts.assert_called_once()

    @patch("online_estimator_version.get_prompts")
    def test_init_histories_are_empty(self, mock_get_prompts):  # NEW – KEEP
        """Histories must start empty."""
        mock_get_prompts.return_value = {"x": 1}

        selector = IterativePromptSelector()

        self.assertEqual(selector.feature_history, [])
        self.assertEqual(selector.prompt_history, [])
        self.assertEqual(selector.score_history, [])

    @patch("online_estimator_version.get_prompts")
    def test_init_model_is_sgd_regressor(self, mock_get_prompts):  # NEW – KEEP
        """Model must be an SGDRegressor with correct hyperparameters."""
        mock_get_prompts.return_value = {"p": 1}

        selector = IterativePromptSelector()

        self.assertIsInstance(selector.model, SGDRegressor)
        self.assertEqual(selector.model.random_state, 42)
        self.assertEqual(selector.model.learning_rate, "constant")
        self.assertEqual(selector.model.eta0, 0.01)
        self.assertEqual(selector.model.alpha, 0.0001)
        self.assertEqual(selector.model.max_iter, 1000)
        self.assertEqual(selector.model.tol, 1e-3)
        self.assertTrue(selector.model.warm_start)

    @patch("online_estimator_version.get_prompts")
    def test_init_scaler_is_standard_scaler(self, mock_get_prompts):  # NEW – KEEP
        """Scaler must be a StandardScaler and unfitted."""
        mock_get_prompts.return_value = {"p": 1}

        selector = IterativePromptSelector()

        self.assertIsInstance(selector.scaler, StandardScaler)
        # must not have mean_ or scale_ yet
        self.assertFalse(hasattr(selector.scaler, "mean_"))
        self.assertFalse(hasattr(selector.scaler, "scale_"))

    @patch("online_estimator_version.get_prompts")
    def test_init_internal_flags(self, mock_get_prompts):  # NEW – KEEP
        """Check new flags: sample_count and is_scaler_fitted."""
        mock_get_prompts.return_value = {"p": 1}

        selector = IterativePromptSelector()

        self.assertEqual(selector.sample_count, 0)
        self.assertFalse(selector.is_scaler_fitted)
