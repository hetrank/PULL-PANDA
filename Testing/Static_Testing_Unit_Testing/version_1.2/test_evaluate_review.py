"""
Test suite for evaluate_review method.
Tests review evaluation and scoring logic.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestEvaluateReview(unittest.TestCase):
    """Tests for evaluate_review method"""

    def setUp(self):
        self.selector = IterativePromptSelector()

    @patch('iterative_prompt_selector.meta_evaluate')
    @patch('iterative_prompt_selector.heuristic_metrics')
    def test_evaluate_review_success(self, mock_heur, mock_meta):
        """Test successful review evaluation"""
        # Mock heuristic metrics
        mock_heur.return_value = {
            'sections_presence': {'summary': True, 'issues': True},
            'bullet_points': 5,
            'length_words': 200,
            'mentions_bug': True,
            'mentions_suggest': True
        }
        
        # Mock meta evaluation
        mock_meta.return_value = ({
            'clarity': 8,
            'usefulness': 7,
            'depth': 9,
            'actionability': 8,
            'positivity': 7
        }, None)
        
        score, heur, meta = self.selector.evaluate_review("diff", "review")
        
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 10)
        self.assertIsInstance(heur, dict)
        self.assertIsInstance(meta, dict)

    @patch('iterative_prompt_selector.meta_evaluate')
    @patch('iterative_prompt_selector.heuristic_metrics')
    def test_evaluate_review_meta_error(self, mock_heur, mock_meta):
        """Test evaluation when meta evaluation returns error"""
        mock_heur.return_value = {
            'sections_presence': {},
            'bullet_points': 0,
            'length_words': 0,
            'mentions_bug': False,
            'mentions_suggest': False
        }
        
        # Meta evaluation returns error
        mock_meta.return_value = ({'error': 'Failed'}, None)
        
        score, heur, meta = self.selector.evaluate_review("diff", "review")
        
        # Should return default score
        self.assertEqual(score, 5.0)

    @patch('iterative_prompt_selector.meta_evaluate')
    @patch('iterative_prompt_selector.heuristic_metrics')
    def test_evaluate_review_score_calculation(self, mock_heur, mock_meta):
        """Test score calculation with specific values"""
        mock_heur.return_value = {
            'sections_presence': {'s1': True, 's2': True, 's3': True, 's4': True},
            'bullet_points': 10,
            'length_words': 150,
            'mentions_bug': True,
            'mentions_suggest': True
        }
        
        mock_meta.return_value = ({
            'clarity': 10,
            'usefulness': 10,
            'depth': 10,
            'actionability': 10,
            'positivity': 10
        }, None)
        
        score, heur, meta = self.selector.evaluate_review("diff", "review")
        
        # With perfect scores, should be close to 10
        self.assertGreater(score, 9.0)

    @patch('iterative_prompt_selector.meta_evaluate')
    @patch('iterative_prompt_selector.heuristic_metrics')
    def test_evaluate_review_length_scoring(self, mock_heur, mock_meta):
        """Test length-based scoring edge cases"""
        mock_meta.return_value = ({
            'clarity': 5, 'usefulness': 5, 'depth': 5,
            'actionability': 5, 'positivity': 5
        }, None)
        
        # Test too short
        mock_heur.return_value = {
            'sections_presence': {},
            'bullet_points': 0,
            'length_words': 10,  # Too short
            'mentions_bug': False,
            'mentions_suggest': False
        }
        score_short, _, _ = self.selector.evaluate_review("diff", "review")
        
        # Test optimal length
        mock_heur.return_value['length_words'] = 200  # Optimal
        score_optimal, _, _ = self.selector.evaluate_review("diff", "review")
        
        # Test too long
        mock_heur.return_value['length_words'] = 1500  # Too long
        score_long, _, _ = self.selector.evaluate_review("diff", "review")
        
        # Optimal should score higher
        self.assertGreater(score_optimal, score_short)