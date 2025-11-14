"""
Test suite for generate_review method.
Tests review generation, diff truncation, and timing.
"""

import pytest
import numpy as np
import unittest
from unittest.mock import Mock, patch, MagicMock
import time # Import time for the original method, though we mock it in tests

# Assuming IterativePromptSelector is imported from online_estimator_version
from online_estimator_version import IterativePromptSelector


class TestGenerateReview(unittest.TestCase):
    """Tests for generate_review method"""

    def setUp(self):
        # We patch get_prompts to avoid external calls during setup
        with patch('online_estimator_version.get_prompts'):
            self.selector = IterativePromptSelector()
            # The actual function needs self.prompts to be a dictionary, 
            # so we ensure it's set up for the tests.
            self.selector.prompts = {'test_prompt': MagicMock()}

    # --- Utility for Mocking the LCEL Chain ---
    # The chain is: self.prompts[selected_prompt] | llm | parser
    def _setup_chain_mock(self, mock_llm, mock_parser, return_value):
        """Helper to set up recursive mocking for the LCEL pipe operations."""
        # 1. Mock the final chain object's invoke method
        final_chain_mock = MagicMock()
        final_chain_mock.invoke.return_value = return_value

        # 2. Mock the result of the second pipe: (llm | parser)
        # We mock __or__ on llm to simulate it returning a mock chain object 
        # that will be piped with parser. For simplicity, we can sometimes 
        # mock the result of the entire chain construction.
        
        # In this structure (A | B | C), we mock the result of the whole line.
        # Patching __or__ on the middle element (llm) to return the end chain 
        # is the most reliable way to mock multi-step piping.
        
        # When llm is piped with parser (llm | parser), return a final mock.
        # Note: We must chain the mocks correctly.
        
        # Mock the result of (llm | parser) to be the final_chain_mock
        # This requires mocking the __or__ on the result of the first pipe.
        
        # The result of (prompt | llm) must have an __or__ method 
        # that returns the final chain when passed 'parser'.
        
        # Mock the result of the first pipe (self.prompts[... ] | llm)
        chain_after_llm_mock = MagicMock()
        # When this result is piped with 'parser', it returns the final chain.
        chain_after_llm_mock.__or__.return_value = final_chain_mock 
        
        # Mock llm's __or__ (used in self.prompts[... ] | llm) 
        # to return the chain_after_llm_mock when piped with the prompt (which is mocked 
        # as self.selector.prompts['test_prompt']). Since the prompt object is the 
        # one starting the chain, we rely on the internal mock of the prompt object 
        # or the outer patch of llm to control the flow.
        
        # The simplest way that often works for the line: A | B | C is to 
        # mock the pipe operator on the final element (parser) to return the final 
        # chain mock, but this requires special handling. 
        
        # Let's use the most reliable approach: mock the __or__ on the middle object (llm).
        mock_llm.__or__.return_value = final_chain_mock # This simplifies the two pipes into one step
        
        return final_chain_mock

    # --------------------------------------------------------------------------

    @patch('online_estimator_version.llm')
    @patch('online_estimator_version.parser')
    @patch('online_estimator_version.time') 
    def test_generate_review_success(self, mock_time, mock_parser, mock_llm):
        """Test successful review generation and correct time measurement."""
        
        expected_review = "This is a great review!"
        
        # FIX: Call the helper to set up chain mocking correctly
        final_chain_mock = self._setup_chain_mock(mock_llm, mock_parser, expected_review)
        
        # Mock time so elapsed can be checked easily
        mock_time.time.side_effect = [1.0, 1.5] # Start time 1.0, End time 1.5
        
        diff_text = "diff content here"
        review, elapsed = self.selector.generate_review(diff_text, 'test_prompt')
        
        # Assertions
        self.assertEqual(review, expected_review)
        self.assertAlmostEqual(elapsed, 0.5)
        # Ensure invoke was called
        final_chain_mock.invoke.assert_called_once()


    @patch('online_estimator_version.llm')
    @patch('online_estimator_version.parser')
    @patch('online_estimator_version.time') # Patch time to avoid real measurement in this truncation test
    def test_generate_review_truncates_diff(self, mock_time, mock_parser, mock_llm):
        """Test that long diffs are truncated to 4000 chars."""
        
        expected_review = "Review"
        
        # FIX: Call the helper to set up chain mocking correctly
        final_chain_mock = self._setup_chain_mock(mock_llm, mock_parser, expected_review)
        
        # Set time side effect so the function runs without error
        mock_time.time.side_effect = [1.0, 1.0]

        # Create diff longer than 4000 chars
        long_diff = "x" * 5000
        review, elapsed = self.selector.generate_review(long_diff, 'test_prompt')
        
        # Check that invoke was called with truncated diff
        final_chain_mock.invoke.assert_called_once()
        call_args = final_chain_mock.invoke.call_args[0][0] # This will be the dictionary
        
        self.assertIn('diff', call_args)
        # Assert the diff length is the maximum allowed (4000)
        self.assertEqual(len(call_args['diff']), 4000)


    @patch('online_estimator_version.llm')
    @patch('online_estimator_version.parser')
    @patch('online_estimator_version.time') # FIX: Add time mock here
    def test_generate_review_measures_time(self, mock_time, mock_parser, mock_llm):
        """Test that elapsed time is measured correctly using time mocks."""
        
        expected_review = "Review"
        
        # FIX: Call the helper to set up chain mocking correctly
        final_chain_mock = self._setup_chain_mock(mock_llm, mock_parser, expected_review)
        
        # FIX: Use precise time mocking to assert elapsed time
        start_time = 100.0
        end_time = 100.35
        expected_elapsed = end_time - start_time
        
        mock_time.time.side_effect = [start_time, end_time] 
        
        review, elapsed = self.selector.generate_review("diff content", 'test_prompt')
        
        self.assertEqual(review, expected_review)
        # Assert elapsed time is the difference between the mocked times
        self.assertAlmostEqual(elapsed, expected_elapsed)