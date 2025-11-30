"""
Test suite for heuristic_metrics function.
Tests various review text patterns and edge cases.
"""

import pytest
from accuracy_checker_refactored import heuristic_metrics


class TestHeuristicMetrics:
    """Test suite for heuristic_metrics function."""

    def test_empty_review(self):
        """Test with completely empty review."""
        result = heuristic_metrics("")
        assert result["length_words"] == 0
        assert result["bullet_points"] == 0
        assert result["mentions_bug"] is False
        assert result["mentions_suggest"] is False
        assert all(not v for v in result["sections_presence"].values())

    def test_whitespace_only_review(self):
        """Test review with only whitespace and newlines."""
        result = heuristic_metrics("   \n\n\t  \n  ")
        assert result["length_words"] == 0
        assert result["bullet_points"] == 0

    def test_multiple_bullet_point_formats(self):
        """Test detection of different bullet point formats."""
        review = """
        - First bullet with dash
        * Second bullet with asterisk
        • Third bullet with bullet char
          - Nested bullet indented
        - Another dash bullet
        """
        result = heuristic_metrics(review)
        assert result["bullet_points"] >= 4

    def test_bullet_points_without_leading_whitespace(self):
        """Test bullets that start at line beginning."""
        review = "- bullet one\n- bullet two\n* bullet three"
        result = heuristic_metrics(review)
        assert result["bullet_points"] == 3

    def test_bug_keyword_variations(self):
        """Test various bug-related keyword patterns."""
        test_cases = [
            ("This code has a BUG in it", True),
            ("ERROR: null pointer exception", True),
            ("Test will FAIL without this fix", True),
            ("There's an ISSUE with the logic", True),
            ("The bug is subtle", True),
            ("error in the code", True),
            ("No problems found", False),
            ("debugging the problem", False),  # "bug" not as whole word
            ("errorHandler function", False),  # "error" not as whole word
        ]
        for review, expected in test_cases:
            result = heuristic_metrics(review)
            assert result["mentions_bug"] == expected, f"Failed for: {review}"

    def test_suggest_keyword_variations(self):
        """Test various suggestion-related keyword patterns."""
        test_cases = [
            ("I SUGGEST refactoring this", True),
            ("Would RECOMMEND using a map", True),
            ("Please CONSIDER this approach", True),
            ("Need to FIX the memory leak", True),
            ("ACTION required on this PR", True),
            ("suggesting improvements", True),
            ("Good code review", False),
        ]
        for review, expected in test_cases:
            result = heuristic_metrics(review)
            assert result["mentions_suggest"] == expected, f"Failed for: {review}"

    def test_case_insensitive_keywords(self):
        """Test that keyword detection is case-insensitive."""
        reviews = [
            "BUG found",
            "bug found",
            "Bug Found",
            "bUg FoUnD"
        ]
        for review in reviews:
            result = heuristic_metrics(review)
            assert result["mentions_bug"] is True

    def test_word_boundaries_for_keywords(self):
        """Test that keywords must be complete words."""
        # "bug" should match only as a complete word
        result1 = heuristic_metrics("debugging")  # contains "bug" but not as word
        result2 = heuristic_metrics("debug")  # doesn't contain "bug"
        result3 = heuristic_metrics("a bug exists")  # contains "bug" as word
        
        # Note: regex \b matches word boundaries, "debugging" contains \bbug\b? No.
        # Let's verify actual behavior
        assert result1["mentions_bug"] is False
        assert result2["mentions_bug"] is False
        assert result3["mentions_bug"] is True

    def test_all_sections_present(self):
        """Test when all expected sections are mentioned."""
        review = """
        Summary: This PR adds new features
        Bugs found in the implementation
        Errors need to be handled
        Code quality is good
        Suggestions for improvement
        Improvements can be made
        Tests are comprehensive
        Positive feedback on design
        Final review: Approved
        """
        result = heuristic_metrics(review)
        assert all(result["sections_presence"].values())

    def test_partial_section_matches(self):
        """Test when sections are embedded in words."""
        review = """
        summarize the changes
        debugging is needed
        """
        result = heuristic_metrics(review)
        # "summarize" contains "summary"
        assert result["sections_presence"]["summary"] is True

    def test_no_sections_present(self):
        """Test when no sections are mentioned."""
        review = "This is a simple review without any specific sections."
        result = heuristic_metrics(review)
        # Check that most sections are False
        false_count = sum(1 for v in result["sections_presence"].values() if not v)
        assert false_count >= 7

    def test_very_long_review(self):
        """Test with extremely long review text."""
        review = " ".join(["word"] * 10000)
        result = heuristic_metrics(review)
        assert result["length_words"] == 10000
        assert isinstance(result["bullet_points"], int)

    def test_unicode_and_special_characters(self):
        """Test with unicode characters and special symbols."""
        review = """
        • Unicode bullet point
        — This has an em-dash
        "Smart quotes" are here
        Testing unicode: 你好世界
        """
        result = heuristic_metrics(review)
        assert result["bullet_points"] >= 1
        assert result["length_words"] > 0

    def test_mixed_bullet_and_text(self):
        """Test complex review with mixed content."""
        review = """
        Initial paragraph without bullets.
        
        - First bullet point
        - Second bullet point
        
        Middle paragraph.
        
        * Another bullet style
        • Yet another bullet
        
        Final paragraph discussing bugs and suggesting fixes.
        """
        result = heuristic_metrics(review)
        assert result["bullet_points"] == 4
        assert result["mentions_bug"] is True
        assert result["mentions_suggest"] is True
        assert result["length_words"] > 20

    def test_only_keywords_no_bullets(self):
        """Test review with keywords but no structure."""
        review = "bug error fail issue suggest recommend consider fix action"
        result = heuristic_metrics(review)
        assert result["mentions_bug"] is True
        assert result["mentions_suggest"] is True
        assert result["bullet_points"] == 0

    def test_multiple_newlines_and_spacing(self):
        """Test that multiple spaces and newlines don't inflate word count."""
        review = "word1    word2\n\n\nword3\t\tword4"
        result = heuristic_metrics(review)
        assert result["length_words"] == 4

    def test_bullet_points_inline_not_counted(self):
        """Test that bullet chars not at line start aren't counted."""
        review = "This sentence has - a dash and * asterisk in it"
        result = heuristic_metrics(review)
        assert result["bullet_points"] == 0

    def test_sections_case_sensitivity(self):
        """Test that section detection is case-insensitive."""
        review = "SUMMARY: overall BUGS found CODE QUALITY good"
        result = heuristic_metrics(review)
        assert result["sections_presence"]["summary"] is True
        assert result["sections_presence"]["bugs"] is True
        assert result["sections_presence"]["code quality"] is True