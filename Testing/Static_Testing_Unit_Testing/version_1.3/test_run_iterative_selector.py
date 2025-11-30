"""
Updated test suite for run_iterative_selector.
Each test labeled OBSOLETE / NEW.
"""

import pytest
import unittest
from unittest.mock import patch, Mock
from online_estimator_version import IterativePromptSelector, run_iterative_selector


class TestRunIterativeSelector(unittest.TestCase):
    """Tests for run_iterative_selector"""

    def setUp(self):
        # Patch get_prompts for the selector constructor
        patcher = patch("online_estimator_version.get_prompts")
        self.addCleanup(patcher.stop)
        patcher.start()


    # ============================================================
    # OBSOLETE — Updated to include periodic save + final save
    # ============================================================
    @patch("online_estimator_version.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_success(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """OBSOLETE: updated for periodic save behavior"""

        # Arrange simulated PR results
        mock_process.side_effect = [
            {"pr_number": 1, "selected_prompt": "p1", "score": 8},
            {"pr_number": 2, "selected_prompt": "p2", "score": 9},
        ]
        mock_stats.return_value = {"training_samples": 2}

        # Act
        results, selector = run_iterative_selector(
            [1, 2], load_previous=True, save_frequency=2
        )

        # load_state called
        mock_load.assert_called_once()

        # process_pr called twice
        self.assertEqual(mock_process.call_count, 2)

        # stats printed twice + once at end = 3
        self.assertEqual(mock_stats.call_count, 3)

        # save_state should be called twice:
        # → one periodic save on 2nd PR
        # → one final save at end
        self.assertEqual(mock_save.call_count, 2)

        # sleep called twice
        self.assertEqual(mock_sleep.call_count, 2)

        # Result correctness
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["pr_number"], 1)
        self.assertEqual(results[1]["pr_number"], 2)


    # ============================================================
    # OBSOLETE — Must update exceptions + periodic save
    # ============================================================
    @patch("online_estimator_version.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_error_handling(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """OBSOLETE: updated to handle new error types & periodic saves"""

        # First PR fails, second succeeds
        mock_process.side_effect = [
            ValueError("bad PR"),  # still caught
            {"pr_number": 5, "selected_prompt": "ok", "score": 7}
        ]

        mock_stats.return_value = {"training_samples": 1}

        # Act
        results, selector = run_iterative_selector(
            [100, 5], save_frequency=2
        )

        # Only one valid result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["pr_number"], 5)

        mock_load.assert_called_once()

        # save_state should be called twice:
        # - 2nd iteration periodic save
        # - final save
        self.assertEqual(mock_save.call_count, 2)


    # ============================================================
    # OBSOLETE — Must update expected save count
    # ============================================================
    @patch("online_estimator_version.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    @patch.object(IterativePromptSelector, "load_state")
    def test_run_iterative_selector_no_load_previous(
        self, mock_load, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """OBSOLETE: updated for final save behavior"""

        mock_process.return_value = {
            "pr_number": 9, "selected_prompt": "x", "score": 6
        }
        mock_stats.return_value = {"training_samples": 1}

        # Act
        run_iterative_selector([9], load_previous=False)

        # load_state was not called
        mock_load.assert_not_called()

        # save_state should be called once (final save)
        mock_save.assert_called_once()

        # sleep called once
        mock_sleep.assert_called_once()


    # ============================================================
    # NEW — ensure periodic save triggers correctly
    # ============================================================
    @patch("online_estimator_version.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    def test_periodic_save_triggers_correctly(
        self, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """NEW: save_state must trigger every 'save_frequency' iterations"""

        mock_process.return_value = {"pr_number": 1, "selected_prompt": "p", "score": 1}
        mock_stats.return_value = {}

        # 4 PRs with save_frequency=2 → periodic saves at 2nd & 4th + final save
        run_iterative_selector([1, 2, 3, 4], save_frequency=2)

        # Expected:
        # - Save after 2nd PR
        # - Save after 4th PR
        # - Final save
        self.assertEqual(mock_save.call_count, 3)


    # ============================================================
    # NEW — ensure periodic save does NOT trigger early
    # ============================================================
    @patch("online_estimator_version.time.sleep")
    @patch.object(IterativePromptSelector, "save_state")
    @patch.object(IterativePromptSelector, "get_stats")
    @patch.object(IterativePromptSelector, "process_pr")
    def test_periodic_save_not_triggered_when_below_frequency(
        self, mock_process, mock_stats, mock_save, mock_sleep
    ):
        """NEW: with only 1 PR and save_frequency=3, no periodic save should occur"""

        mock_process.return_value = {"pr_number": 10, "selected_prompt": "p", "score": 1}
        mock_stats.return_value = {}

        run_iterative_selector([10], save_frequency=3)

        # Only final save
        mock_save.assert_called_once()
