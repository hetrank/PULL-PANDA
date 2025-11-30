"""
Test suite for run_all function.
Tests integration, file generation, and end-to-end workflow.
"""

import pytest
import os
import csv
from unittest.mock import Mock, patch, mock_open
from accuracy_checker_refactored import run_all


class TestRunAll:
    """Test suite for run_all function."""

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_basic_execution_flow(self, mock_parser, mock_llm, mock_prompts, mock_fetch, mock_heur, 
                                  mock_meta, mock_save):
        """Test basic execution with single prompt."""
        # Setup mocks
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test_prompt": mock_prompt_obj}
        mock_fetch.return_value = "diff content"
        mock_heur.return_value = {
            "length_words": 100,
            "bullet_points": 5,
            "mentions_bug": True,
            "mentions_suggest": True,
            "sections_presence": {"summary": True}
        }
        mock_meta.return_value = (
            {"clarity": 8, "usefulness": 7, "depth": 6, "actionability": 9, "positivity": 7},
            "raw output"
        )
        
        # Mock chain execution - FIXED: return actual string, not Mock
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="test review")
        
        # Set up pipe operators
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        results = run_all(post_to_github=False)
        
        assert len(results) == 1
        assert results[0]["prompt"] == "test_prompt"
        assert "final_score" in results[0]
        assert mock_save.called

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_multiple_prompts_execution(self, mock_parser, mock_llm, mock_prompts, mock_fetch, 
                                       mock_heur, mock_meta, mock_save):
        """Test execution with multiple prompts."""
        # Setup multiple prompts
        mock_prompt_1 = Mock()
        mock_prompt_2 = Mock()
        mock_prompt_3 = Mock()
        mock_prompts.return_value = {
            "prompt_1": mock_prompt_1,
            "prompt_2": mock_prompt_2,
            "prompt_3": mock_prompt_3,
        }
        mock_fetch.return_value = "diff content"
        mock_heur.return_value = {
            "length_words": 100,
            "bullet_points": 5,
            "mentions_bug": True,
            "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = (
            {"clarity": 7, "usefulness": 7, "depth": 7, "actionability": 7, "positivity": 7},
            "raw"
        )
        
        # Mock chain for all prompts
        for prompt in [mock_prompt_1, mock_prompt_2, mock_prompt_3]:
            mock_chain = Mock()
            mock_chain.invoke = Mock(return_value="review")
            prompt.__or__ = Mock(return_value=Mock(
                __or__=Mock(return_value=mock_chain)
            ))
        
        results = run_all()
        
        assert len(results) == 3
        assert all("prompt" in r for r in results)

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_results_sorted_by_final_score(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                          mock_heur, mock_meta, mock_save):
        """Test that results are sorted by final score ascending."""
        mock_high = Mock()
        mock_mid = Mock()
        mock_low = Mock()
        mock_prompts.return_value = {
            "high_score": mock_high,
            "low_score": mock_low,
            "mid_score": mock_mid,
        }
        mock_fetch.return_value = "diff"
        
        # Return different scores for different prompts
        def heur_side_effect(review):
            if "high" in review:
                return {"length_words": 500, "bullet_points": 10, 
                       "mentions_bug": True, "mentions_suggest": True,
                       "sections_presence": {f"s{i}": True for i in range(9)}}
            elif "mid" in review:
                return {"length_words": 200, "bullet_points": 5,
                       "mentions_bug": True, "mentions_suggest": False,
                       "sections_presence": {"s1": True, "s2": True}}
            else:
                return {"length_words": 50, "bullet_points": 0,
                       "mentions_bug": False, "mentions_suggest": False,
                       "sections_presence": {}}
        
        mock_heur.side_effect = heur_side_effect
        mock_meta.return_value = (
            {"clarity": 7, "usefulness": 7, "depth": 7, "actionability": 7, "positivity": 7},
            "raw"
        )
        
        # Setup chains
        for name, prompt in [("high_score", mock_high), ("mid_score", mock_mid), ("low_score", mock_low)]:
            mock_chain = Mock()
            mock_chain.invoke = Mock(return_value=f"{name} review")
            prompt.__or__ = Mock(return_value=Mock(
                __or__=Mock(return_value=mock_chain)
            ))
        
        results = run_all()
        
        # Verify ascending order
        scores = [r["final_score"] for r in results]
        assert scores == sorted(scores)

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_prompt_invoke_exception_handling(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                             mock_heur, mock_meta, mock_save):
        """Test handling when prompt invocation fails."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"failing_prompt": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 0, "bullet_points": 0,
            "mentions_bug": False, "mentions_suggest": False,
            "sections_presence": {}
        }
        mock_meta.return_value = ({"error": "meta failed"}, None)
        
        # Make chain.invoke raise exception
        mock_chain = Mock()
        mock_chain.invoke = Mock(side_effect=Exception("LLM timeout"))
        
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        results = run_all()
        
        assert len(results) == 1
        assert "ERROR" in results[0]["review"]
        assert "LLM timeout" in results[0]["review"]

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_meta_evaluate_failure_uses_heuristic_only(self, mock_parser, mock_llm, mock_prompts,
                                                       mock_fetch, mock_heur,
                                                       mock_meta, mock_save):
        """Test that final score uses only heuristic when meta fails."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 200, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {"summary": True}
        }
        # Meta evaluation fails
        mock_meta.return_value = ({"error": "failed"}, None)
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        results = run_all()
        
        assert results[0]["meta_score"] == "N/A"
        assert results[0]["final_score"] == results[0]["heur_score"]

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_successful_meta_uses_weighted_score(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                                 mock_heur, mock_meta, mock_save):
        """Test that final score uses 70/30 weighting when meta succeeds."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        
        # Set specific scores
        mock_heur.return_value = {
            "length_words": 200, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {"summary": True}
        }
        
        mock_meta.return_value = (
            {"clarity": 10, "usefulness": 10, "depth": 10, 
             "actionability": 10, "positivity": 10},
            "raw"
        )
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        results = run_all()
        
        # final_score should be 0.7 * meta_score + 0.3 * heur_score
        assert results[0]["meta_score"] == 10.0
        expected = round(0.7 * 10.0 + 0.3 * results[0]["heur_score"], 2)
        assert results[0]["final_score"] == expected

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    @patch('builtins.open')
    def test_csv_file_generation(self, mock_file, mock_parser, mock_llm, mock_prompts,
                                 mock_fetch, mock_heur, mock_meta, mock_save):
        """Test that CSV file is created with correct headers."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = (
            {"clarity": 7, "usefulness": 7, "depth": 7,
             "actionability": 7, "positivity": 7},
            "raw"
        )
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        run_all()
        
        # --- CHANGED: check save_text_to_file calls instead of open() ---
        csv_calls = [call for call in mock_save.call_args_list if '.csv' in str(call)]
        assert len(csv_calls) > 0


    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_markdown_report_generation(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                       mock_heur, mock_meta, mock_save):
        """Test that markdown report is generated."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = (
            {"clarity": 7, "usefulness": 7, "depth": 7,
             "actionability": 7, "positivity": 7},
            "raw"
        )
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        run_all()
        
        # Check markdown file was saved
        md_calls = [call for call in mock_save.call_args_list
                   if '.md' in str(call[0][0])]
        assert len(md_calls) > 0

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_individual_review_files_generated(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                              mock_heur, mock_meta, mock_save):
        """Test that individual review files are generated for each prompt."""
        mock_prompt_1 = Mock()
        mock_prompt_2 = Mock()
        mock_prompts.return_value = {
            "prompt_1": mock_prompt_1,
            "prompt_2": mock_prompt_2,
        }
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = (
            {"clarity": 7, "usefulness": 7, "depth": 7,
             "actionability": 7, "positivity": 7},
            "raw"
        )
        
        for prompt in [mock_prompt_1, mock_prompt_2]:
            mock_chain = Mock()
            mock_chain.invoke = Mock(return_value="review")
            prompt.__or__ = Mock(return_value=Mock(
                __or__=Mock(return_value=mock_chain)
            ))
        
        run_all()
        
        # Should save: 1 CSV + 1 MD summary + 2 individual reviews = 4 files
        assert mock_save.call_count >= 4

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_diff_truncation_to_4000_chars(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                          mock_heur, mock_meta, mock_save):
        """Test that diff is truncated to 4000 chars for prompts."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "x" * 10000  # Very long diff
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = ({"clarity": 7, "usefulness": 7, "depth": 7,
                                   "actionability": 7, "positivity": 7}, "raw")
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        run_all()
        
        # Check that chain was invoked with truncated diff
        assert mock_chain.invoke.called
        call_args = mock_chain.invoke.call_args[0][0]
        assert len(call_args["diff"]) == 4000

    @patch('accuracy_checker_refactored.time.sleep')
    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_sleep_between_prompts(self, mock_parser, mock_llm, mock_prompts, mock_fetch, mock_heur,
                                   mock_meta, mock_save, mock_sleep):
        """Test that sleep is called between prompt executions."""
        mock_p1 = Mock()
        mock_p2 = Mock()
        mock_prompts.return_value = {"p1": mock_p1, "p2": mock_p2}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = ({"clarity": 7, "usefulness": 7, "depth": 7,
                                   "actionability": 7, "positivity": 7}, "raw")
        
        for prompt in [mock_p1, mock_p2]:
            mock_chain = Mock()
            mock_chain.invoke = Mock(return_value="review")
            prompt.__or__ = Mock(return_value=Mock(
                __or__=Mock(return_value=mock_chain)
            ))
        
        run_all()
        
        # Sleep should be called between prompts
        assert mock_sleep.call_count >= 1
        mock_sleep.assert_called_with(0.2)

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_post_to_github_parameter_ignored(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                                             mock_heur, mock_meta, mock_save):
        """Test that post_to_github parameter is accepted but unused."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = ({"clarity": 7, "usefulness": 7, "depth": 7,
                                   "actionability": 7, "positivity": 7}, "raw")
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        # Should not raise error with either value
        results_true = run_all(post_to_github=True)
        results_false = run_all(post_to_github=False)
        
        assert len(results_true) > 0
        assert len(results_false) > 0

    @patch('accuracy_checker_refactored.save_text_to_file')
    @patch('accuracy_checker_refactored.meta_evaluate')
    @patch('accuracy_checker_refactored.heuristic_metrics')
    @patch('accuracy_checker_refactored.fetch_pr_diff')
    @patch('accuracy_checker_refactored.get_prompts')
    @patch('accuracy_checker_refactored.llm')
    @patch('accuracy_checker_refactored.parser')
    def test_timing_measurement(self, mock_parser, mock_llm, mock_prompts, mock_fetch,
                               mock_heur, mock_meta, mock_save):
        """Test that execution time is measured for each prompt."""
        mock_prompt_obj = Mock()
        mock_prompts.return_value = {"test": mock_prompt_obj}
        mock_fetch.return_value = "diff"
        mock_heur.return_value = {
            "length_words": 100, "bullet_points": 5,
            "mentions_bug": True, "mentions_suggest": True,
            "sections_presence": {}
        }
        mock_meta.return_value = ({"clarity": 7, "usefulness": 7, "depth": 7,
                                   "actionability": 7, "positivity": 7}, "raw")
        
        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value="review")
        mock_prompt_obj.__or__ = Mock(return_value=Mock(
            __or__=Mock(return_value=mock_chain)
        ))
        
        results = run_all()
        
        assert "time_s" in results[0]
        assert isinstance(results[0]["time_s"], (int, float))
        assert results[0]["time_s"] >= 0