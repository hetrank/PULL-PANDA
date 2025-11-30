"""
Combined test suite for accuracy_checker_refactored module.
Contains critical edge cases and integration tests only.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from accuracy_checker_refactored import (
    heuristic_metrics,
    meta_evaluate,
    heuristics_to_score,
    meta_to_score,
    run_all
)


class TestHeuristicMetricsEdgeCases:
    """Critical edge cases for heuristic_metrics."""

    def test_empty_review(self):
        """Test with completely empty review."""
        result = heuristic_metrics("")
        assert result["length_words"] == 0
        assert result["bullet_points"] == 0
        assert result["mentions_bug"] is False
        assert result["mentions_suggest"] is False

    def test_multiple_bullet_point_formats(self):
        """Test detection of different bullet point formats."""
        review = "- dash\n* asterisk\n• bullet\n  - nested"
        result = heuristic_metrics(review)
        assert result["bullet_points"] >= 4

    def test_word_boundaries_for_keywords(self):
        """Test that keywords must be complete words."""
        assert heuristic_metrics("debugging")["mentions_bug"] is False
        assert heuristic_metrics("a bug exists")["mentions_bug"] is True

    def test_very_long_review(self):
        """Test with extremely long review text."""
        review = " ".join(["word"] * 10000)
        result = heuristic_metrics(review)
        assert result["length_words"] == 10000

    def test_unicode_and_special_characters(self):
        """Test with unicode characters and special symbols."""
        review = "• Unicode bullet\n— em-dash\n你好世界"
        result = heuristic_metrics(review)
        assert result["bullet_points"] >= 1
        assert result["length_words"] > 0

    def test_multiple_newlines_and_spacing(self):
        """Test that multiple spaces and newlines don't inflate word count."""
        review = "word1    word2\n\n\nword3\t\tword4"
        result = heuristic_metrics(review)
        assert result["length_words"] == 4


class TestMetaEvaluateEdgeCases:
    """Critical edge cases for meta_evaluate."""

    def test_json_with_text_prefix_suffix(self):
        """Test JSON extraction when surrounded by text."""
        response = '''Sure! Here is the evaluation:
        {"clarity": 9, "usefulness": 8, "depth": 7, "actionability": 8, "positivity": 6, "explain": "excellent"}
        This completes the evaluation.'''
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert isinstance(parsed, dict)
            if "error" not in parsed:
                assert parsed["clarity"] == 9

    def test_malformed_json(self):
        """Test handling of malformed JSON response."""
        response = '{"clarity": 8, missing quote}'
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert "error" in parsed

    def test_no_json_in_response(self):
        """Test response with no JSON at all."""
        response = "This is just plain text."
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert "error" in parsed
            assert "no JSON" in parsed["error"]

    def test_llm_invocation_exception(self):
        """Test handling of LLM invocation failure."""
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.side_effect = Exception("API rate limit exceeded")
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert "error" in parsed
            assert "evaluator invoke failed" in parsed["error"]
            assert raw is None

    def test_truncated_diff_4000_chars(self):
        """Test that diff is properly truncated to 4000 chars."""
        json_response = '{"clarity": 5, "usefulness": 5, "depth": 5, "actionability": 5, "positivity": 5, "explain": "ok"}'
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = json_response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            long_diff = "x" * 10000
            parsed, raw = meta_evaluate(long_diff, "review")
            
            assert mock_chain.invoke.called
            call_args = mock_chain.invoke.call_args[0][0]
            assert len(call_args["diff"]) == 4000

    def test_json_with_missing_fields(self):
        """Test JSON missing some required fields."""
        json_response = '{"clarity": 7, "usefulness": 8, "explain": "incomplete"}'
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = json_response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert "error" not in parsed
            assert parsed["clarity"] == 7

    def test_unicode_in_json_values(self):
        """Test JSON with unicode characters in string values."""
        json_response = '''{
            "clarity": 7, "usefulness": 8, "depth": 6,
            "actionability": 7, "positivity": 8,
            "explain": "Good review! 👍 很好"
        }'''
        
        with patch('accuracy_checker_refactored.evaluator_prompt') as mock_prompt, \
             patch('accuracy_checker_refactored.llm') as mock_llm, \
             patch('accuracy_checker_refactored.StrOutputParser') as mock_parser:
            
            mock_chain = Mock()
            mock_chain.invoke.return_value = json_response
            
            mock_prompt.__or__ = Mock(return_value=mock_prompt)
            mock_llm.__or__ = Mock(return_value=mock_llm)
            mock_parser.return_value = Mock(__or__=Mock(return_value=mock_chain))
            
            parsed, raw = meta_evaluate("diff", "review")
            
            assert isinstance(parsed, dict)
            assert "error" not in parsed


class TestHeuristicsToScoreEdgeCases:
    """Critical edge cases for heuristics_to_score."""

    def test_perfect_score_scenario(self):
        """Test maximum possible score with ideal metrics."""
        heur = {
            "sections_presence": {f"s{i}": True for i in range(9)},
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

    def test_optimal_word_count_boundaries(self):
        """Test scores at optimal word count boundaries (80-800)."""
        base = {"sections_presence": {}, "bullet_points": 0,
                "mentions_bug": False, "mentions_suggest": False}
        
        scores = [
            heuristics_to_score({**base, "length_words": w})
            for w in [80, 400, 800]
        ]
        # All should have length_score = 1.0
        assert all(abs(s - scores[0]) < 0.1 for s in scores)

    def test_below_minimum_word_count(self):
        """Test word counts below optimal range."""
        base = {"sections_presence": {}, "bullet_points": 0,
                "mentions_bug": False, "mentions_suggest": False}
        
        score_10 = heuristics_to_score({**base, "length_words": 10})
        score_40 = heuristics_to_score({**base, "length_words": 40})
        score_79 = heuristics_to_score({**base, "length_words": 79})
        
        assert score_10 < score_40 < score_79

    def test_above_maximum_word_count(self):
        """Test word counts above optimal range."""
        base = {"sections_presence": {}, "bullet_points": 0,
                "mentions_bug": False, "mentions_suggest": False}
        
        score_900 = heuristics_to_score({**base, "length_words": 900})
        score_1500 = heuristics_to_score({**base, "length_words": 1500})
        score_3000 = heuristics_to_score({**base, "length_words": 3000})
        
        assert score_900 > score_1500 > score_3000 >= 0.0

    def test_bullet_points_capped_at_10(self):
        """Test that bullet points are capped at 10 for scoring."""
        base = {"sections_presence": {}, "length_words": 200,
                "mentions_bug": False, "mentions_suggest": False}
        
        score_10 = heuristics_to_score({**base, "bullet_points": 10})
        score_50 = heuristics_to_score({**base, "bullet_points": 50})
        
        assert abs(score_10 - score_50) < 0.01

    def test_both_bonuses_combined(self):
        """Test combined effect of both bonuses."""
        base = {"sections_presence": {}, "bullet_points": 5, "length_words": 200}
        
        score_no = heuristics_to_score({**base, "mentions_bug": False, "mentions_suggest": False})
        score_both = heuristics_to_score({**base, "mentions_bug": True, "mentions_suggest": True})
        
        assert abs(score_both - score_no - 2.0) < 0.01

    def test_missing_keys_in_heuristics(self):
        """Test behavior with missing dictionary keys."""
        heur = {"sections_presence": {}}
        score = heuristics_to_score(heur)
        assert 0.0 <= score <= 10.0

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


class TestMetaToScoreEdgeCases:
    """Critical edge cases for meta_to_score."""

    def test_perfect_scores(self):
        """Test maximum possible weighted score."""
        meta = {"clarity": 10, "usefulness": 10, "depth": 10,
                "actionability": 10, "positivity": 10}
        assert meta_to_score(meta) == 10.0

    def test_minimum_scores(self):
        """Test minimum scores (all 1s)."""
        meta = {"clarity": 1, "usefulness": 1, "depth": 1,
                "actionability": 1, "positivity": 1}
        assert meta_to_score(meta) == 1.0

    def test_weighted_calculation_verification(self):
        """Test correct weighted calculation with known values."""
        meta = {"clarity": 10, "usefulness": 10, "depth": 10,
                "actionability": 10, "positivity": 0}
        # 10*0.18 + 10*0.28 + 10*0.2 + 10*0.24 + 0*0.1 = 9.0
        assert meta_to_score(meta) == 9.0

    def test_error_dict_returns_none(self):
        """Test that error dictionary returns None."""
        meta = {"error": "some error", "raw": "output"}
        assert meta_to_score(meta) is None

    def test_non_dict_input(self):
        """Test with non-dictionary input."""
        assert meta_to_score("not a dict") is None
        assert meta_to_score(None) is None
        assert meta_to_score([1, 2, 3]) is None

    def test_missing_all_keys_defaults_to_5(self):
        """Test with dictionary missing all expected keys."""
        meta = {"other_key": "value"}
        # All default to 5: 5 * (0.18+0.28+0.2+0.24+0.1) = 5.0
        assert meta_to_score(meta) == 5.0

    def test_missing_some_keys(self):
        """Test with some keys missing."""
        meta = {"clarity": 8, "usefulness": 9, "actionability": 7}
        # clarity: 8*0.18=1.44, usefulness: 9*0.28=2.52
        # depth: 5*0.2=1.0, actionability: 7*0.24=1.68
        # positivity: 5*0.1=0.5
        # Total = 7.14
        assert meta_to_score(meta) == 7.14

    def test_values_as_strings_default_to_5(self):
        """Test with string values (should default to 5)."""
        meta = {"clarity": "high", "usefulness": 8, "depth": "medium",
                "actionability": 7, "positivity": "low"}
        # Non-numeric default to 5: 5*0.18 + 8*0.28 + 5*0.2 + 7*0.24 + 5*0.1
        assert meta_to_score(meta) == 6.32

    def test_none_values(self):
        """Test with None values."""
        meta = {"clarity": None, "usefulness": 8, "depth": None,
                "actionability": 7, "positivity": None}
        score = meta_to_score(meta)
        assert isinstance(score, float) and 0.0 <= score <= 10.0

    def test_zero_values(self):
        """Test with zero values."""
        meta = {"clarity": 0, "usefulness": 0, "depth": 0,
                "actionability": 0, "positivity": 0}
        assert meta_to_score(meta) == 0.0

    def test_rounding_to_two_decimals(self):
        """Test that result is rounded to 2 decimal places."""
        meta = {"clarity": 7, "usefulness": 8, "depth": 9,
                "actionability": 6, "positivity": 5}
        score = meta_to_score(meta)
        assert score == round(score, 2)

    def test_empty_dict_defaults_all_to_5(self):
        """Test with completely empty dictionary."""
        assert meta_to_score({}) == 5.0

    def test_mixed_types_in_values(self):
        """Test with mixed types (int, float, string, None)."""
        meta = {"clarity": 8, "usefulness": 7.5, "depth": "invalid",
                "actionability": None, "positivity": 9}
        score = meta_to_score(meta)
        assert isinstance(score, float) and 0.0 <= score <= 10.0


class TestRunAllEdgeCases:
    """Critical edge cases for run_all integration."""

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_multiple_prompts_sorted_by_score(self, mock_prompts, mock_fetch,
                                              mock_heur, mock_meta, mock_save):
        """Test that results are sorted by final score ascending."""
        mock_prompts.return_value = {
            "high": Mock(), "low": Mock(), "mid": Mock()
        }
        mock_fetch.return_value = "diff"
        
        def heur_effect(review):
            if "high" in review:
                return {"length_words": 500, "bullet_points": 10,
                       "mentions_bug": True, "mentions_suggest": True,
                       "sections_presence": {f"s{i}": True for i in range(9)}}
            elif "mid" in review:
                return {"length_words": 200, "bullet_points": 5,
                       "mentions_bug": True, "mentions_suggest": False,
                       "sections_presence": {"s1": True}}
            return {"length_words": 50, "bullet_points": 0,
                   "mentions_bug": False, "mentions_suggest": False,
                   "sections_presence": {}}
        
        mock_heur.side_effect = heur_effect
        mock_meta.return_value = ({"clarity": 7, "usefulness": 7, "depth": 7,
                                   "actionability": 7, "positivity": 7}, "raw")
        
        for name, prompt in mock_prompts.return_value.items():
            mock_chain = Mock()
            mock_chain.invoke.return_value = f"{name} review"
            prompt.__or__ = Mock(return_value=mock_chain)
        
        results = run_all()
        
        scores = [r["final_score"] for r in results]
        assert scores == sorted(scores)

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_prompt_invoke_exception_handling(self, mock_prompts, mock_fetch,
                                             mock_heur, mock_meta, mock_save):
        """Test handling when prompt invocation fails."""
        mock_prompts.return_value = {"failing": Mock()}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {"length_words": 0, "bullet_points": 0,
                                  "mentions_bug": False, "mentions_suggest": False,
                                  "sections_presence": {}}
        mock_meta.return_value = ({"error": "failed"}, None)
        
        mock_chain = Mock()
        mock_chain.invoke.side_effect = Exception("LLM timeout")
        mock_prompts.return_value["failing"].__or__ = Mock(return_value=mock_chain)
        
        results = run_all()
        
        assert "ERROR" in results[0]["review"]
        assert "timeout" in results[0]["review"].lower()

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_meta_failure_uses_heuristic_only(self, mock_prompts, mock_fetch,
                                              mock_heur, mock_meta, mock_save):
        """Test that final score uses only heuristic when meta fails."""
        mock_prompts.return_value = {"test": Mock()}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {"length_words": 200, "bullet_points": 5,
                                  "mentions_bug": True, "mentions_suggest": True,
                                  "sections_presence": {"summary": True}}
        mock_meta.return_value = ({"error": "failed"}, None)
        
        mock_chain = Mock()
        mock_chain.invoke.return_value = "review"
        mock_prompts.return_value["test"].__or__ = Mock(return_value=mock_chain)
        
        results = run_all()
        
        assert results[0]["meta_score"] == "N/A"
        assert results[0]["final_score"] == results[0]["heur_score"]

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_weighted_score_calculation(self, mock_prompts, mock_fetch,
                                       mock_heur, mock_meta, mock_save):
        """Test 70/30 weighted scoring when meta succeeds."""
        mock_prompts.return_value = {"test": Mock()}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {"length_words": 200, "bullet_points": 5,
                                  "mentions_bug": True, "mentions_suggest": True,
                                  "sections_presence": {"summary": True}}
        mock_meta.return_value = ({"clarity": 10, "usefulness": 10, "depth": 10,
                                   "actionability": 10, "positivity": 10}, "raw")
        
        mock_chain = Mock()
        mock_chain.invoke.return_value = "review"
        mock_prompts.return_value["test"].__or__ = Mock(return_value=mock_chain)
        
        results = run_all()
        
        assert results[0]["meta_score"] == 10.0
        expected = round(0.7 * 10.0 + 0.3 * results[0]["heur_score"], 2)
        assert results[0]["final_score"] == expected

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_diff_truncation(self, mock_prompts, mock_fetch, mock_heur,
                            mock_meta, mock_save):
        """Test that diff is truncated to 4000 chars."""
        mock_prompts.return_value = {"test": Mock()}
        mock_fetch.return_value = "x" * 10000
        mock_heur.return_value = {"length_words": 100, "bullet_points": 5,
                                  "mentions_bug": True, "mentions_suggest": True,
                                  "sections_presence": {}}
        mock_meta.return_value = ({"clarity": 7}, "raw")
        
        mock_chain = Mock()
        mock_chain.invoke.return_value = "review"
        mock_prompts.return_value["test"].__or__ = Mock(return_value=mock_chain)
        
        run_all()
        
        call_args = mock_chain.invoke.call_args[0][0]
        assert len(call_args["diff"]) == 4000

    @patch('accuracy_checker_refactored.time.sleep')
    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    def test_sleep_between_prompts(self, mock_prompts, mock_fetch, mock_heur,
                                   mock_meta, mock_save, mock_sleep):
        """Test that sleep is called between prompt executions."""
        mock_prompts.return_value = {"p1": Mock(), "p2": Mock()}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {"length_words": 100, "bullet_points": 5,
                                  "mentions_bug": True, "mentions_suggest": True,
                                  "sections_presence": {}}
        mock_meta.return_value = ({"clarity": 7}, "raw")
        
        for prompt in mock_prompts.return_value.values():
            mock_chain = Mock()
            mock_chain.invoke.return_value = "review"
            prompt.__or__ = Mock(return_value=mock_chain)
        
        run_all()
        
        assert mock_sleep.call_count >= 1
        mock_sleep.assert_called_with(0.2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])