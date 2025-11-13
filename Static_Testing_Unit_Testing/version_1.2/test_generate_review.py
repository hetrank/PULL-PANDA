"""
Test suite for update_model method.
Tests model training and retraining logic.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestGenerateReview(unittest.TestCase):
    """Tests for generate_review method"""

    def setUp(self):
        with patch('iterative_prompt_selector.get_prompts'):
            self.selector = IterativePromptSelector()

    @patch('iterative_prompt_selector.llm')
    @patch('iterative_prompt_selector.parser')
    @patch('iterative_prompt_selector.time') # Add time mock to avoid real time in success test
    def test_generate_review_success(self, mock_time, mock_parser, mock_llm):
        """Test successful review generation"""
        
        # 1. Mock the *final* chain object (the result of A|B|C)
        final_chain_mock = MagicMock()
        final_chain_mock.invoke.return_value = "This is a great review!"
        
        # 2. Mock the chain *construction* to return the final_chain_mock
        # Use patch.object to mock the pipe operator on the final component (parser)
        # The actual line is `chain = self.prompts[selected_prompt] | llm | parser`
        # We mock the result of the last pipe operation involving `parser`.
        with patch.object(mock_parser, '__ror__', return_value=final_chain_mock):
            
            # Mock time so elapsed can be checked easily
            mock_time.time.side_effect = [1.0, 1.5] # Start time 1.0, End time 1.5
            
            diff_text = "diff content here"
            review, elapsed = self.selector.generate_review(diff_text, 'test_prompt')
            
            self.assertEqual(review, "This is a great review!")
            # The elapsed time should be 1.5 - 1.0 = 0.5
            self.assertAlmostEqual(elapsed, 0.5)

    @patch('iterative_prompt_selector.llm')
    @patch('iterative_prompt_selector.parser')
    def test_generate_review_truncates_diff(self, mock_parser, mock_llm):
        """Test that long diffs are truncated to 4000 chars"""
        
        # Mock the *final* chain object
        final_chain_mock = MagicMock()
        final_chain_mock.invoke.return_value = "Review"

        # Mock the chain construction (the result of the last pipe operation)
        with patch.object(mock_parser, '__ror__', return_value=final_chain_mock):
            
            # Create diff longer than 4000 chars
            long_diff = "x" * 5000
            review, elapsed = self.selector.generate_review(long_diff, 'test_prompt')
            
            # Check that invoke was called with truncated diff
            # The argument passed to invoke is a dictionary: {"diff": truncated_diff}
            final_chain_mock.invoke.assert_called_once()
            call_args = final_chain_mock.invoke.call_args[0][0] # This will be the dictionary
            
            self.assertIn('diff', call_args)
            self.assertEqual(len(call_args['diff']), 4000)

    @patch('iterative_prompt_selector.llm')
    @patch('iterative_prompt_selector.parser')
    def test_generate_review_measures_time(self, mock_parser, mock_llm): # ADD MOCKS HERE
        """Test that elapsed time is measured correctly"""
        
        # Mock the *final* chain object
        final_chain_mock = MagicMock()
        
        def slow_invoke(x):
            import time
            time.sleep(0.1)
            return "Review" # Ensure the mock returns a non-Generation type to skip real parser logic
        
        final_chain_mock.invoke.side_effect = slow_invoke # Assign the slow_invoke to the final chain's invoke
        
        # Mock the chain construction (the result of the last pipe operation)
        with patch.object(mock_parser, '__ror__', return_value=final_chain_mock):
            
            self.selector.prompts = {'test_prompt': Mock()}
            # The prompt mock is no longer needed since we mock the full chain construction via `parser.__ror__`
            
            review, elapsed = self.selector.generate_review("diff", 'test_prompt')
            
            self.assertEqual(review, "Review")
            self.assertGreaterEqual(elapsed, 0.1)