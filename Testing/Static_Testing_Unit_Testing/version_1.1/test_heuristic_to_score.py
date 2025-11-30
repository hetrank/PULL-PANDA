"""
Test suite for heuristics_to_score function.
Tests scoring algorithm with various metric combinations.
"""
# 18 pass
import pytest
from accuracy_checker_refactored import heuristics_to_score


class TestHeuristicsToScore:
    """Test suite for heuristics_to_score function."""

    def test_perfect_score_scenario(self):
        """Test maximum possible score with ideal metrics."""
        heur = {
            "sections_presence": {
                "summary": True,
                "bugs": True,
                "errors": True,
                "code quality": True,
                "suggestions": True,
                "improvements": True,
                "tests": True,
                "positive": True,
                "final review": True,
            },
            "bullet_points": 15,
            "length_words": 400,
            "mentions_bug": True,
            "mentions_suggest": True,
        }
        score = heuristics_to_score(heur)
        assert score == 10.0

    def test_minimum_score_scenario(self):
        """Test minimum score with worst metrics."""
        heur = {
            "sections_presence": {},
            "bullet_points": 0,
            "length_words": 0,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert score == 0.0

    def test_empty_sections_presence_dict(self):
        """Test with empty sections_presence dictionary."""
        heur = {
            "sections_presence": {},
            "bullet_points": 5,
            "length_words": 200,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert 0.0 <= score <= 10.0
        # With no sections, sec_frac = 0, should still get points from other factors

    def test_all_sections_false(self):
        """Test when all sections are present but all False."""
        heur = {
            "sections_presence": {
                "summary": False,
                "bugs": False,
                "errors": False,
                "code quality": False,
                "suggestions": False,
            },
            "bullet_points": 5,
            "length_words": 200,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert score < 5.0  # Should be relatively low without sections

    def test_half_sections_present(self):
        """Test with exactly half sections present."""
        heur = {
            "sections_presence": {
                "summary": True,
                "bugs": False,
                "errors": True,
                "code quality": False,
                "suggestions": True,
                "improvements": False,
            },
            "bullet_points": 5,
            "length_words": 300,
            "mentions_bug": True,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert 4.0 <= score <= 8.0

    def test_optimal_word_count_range(self):
        """Test scores at optimal word count boundaries (80-800)."""
        base_heur = {
            "sections_presence": {"summary": True},
            "bullet_points": 5,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        
        # Test at lower bound (80 words)
        heur_80 = {**base_heur, "length_words": 80}
        score_80 = heuristics_to_score(heur_80)
        
        # Test at middle (400 words)
        heur_400 = {**base_heur, "length_words": 400}
        score_400 = heuristics_to_score(heur_400)
        
        # Test at upper bound (800 words)
        heur_800 = {**base_heur, "length_words": 800}
        score_800 = heuristics_to_score(heur_800)
        
        # All should have length_score = 1.0, so scores should be equal
        assert abs(score_80 - score_400) < 0.1
        assert abs(score_400 - score_800) < 0.1

    def test_below_minimum_word_count(self):
        """Test word counts below optimal range."""
        base_heur = {
            "sections_presence": {},
            "bullet_points": 0,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        
        # Very few words
        heur_10 = {**base_heur, "length_words": 10}
        score_10 = heuristics_to_score(heur_10)
        
        # Half of minimum
        heur_40 = {**base_heur, "length_words": 40}
        score_40 = heuristics_to_score(heur_40)
        
        # Just below minimum
        heur_79 = {**base_heur, "length_words": 79}
        score_79 = heuristics_to_score(heur_79)
        
        assert score_10 < score_40 < score_79

    def test_above_maximum_word_count(self):
        """Test word counts above optimal range."""
        base_heur = {
            "sections_presence": {},
            "bullet_points": 0,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        
        # Just above maximum
        heur_900 = {**base_heur, "length_words": 900}
        score_900 = heuristics_to_score(heur_900)
        
        # Well above maximum
        heur_1500 = {**base_heur, "length_words": 1500}
        score_1500 = heuristics_to_score(heur_1500)
        
        # Extremely long
        heur_3000 = {**base_heur, "length_words": 3000}
        score_3000 = heuristics_to_score(heur_3000)
        
        assert score_900 > score_1500 > score_3000
        assert score_3000 >= 0.0  # Should not go negative

    def test_bullet_points_capped_at_10(self):
        """Test that bullet points are capped at 10 for scoring."""
        base_heur = {
            "sections_presence": {},
            "length_words": 200,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        
        heur_10 = {**base_heur, "bullet_points": 10}
        score_10 = heuristics_to_score(heur_10)
        
        heur_50 = {**base_heur, "bullet_points": 50}
        score_50 = heuristics_to_score(heur_50)
        
        # Both should have same bullets_score
        assert abs(score_10 - score_50) < 0.01

    def test_bug_bonus_impact(self):
        """Test impact of bug mention bonus."""
        base_heur = {
            "sections_presence": {},
            "bullet_points": 5,
            "length_words": 200,
            "mentions_suggest": False,
        }
        
        heur_no_bug = {**base_heur, "mentions_bug": False}
        heur_with_bug = {**base_heur, "mentions_bug": True}
        
        score_no_bug = heuristics_to_score(heur_no_bug)
        score_with_bug = heuristics_to_score(heur_with_bug)
        
        # Bug bonus should add 1.0 to final score (0.1 * 10)
        assert abs(score_with_bug - score_no_bug - 1.0) < 0.01

    def test_suggest_bonus_impact(self):
        """Test impact of suggestion mention bonus."""
        base_heur = {
            "sections_presence": {},
            "bullet_points": 5,
            "length_words": 200,
            "mentions_bug": False,
        }
        
        heur_no_suggest = {**base_heur, "mentions_suggest": False}
        heur_with_suggest = {**base_heur, "mentions_suggest": True}
        
        score_no_suggest = heuristics_to_score(heur_no_suggest)
        score_with_suggest = heuristics_to_score(heur_with_suggest)
        
        # Suggest bonus should add 1.0 to final score
        assert abs(score_with_suggest - score_no_suggest - 1.0) < 0.01

    def test_both_bonuses_combined(self):
        """Test combined effect of both bonuses."""
        base_heur = {
            "sections_presence": {},
            "bullet_points": 5,
            "length_words": 200,
        }
        
        heur_no_bonus = {**base_heur, "mentions_bug": False, "mentions_suggest": False}
        heur_both_bonus = {**base_heur, "mentions_bug": True, "mentions_suggest": True}
        
        score_no_bonus = heuristics_to_score(heur_no_bonus)
        score_both_bonus = heuristics_to_score(heur_both_bonus)
        
        # Both bonuses should add 2.0 total
        assert abs(score_both_bonus - score_no_bonus - 2.0) < 0.01

    def test_missing_keys_in_heuristics(self):
        """Test behavior with missing dictionary keys."""
        heur = {
            "sections_presence": {},
            # missing bullet_points, length_words, mentions_bug, mentions_suggest
        }
        score = heuristics_to_score(heur)
        # Should handle missing keys with .get() default of 0/False
        assert 0.0 <= score <= 10.0

    def test_none_values_in_sections(self):
        """Test sections_presence with None values."""
        heur = {
            "sections_presence": {
                "summary": None,
                "bugs": True,
                "errors": None,
            },
            "bullet_points": 5,
            "length_words": 200,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert 0.0 <= score <= 10.0

    def test_weight_distribution(self):
        """Test that weights sum correctly (0.45 + 0.25 + 0.25 = 0.95)."""
        # Test maximum without bonuses
        heur_max = {
            "sections_presence": {"a": True, "b": True},
            "bullet_points": 10,
            "length_words": 400,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur_max)
        # Max without bonuses should be 9.5
        assert 9.4 <= score <= 9.6

    def test_score_boundaries(self):
        """Test that scores are properly bounded and rounded."""
        # Test various combinations to ensure 0 <= score <= 10
        test_cases = [
            {"sections_presence": {}, "bullet_points": 0, "length_words": 0, "mentions_bug": False, "mentions_suggest": False},
            {"sections_presence": {"a": True}, "bullet_points": 20, "length_words": 100, "mentions_bug": True, "mentions_suggest": True},
            {"sections_presence": {f"s{i}": True for i in range(20)}, "bullet_points": 100, "length_words": 5000, "mentions_bug": True, "mentions_suggest": True},
        ]
        
        for heur in test_cases:
            score = heuristics_to_score(heur)
            assert 0.0 <= score <= 10.0
            assert isinstance(score, float)
            # Check rounding to 2 decimal places
            assert score == round(score, 2)

    def test_extreme_values(self):
        """Test with extreme metric values."""
        heur = {
            "sections_presence": {str(i): (i % 2 == 0) for i in range(100)},
            "bullet_points": 1000,
            "length_words": 100000,
            "mentions_bug": True,
            "mentions_suggest": True,
        }
        score = heuristics_to_score(heur)
        assert 0.0 <= score <= 10.0

    def test_zero_division_safety(self):
        """Test that there's no division by zero with edge cases."""
        heur = {
            "sections_presence": {},
            "bullet_points": 0,
            "length_words": 0,
            "mentions_bug": False,
            "mentions_suggest": False,
        }
        score = heuristics_to_score(heur)
        assert score == 0.0  # Should not raise exception