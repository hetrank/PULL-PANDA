"""
Test suite for IterativePromptSelector.__init__ method.
Tests correct initialization of all internal fields.
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from iterative_prompt_selector import IterativePromptSelector


class TestInit(unittest.TestCase):
    """Tests for __init__ method"""

    @patch("iterative_prompt_selector.get_prompts")
    def test_init_initializes_correct_fields(self, mock_get_prompts):
        """Test that constructor initializes all fields correctly"""

        # Arrange: create fake prompts
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

        # Assert model type
        self.assertIsInstance(selector.model, RandomForestRegressor)

        # Assert scaler type
        self.assertIsInstance(selector.scaler, StandardScaler)

        # Assert training flags
        self.assertFalse(selector.is_trained)
        self.assertEqual(selector.min_samples_for_training, 5)

    @patch("iterative_prompt_selector.get_prompts")
    def test_init_model_configuration(self, mock_get_prompts):
        """Test that model is configured with correct parameters"""

        mock_get_prompts.return_value = {"p": MagicMock()}  # minimal case

        selector = IterativePromptSelector()

        # RandomForest params
        self.assertEqual(selector.model.n_estimators, 50)
        self.assertEqual(selector.model.random_state, 42)

        # StandardScaler should have no fitted attributes initially
        self.assertFalse(hasattr(selector.scaler, "mean_"))
        self.assertFalse(hasattr(selector.scaler, "scale_"))
