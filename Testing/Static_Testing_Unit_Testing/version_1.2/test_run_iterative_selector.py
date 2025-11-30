"""
Test suite for run_iterative_selector function.
Tests multi-PR execution flow, error handling, and final reporting.
"""

import pytest
import unittest
from unittest.mock import patch, Mock
from iterative_prompt_selector import IterativePromptSelector, run_iterative_selector


class TestRunIterativeSelector(unittest.TestCase):
    """Tests for run_iterative_selector function"""

    def setUp(self):
        # Patch get_prompts for the selector constructor
        patcher = patch("iterative_prompt_selector.get_prompts")
        self.addCleanup(patcher.stop)
        patcher.start()

    @patch("iterative_prompt_selector.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_success(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """Test successful run across multiple PRs"""

        # Arrange simulated PR results
        mock_process.side_effect = [
            {"pr_number": 1, "selected_prompt": "p1", "score": 8},
            {"pr_number": 2, "selected_prompt": "p2", "score": 9},
        ]
        mock_stats.return_value = {"training_samples": 2}

        # Act
        results, selector = run_iterative_selector([1, 2], load_previous=True)

        # Assert load_state called
        mock_load.assert_called_once()

        # process_pr called for each PR
        self.assertEqual(mock_process.call_count, 2)

        # Stats printed for each PR
        self.assertEqual(mock_stats.call_count, 3)  # two loops + final stats

        # save_state called at end
        mock_save.assert_called_once()

        # sleep called twice (for two PRs)
        self.assertEqual(mock_sleep.call_count, 2)

        # Results returned correctly
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["pr_number"], 1)
        self.assertEqual(results[1]["pr_number"], 2)
        self.assertIsInstance(selector, IterativePromptSelector)

    @patch("iterative_prompt_selector.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_error_handling(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """Test that PR failures are caught and skipped"""

        # First PR fails, second succeeds
        mock_process.side_effect = [
            ValueError("bad PR"),
            {"pr_number": 5, "selected_prompt": "ok", "score": 7}
        ]

        mock_stats.return_value = {"training_samples": 1}

        # Act
        results, selector = run_iterative_selector([100, 5])

        # First ValueError should be skipped, second processed
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["pr_number"], 5)

        # load_state used by default
        mock_load.assert_called_once()

        # save_state called once
        mock_save.assert_called_once()

    @patch("iterative_prompt_selector.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_no_load_previous(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """Test that load_state is skipped when load_previous=False"""

        mock_process.return_value = {"pr_number": 9, "selected_prompt": "x", "score": 6}
        mock_stats.return_value = {"training_samples": 1}

        run_iterative_selector([9], load_previous=False)

        # Ensure load_state was NOT called
        mock_load.assert_not_called()

        # save_state still called
        mock_save.assert_called_once()

        # sleep called once
        mock_sleep.assert_called_once()
