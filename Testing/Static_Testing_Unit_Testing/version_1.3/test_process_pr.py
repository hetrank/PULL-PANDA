"""
Updated test suite for process_pr.
Each test marked KEEP / OBSOLETE / NEW.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock
from online_estimator_version import IterativePromptSelector


class TestProcessPR(unittest.TestCase):

    def setUp(self):
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()


    # ============================================================
    # OBSOLETE — updated to include new return key + autosave logic
    # ============================================================
    @patch.object(IterativePromptSelector, 'save_state')
    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'update_model')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_success(
        self,
        mock_save_results,
        mock_update,
        mock_eval,
        mock_gen,
        mock_select,
        mock_vec,
        mock_extract,
        mock_fetch,
        mock_save_state,
    ):
        """OBSOLETE: Updated test for successful PR processing."""

        # Arrange
        mock_fetch.return_value = "diff content"
        mock_extract.return_value = {"lines": 10}
        mock_vec.return_value = np.array([1, 2, 3])
        mock_select.return_value = "best_prompt"
        mock_gen.return_value = ("review text", 0.7)
        mock_eval.return_value = (9.0, {"h": 2}, {"parsed": True})

        # Force sample_count to hit auto-save
        self.selector.sample_count = 2  # pre-update -> after update: 3 → triggers
        mock_save_state.return_value = True

        # Act
        result = self.selector.process_pr(101)

        # Assert main pipeline
        mock_fetch.assert_called_once()
        mock_extract.assert_called_once_with("diff content")
        mock_vec.assert_called_once_with({"lines": 10})
        mock_select.assert_called_once_with(np.array([1, 2, 3]))
        mock_gen.assert_called_once_with("diff content", "best_prompt")
        mock_eval.assert_called_once_with("diff content", "review text")
        mock_update.assert_called_once()
        mock_save_results.assert_called_once()

        # NEW: autosave must occur because sample_count == 3
        mock_save_state.assert_called_once()

        # NEW return field
        self.assertIn("generation_time", result)

        # Original fields unchanged
        self.assertEqual(result["pr_number"], 101)
        self.assertEqual(result["selected_prompt"], "best_prompt")
        self.assertEqual(result["review"], "review text")
        self.assertEqual(result["score"], 9.0)
        self.assertEqual(result["features"], {"lines": 10})


    # ============================================================
    # KEEP — exceptions behave the same
    # ============================================================
    @patch('online_estimator_version.fetch_pr_diff', side_effect=Exception("Network error"))
    def test_process_pr_fetch_failure(self, mock_fetch):
        """KEEP: fetch failure still raises"""
        with self.assertRaises(Exception):
            self.selector.process_pr(55)


    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features', side_effect=ValueError("bad diff"))
    def test_process_pr_feature_extraction_failure(self, mock_extract, mock_fetch):
        """KEEP"""
        mock_fetch.return_value = "diff"
        with self.assertRaises(ValueError):
            self.selector.process_pr(88)


    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt', side_effect=RuntimeError("no prompt"))
    def test_process_pr_prompt_selection_failure(
        self, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """KEEP"""
        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"x": 1}
        mock_vec.return_value = np.array([0])
        with self.assertRaises(RuntimeError):
            self.selector.process_pr(42)


    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review', side_effect=Exception("LLM failed"))
    def test_process_pr_generate_review_failure(
        self, mock_gen, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """KEEP"""
        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"f": 1}
        mock_vec.return_value = np.array([10])
        mock_select.return_value = "prompt"
        with self.assertRaises(Exception):
            self.selector.process_pr(77)


    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review', side_effect=Exception("Scoring failed"))
    def test_process_pr_evaluate_failure(
        self, mock_eval, mock_gen, mock_select, mock_vec, mock_extract, mock_fetch
    ):
        """KEEP"""
        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"ok": True}
        mock_vec.return_value = np.array([99])
        mock_select.return_value = "prompt"
        mock_gen.return_value = ("review", 0.3)
        with self.assertRaises(Exception):
            self.selector.process_pr(66)


    # ============================================================
    # OBSOLETE — Updated but still relevant
    # ============================================================
    @patch.object(IterativePromptSelector, 'save_state')
    @patch('online_estimator_version.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_updates_model_correctly(
        self,
        mock_save,
        mock_eval,
        mock_gen,
        mock_select,
        mock_vec,
        mock_extract,
        mock_fetch,
        mock_save_state,
    ):
        """OBSOLETE: Updated due to autosave."""

        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"metric": 7}
        mock_vec.return_value = np.array([4, 5])
        mock_select.return_value = "chosen_prompt"
        mock_gen.return_value = ("generated review", 1.1)
        mock_eval.return_value = (6.4, {}, {})

        # IMPORTANT: start at non-multiple of 3 → no autosave
        self.selector.sample_count = 1

        with patch.object(self.selector, 'update_model') as mock_update:
            self.selector.process_pr(808)

        mock_update.assert_called_once_with(
            np.array([4, 5]), "chosen_prompt", 6.4
        )

        # autosave must NOT occur here
        mock_save_state.assert_not_called()


    # ============================================================
    # NEW — must autosave on multiples of 3
    # ============================================================
    @patch.object(IterativePromptSelector, 'save_state')
    @patch.object(IterativePromptSelector, 'save_results')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'features_to_vector')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch('online_estimator_version.fetch_pr_diff')
    def test_autosave_every_three_calls(
        self,
        mock_fetch,
        mock_extract,
        mock_vec,
        mock_select,
        mock_gen,
        mock_eval,
        mock_save_results,
        mock_save_state,
    ):
        """NEW: autosave must trigger when sample_count becomes multiple of 3."""

        mock_fetch.return_value = "diff"
        mock_extract.return_value = {"n": 1}
        mock_vec.return_value = np.array([1])
        mock_select.return_value = "p"
        mock_gen.return_value = ("rev", 0.3)
        mock_eval.return_value = (8.0, {}, {})

        # Set sample_count so update_model -> sample_count=3
        self.selector.sample_count = 2

        self.selector.process_pr(501)

        mock_save_state.assert_called_once()
