"""
Test suite for meta_to_score function.
Tests weighted scoring calculation from meta-evaluation results.
"""
# 21 pass
import pytest
from accuracy_checker_refactored import meta_to_score


class TestMetaToScore:
    """Test suite for meta_to_score function."""

    def test_perfect_scores(self):
        """Test maximum possible weighted score."""
        meta_parsed = {
            "clarity": 10,
            "usefulness": 10,
            "depth": 10,
            "actionability": 10,
            "positivity": 10,
        }
        score = meta_to_score(meta_parsed)
        assert score == 10.0

    def test_minimum_scores(self):
        """Test minimum scores (all 1s)."""
        meta_parsed = {
            "clarity": 1,
            "usefulness": 1,
            "depth": 1,
            "actionability": 1,
            "positivity": 1,
        }
        score = meta_to_score(meta_parsed)
        assert score == 1.0

    def test_weighted_calculation(self):
        """Test correct weighted calculation with known values."""
        # clarity: 0.18, usefulness: 0.28, depth: 0.2, actionability: 0.24, positivity: 0.1
        meta_parsed = {
            "clarity": 10,      # 10 * 0.18 = 1.8
            "usefulness": 10,   # 10 * 0.28 = 2.8
            "depth": 10,        # 10 * 0.2 = 2.0
            "actionability": 10, # 10 * 0.24 = 2.4
            "positivity": 0,    # 0 * 0.1 = 0.0
        }
        # Total = 1.8 + 2.8 + 2.0 + 2.4 + 0.0 = 9.0
        score = meta_to_score(meta_parsed)
        assert score == 9.0

    def test_usefulness_highest_weight(self):
        """Test that usefulness has highest impact (weight 0.28)."""
        base = {
            "clarity": 5,
            "usefulness": 5,
            "depth": 5,
            "actionability": 5,
            "positivity": 5,
        }
        
        # Increase usefulness
        meta_usefulness = {**base, "usefulness": 10}
        score_usefulness = meta_to_score(meta_usefulness)
        
        # Increase clarity (lower weight)
        meta_clarity = {**base, "clarity": 10}
        score_clarity = meta_to_score(meta_clarity)
        
        # Usefulness increase should have bigger impact
        assert (score_usefulness - 5.0) > (score_clarity - 5.0)

    def test_positivity_lowest_weight(self):
        """Test that positivity has lowest impact (weight 0.1)."""
        base = {
            "clarity": 5,
            "usefulness": 5,
            "depth": 5,
            "actionability": 5,
            "positivity": 5,
        }
        
        # Increase positivity
        meta_positivity = {**base, "positivity": 10}
        score_positivity = meta_to_score(meta_positivity)
        
        # Increase actionability (higher weight)
        meta_actionability = {**base, "actionability": 10}
        score_actionability = meta_to_score(meta_actionability)
        
        # Positivity increase should have smaller impact
        assert (score_positivity - 5.0) < (score_actionability - 5.0)

    def test_error_dict_returns_none(self):
        """Test that error dictionary returns None."""
        meta_parsed = {
            "error": "some error message",
            "raw": "raw output"
        }
        score = meta_to_score(meta_parsed)
        assert score is None

    def test_non_dict_input(self):
        """Test with non-dictionary input."""
        score = meta_to_score("not a dict")
        assert score is None
        
        score = meta_to_score(None)
        assert score is None
        
        score = meta_to_score([1, 2, 3])
        assert score is None

    def test_missing_all_keys(self):
        """Test with dictionary missing all expected keys."""
        meta_parsed = {"other_key": "value"}
        score = meta_to_score(meta_parsed)
        # Should default all to 5 * weight
        # 5 * (0.18 + 0.28 + 0.2 + 0.24 + 0.1) = 5 * 1.0 = 5.0
        assert score == 5.0

    def test_missing_some_keys(self):
        """Test with some keys missing."""
        meta_parsed = {
            "clarity": 8,
            "usefulness": 9,
            # depth missing
            "actionability": 7,
            # positivity missing
        }
        # clarity: 8*0.18=1.44, usefulness: 9*0.28=2.52
        # depth: 5*0.2=1.0 (default), actionability: 7*0.24=1.68
        # positivity: 5*0.1=0.5 (default)
        # Total = 1.44 + 2.52 + 1.0 + 1.68 + 0.5 = 7.14
        score = meta_to_score(meta_parsed)
        assert score == 7.14

    def test_float_values(self):
        """Test with float values instead of integers."""
        meta_parsed = {
            "clarity": 8.5,
            "usefulness": 7.5,
            "depth": 9.5,
            "actionability": 6.5,
            "positivity": 8.5,
        }
        score = meta_to_score(meta_parsed)
        # Should calculate correctly with floats
        assert isinstance(score, float)
        assert 0.0 <= score <= 10.0

    def test_values_as_strings(self):
        """Test with string values (should default to 5)."""
        meta_parsed = {
            "clarity": "high",
            "usefulness": 8,
            "depth": "medium",
            "actionability": 7,
            "positivity": "low",
        }
        score = meta_to_score(meta_parsed)
        # Non-numeric values should default to 5
        # clarity: 5*0.18=0.9, usefulness: 8*0.28=2.24
        # depth: 5*0.2=1.0, actionability: 7*0.24=1.68
        # positivity: 5*0.1=0.5
        # Total = 0.9 + 2.24 + 1.0 + 1.68 + 0.5 = 6.32
        score = meta_to_score(meta_parsed)
        assert score == 6.32

    def test_none_values(self):
        """Test with None values."""
        meta_parsed = {
            "clarity": None,
            "usefulness": 8,
            "depth": None,
            "actionability": 7,
            "positivity": None,
        }
        score = meta_to_score(meta_parsed)
        # None values should default to 5
        assert isinstance(score, float)
        assert 0.0 <= score <= 10.0

    def test_zero_values(self):
        """Test with zero values."""
        meta_parsed = {
            "clarity": 0,
            "usefulness": 0,
            "depth": 0,
            "actionability": 0,
            "positivity": 0,
        }
        score = meta_to_score(meta_parsed)
        assert score == 0.0

    def test_out_of_range_values(self):
        """Test with values outside 1-10 range."""
        meta_parsed = {
            "clarity": 15,
            "usefulness": -5,
            "depth": 100,
            "actionability": 8,
            "positivity": 0.5,
        }
        score = meta_to_score(meta_parsed)
        # Should calculate without validation
        assert isinstance(score, float)

    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        # weights: 0.18 + 0.28 + 0.2 + 0.24 + 0.1 = 1.0
        meta_parsed = {
            "clarity": 10,
            "usefulness": 10,
            "depth": 10,
            "actionability": 10,
            "positivity": 10,
        }
        score = meta_to_score(meta_parsed)
        assert score == 10.0
        
        meta_parsed_five = {k: 5 for k in meta_parsed}
        score_five = meta_to_score(meta_parsed_five)
        assert score_five == 5.0

    def test_rounding_to_two_decimals(self):
        """Test that result is rounded to 2 decimal places."""
        meta_parsed = {
            "clarity": 7,
            "usefulness": 8,
            "depth": 9,
            "actionability": 6,
            "positivity": 5,
        }
        score = meta_to_score(meta_parsed)
        # Check it's rounded to 2 decimals
        assert score == round(score, 2)
        # Check no more than 2 decimal places
        assert len(str(score).split('.')[-1]) <= 2

    def test_extra_keys_ignored(self):
        """Test that extra keys in dict are ignored."""
        meta_parsed = {
            "clarity": 8,
            "usefulness": 7,
            "depth": 9,
            "actionability": 8,
            "positivity": 6,
            "explain": "some explanation",
            "extra_field": 100,
            "another_field": "value",
        }
        score = meta_to_score(meta_parsed)
        # Should only use the 5 weighted keys
        expected = (8 * 0.18 + 7 * 0.28 + 9 * 0.2 + 8 * 0.24 + 6 * 0.1)
        assert score == round(expected, 2)

    def test_boundary_values(self):
        """Test with boundary values at 1 and 10."""
        test_cases = [
            {"clarity": 1, "usefulness": 10, "depth": 1, "actionability": 10, "positivity": 1},
            {"clarity": 10, "usefulness": 1, "depth": 10, "actionability": 1, "positivity": 10},
        ]
        
        for meta_parsed in test_cases:
            score = meta_to_score(meta_parsed)
            assert 1.0 <= score <= 10.0
            assert isinstance(score, float)

    def test_mixed_types_in_values(self):
        """Test with mixed types (int, float, string, None)."""
        meta_parsed = {
            "clarity": 8,
            "usefulness": 7.5,
            "depth": "invalid",
            "actionability": None,
            "positivity": 9,
        }
        score = meta_to_score(meta_parsed)
        # Should handle mixed types gracefully
        assert isinstance(score, float)
        assert 0.0 <= score <= 10.0

    def test_empty_dict(self):
        """Test with completely empty dictionary."""
        meta_parsed = {}
        score = meta_to_score(meta_parsed)
        # All default to 5
        assert score == 5.0

    def test_consistency_with_same_input(self):
        """Test that same input always produces same output."""
        meta_parsed = {
            "clarity": 7,
            "usefulness": 8,
            "depth": 6,
            "actionability": 9,
            "positivity": 7,
        }
        score1 = meta_to_score(meta_parsed)
        score2 = meta_to_score(meta_parsed)
        score3 = meta_to_score(meta_parsed)
        
        assert score1 == score2 == score3