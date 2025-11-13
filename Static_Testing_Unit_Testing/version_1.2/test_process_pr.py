"""
Test suite for process_pr method.
Tests end-to-end PR processing flow with extensive coverage.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock
from iterative_prompt_selector import IterativePromptSelector


class TestProcessPR(unittest.TestCase):
    """Tests for process_pr method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'update_model')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_success(
        self,
        mock_save,
        mock_update,
        mock_eval,
        mock_gen,
        mock_select,
        mock_vec,
        mock_extract,
        mock_fetch,
    ):
        """Test successful PR processing"""

        mock_fetch.return_value = "diff content"
        mock_extract.return_value = {"lines": 10}
        mock_vec.return_value = np.array([1, 2, 3])
        mock_select.return_value = "best_prompt"
        mock_gen.return_value = ("review text", 0.7)
        mock_eval.return_value = (9.0, {"h": 2}, {"parsed": True})

        result = self.selector.process_pr(101)

        # Assertions for call order correctness
        mock_fetch.assert_called_once()
        mock_extract.assert_called_once_with("diff content")
        mock_vec.assert_called_once_with({"lines": 10})
        mock_select.assert_called_once_with(np.array([1, 2, 3]))
        mock_gen.assert_called_once_with("diff content", "best_prompt")
        mock_eval.assert_called_once_with("diff content", "review text")
        mock_update.assert_called_once()
        mock_save.assert_called_once()

        # Result structure assertions
        self.assertEqual(result["pr_number"], 101)
        self.assertEqual(result["selected_prompt"], "best_prompt")
        self.assertEqual(result["review"], "review text")
        self.assertEqual(result["score"], 9.0)
        self.assertEqual(result["features"], {"lines": 10})

    @patch('iterative_prompt_selector.fetch_pr_diff', side_effect=Exception("Network error"))
    def test_process_pr_fetch_failure(self, mock_fetch):
        """Test failure when diff fetching fails"""
        with self.assertRaises(Exception):
            self.selector.process_pr(55)

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features', side_effect=ValueError("bad diff"))
    def test_process_pr_feature_extraction_failure(self, mock_extract, mock_fetch):
        """Test feature extraction failure propagates"""
        mock_fetch.return_value = "diff"
        with self.assertRaises(ValueError):
            self.selector.process_pr(88)

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt', side_effect=RuntimeError("no prompt"))
    def test_process_pr_prompt_selection_failure(
        self, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """Test prompt selection failure"""
        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"x": 1}
        mock_vec.return_value = np.array([0])

        with self.assertRaises(RuntimeError):
            self.selector.process_pr(42)

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review', side_effect=Exception("LLM failed"))
    def test_process_pr_generate_review_failure(
        self, mock_gen, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """Test review generation failure"""
        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"f": 1}
        mock_vec.return_value = np.array([10])
        mock_select.return_value = "prompt"

        with self.assertRaises(Exception):
            self.selector.process_pr(77)

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review', side_effect=Exception("Scoring failed"))
    def test_process_pr_evaluate_failure(
        self, mock_eval, mock_gen, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """Test evaluation failure stops processing"""

        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"ok": True}
        mock_vec.return_value = np.array([99])
        mock_select.return_value = "prompt"
        mock_gen.return_value = ("review", 0.3)

        with self.assertRaises(Exception):
            self.selector.process_pr(66)

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'update_model')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_updates_model_correctly(
        self,
        mock_save,
        mock_update,
        mock_eval,
        mock_gen,
        mock_select,
        mock_vec,
        mock_extract,
        mock_fetch,
    ):
        """Ensure update_model is called with correct arguments"""

        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"metric": 7}
        mock_vec.return_value = np.array([4, 5])
        mock_select.return_value = "chosen_prompt"
        mock_gen.return_value = ("generated review", 1.1)
        mock_eval.return_value = (6.4, {}, {})

        self.selector.process_pr(808)

        mock_update.assert_called_once_with(
            np.array([4, 5]),
            "chosen_prompt",
            6.4
        )
