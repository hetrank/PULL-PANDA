"""
Test suite for save_results method.
Tests file writing and output structure.
"""

import pytest
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
from iterative_prompt_selector import IterativePromptSelector


class TestSaveResults(unittest.TestCase):
    """Tests for save_results method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()
            self.selector.feature_history = [1, 2, 3]
            self.selector.is_trained = True

    # Helper function to find content written to a specific filename
    def _get_written_content(self, mock_file, filename):
        # mock_file is mock_open. We iterate over all calls to open()
        for call in mock_file.call_args_list:
            # Check if the filename matches (first arg of open is the filename)
            if call[0][0] == filename:
                # The returned mock handle is the second element of the call tuple
                # We need to access the write calls made on THIS specific handle
                handle = call[0][1] # This is not reliable for mock_open. Let's rely on call_args_list of the handle
                
                # A better approach is to check all handles created by mock_file
                # and return the content written to the handle used with the correct filename.
                
                # mock_file() returns the mock handle. We cannot rely on the simple join 
                # as it combines writes across all files. We must rely on the mock's tracking.
                
                # Since the calls are recorded sequentially, we look for the filename call.
                
                # Find the call that opens the file, then look at what was written to that handle.
                # In mock_open, subsequent calls to open() return the same mock object by default,
                # which is why the writes are mixed. We must access the content in a way that respects
                # the two separate writes.
                
                # We'll use the simplest, most direct fix in the test for the default mock_open behavior:
                # Assuming the JSON file is written first, and the review file is written second.
                # Since the review text is a simple string, it will be the second write operation.
                # This requires your save_results method to use two distinct 'with open' blocks.
                
                # Let's rely on the assumption that the written content can be separated by the call index
                # if we track the content written to each file separately.
                
                # If your save_results writes JSON and then Review text:
                
                # 1. JSON write (first block in save_results)
                # 2. Review text write (second block in save_results)

                # mock_open doesn't isolate writes per file handle automatically in a simple way.
                # We will check the content written to the handle and expect only the relevant part.
                
                # The only way to reliably separate them is to look at the content being written.
                
                pass # We will rely on direct indexing below, as mocking internal file writes is complex with mock_open.
                
        # Since standard mock_open behavior mixes writes, we will separate the write calls
        # based on where the JSON data and review text should appear.
        handle = mock_file()
        
        # This will contain ALL writes: [('{"timestamp": "..."}',), ('review text',)]
        write_calls = [call.args[0] for call in handle.write.call_args_list if call.args]
        
        # We assume the JSON data is the first, large write
        json_content = next((c for c in write_calls if c.startswith('{')), None)
        
        if filename.endswith(".json"):
            return json_content
        elif filename.endswith(".txt"):
            # This is complex because the review text might be embedded in the middle of JSON writes if they are fragmented.
            # However, based on the `Extra data` error, it is likely that the first write is the entire JSON object.
            # We will assume the review text is a distinct, non-JSON string.
            return next((c for c in write_calls if not c.startswith('{')), None)

        return None

    @patch("builtins.open", new_callable=mock_open)
    @patch("iterative_prompt_selector.datetime")
    def test_save_results_success(self, mock_datetime, mock_file):
        """Test successful saving of JSON and review file"""

        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

        pr_number = 77
        features = {"lines": 50}
        prompt = "my prompt"
        review = "This is a generated review text."
        score = 9.1
        heur = {"h1": 1}
        meta_parsed = {"meta": "ok"}

        # Act
        self.selector.save_results(pr_number, features, prompt, review, score, heur, meta_parsed)

        # ---- Assert file writes ----
        expected_json_filename = "iterative_results_pr77_20250101_120000.json"
        expected_review_filename = "review_pr77_my_prompt.txt"

        # Check for both files being opened
        mock_file.assert_any_call(expected_json_filename, 'w', encoding='utf-8')
        mock_file.assert_any_call(expected_review_filename, 'w', encoding='utf-8')

        # --- FIX: Extract ONLY JSON written content ---
        handle = mock_file()
        # Find the calls that look like JSON (starting with '{')
        json_writes = [call.args[0] for call in handle.write.call_args_list if call.args[0].strip().startswith('{')]
        written_json = "".join(json_writes)
        
        # Check that review text was written (it should be the non-JSON write)
        review_writes = [call.args[0] for call in handle.write.call_args_list if not call.args[0].strip().startswith('{') and call.args[0].strip()]
        written_review = "".join(review_writes)
        
        self.assertEqual(written_review, review)

        try:
            data = json.loads(written_json)
        except json.JSONDecodeError as e:
            self.fail(f"Failed to decode JSON. Content written: {written_json}\nError: {e}")

        # Assert JSON structure correctness
        self.assertEqual(data["timestamp"], "20250101_120000")
        self.assertEqual(data["pr_number"], 77)
        self.assertEqual(data["selected_prompt"], "my prompt")
        self.assertEqual(data["review_score"], 9.1)
        self.assertEqual(data["features"], {"lines": 50})
        self.assertEqual(data["heuristics"], {"h1": 1})
        self.assertEqual(data["meta_evaluation"], {"meta": "ok"})
        self.assertEqual(data["training_data_size"], 3)
        self.assertTrue(data["model_trained"])


    @patch("builtins.open", new_callable=mock_open)
    @patch("iterative_prompt_selector.datetime")
    def test_save_results_prompt_sanitization(self, mock_datetime, mock_file):
        """Test that prompt spaces are replaced in filename"""

        mock_datetime.now.return_value.strftime.return_value = "20251231_235959"

        pr_number = 10
        prompt = "complex prompt string"
        review = "Review"

        self.selector.save_results(pr_number, {}, prompt, review, 5, {}, {})

        expected_filename = "review_pr10_complex_prompt_string.txt"
        mock_file.assert_any_call(expected_filename, 'w', encoding='utf-8')

    @patch("builtins.open", new_callable=mock_open)
    @patch("iterative_prompt_selector.datetime")
    def test_save_results_tracks_training_state(self, mock_datetime, mock_file):
        """Test that model state fields are correctly written"""

        mock_datetime.now.return_value.strftime.return_value = "20240101_010101"

        # Change internal state
        self.selector.feature_history = [1]
        self.selector.is_trained = False

        self.selector.save_results(
            5, {"x": 1}, "test", "ok", 7.5, {"h": 0}, {"meta": 1}
        )

        # --- FIX: Extract ONLY JSON written content ---
        handle = mock_file()
        # Find the calls that look like JSON (starting with '{')
        json_writes = [call.args[0] for call in handle.write.call_args_list if call.args[0].strip().startswith('{')]
        written_json = "".join(json_writes)
        
        try:
            data = json.loads(written_json)
        except json.JSONDecodeError as e:
            self.fail(f"Failed to decode JSON. Content written: {written_json}\nError: {e}")

        self.assertEqual(data["training_data_size"], 1)
        self.assertFalse(data["model_trained"])