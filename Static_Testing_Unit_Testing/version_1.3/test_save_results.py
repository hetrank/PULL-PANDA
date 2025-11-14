"""
Updated test suite for save_results.
Each test marked KEEP / OBSOLETE / REDUNDANT / NEW.
"""

import pytest
import json
import unittest
from unittest.mock import patch, MagicMock
from online_estimator_version import IterativePromptSelector


class TestSaveResults(unittest.TestCase):

    def setUp(self):
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()
            self.selector.sample_count = 3  # new field replacing is_trained


    # ===============================================================
    # OBSOLETE — Updated for new save_text_to_file behavior
    # ===============================================================
    @patch("online_estimator_version.save_text_to_file")
    @patch("online_estimator_version.datetime")
    def test_save_results_success(self, mock_datetime, mock_save_text):
        """OBSOLETE: Updated to match the new JSON structure and save method"""

        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

        pr_number = 77
        features = {"lines": 50}
        prompt = "my prompt"
        review = "This is a generated review text."
        score = 9.1
        heur = {"h1": 1}
        meta_parsed = {"meta": "ok"}

        # Act
        self.selector.save_results(
            pr_number, features, prompt,
            review, score, heur, meta_parsed
        )

        # Expected filenames
        json_filename = "iterative_results_pr77_20250101_120000.json"
        review_filename = "review_pr77_my_prompt.txt"

        # save_text_to_file should be called twice
        self.assertEqual(mock_save_text.call_count, 2)

        # Extract calls
        calls = {call.args[0]: call.args[1] for call in mock_save_text.call_args_list}

        # JSON content
        written_json = calls[json_filename]
        data = json.loads(written_json)

        # Assert JSON correctness (updated structure)
        self.assertEqual(data["timestamp"], "20250101_120000")
        self.assertEqual(data["pr_number"], 77)
        self.assertEqual(data["selected_prompt"], "my prompt")
        self.assertEqual(data["review_score"], 9.1)
        self.assertEqual(data["features"], {"lines": 50})
        self.assertEqual(data["heuristics"], {"h1": 1})
        self.assertEqual(data["meta_evaluation"], {"meta": "ok"})
        self.assertEqual(data["training_samples"], 3)

        # Review file check
        self.assertEqual(calls[review_filename], review)


    # ===============================================================
    # OBSOLETE — Updated sanitization test
    # ===============================================================
    @patch("online_estimator_version.save_text_to_file")
    @patch("online_estimator_version.datetime")
    def test_save_results_prompt_sanitization(self, mock_datetime, mock_save_text):
        """OBSOLETE: Updated sanitization test for save_text_to_file"""

        mock_datetime.now.return_value.strftime.return_value = "20251231_235959"

        pr_number = 10
        prompt = "complex prompt/string"
        review = "Review"

        self.selector.save_results(pr_number, {}, prompt, review, 5, {}, {})

        # filename sanitization
        expected_filename = "review_pr10_complex_prompt_string.txt"

        # Assert review save called with sanitized filename
        calls = [c.args[0] for c in mock_save_text.call_args_list]
        self.assertIn(expected_filename, calls)


    # ===============================================================
    # REDUNDANT — No longer applicable because training fields removed
    # ===============================================================
    @unittest.skip("REDUNDANT: 'training_data_size' and 'model_trained' removed in new version.")
    def test_save_results_tracks_training_state(self):
        pass


    # ===============================================================
    # NEW — ensure two files are saved via save_text_to_file
    # ===============================================================
    @patch("online_estimator_version.save_text_to_file")
    @patch("online_estimator_version.datetime")
    def test_save_results_calls_save_text_twice(self, mock_datetime, mock_save_text):
        """NEW: Ensure JSON + review are saved through save_text_to_file"""

        mock_datetime.now.return_value.strftime.return_value = "20240101_010101"

        self.selector.save_results(
            5, {"x": 1}, "test prompt", "review text",
            7.5, {"h": 0}, {"meta": 1}
        )

        # Exactly two calls: JSON + review
        self.assertEqual(mock_save_text.call_count, 2)


    # ===============================================================
    # NEW — verify JSON contains sample_count not is_trained
    # ===============================================================
    @patch("online_estimator_version.save_text_to_file")
    @patch("online_estimator_version.datetime")
    def test_save_results_contains_training_samples(self, mock_datetime, mock_save_text):
        """NEW: Validate 'training_samples' field is correct"""

        mock_datetime.now.return_value.strftime.return_value = "20240101_010101"
        self.selector.sample_count = 9

        self.selector.save_results(
            12, {"k": 2}, "abc", "xyz", 5, {}, {}
        )

        # Extract JSON call
        json_text = None
        for filename, text in (c.args for c in mock_save_text.call_args_list):
            if filename.endswith(".json"):
                json_text = text

        data = json.loads(json_text)
        self.assertEqual(data["training_samples"], 9)
