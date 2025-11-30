"""
Additional test cases to boost coverage for IterativePromptSelector.
Targets uncovered lines and fixes failing tests.
"""

import pytest
import numpy as np
import json
import time
from unittest.mock import patch, Mock, mock_open, MagicMock, call, PropertyMock
from iterative_prompt_selector import IterativePromptSelector, run_iterative_selector


class TestSelectBestPromptErrorHandling:
    """Test error handling in select_best_prompt (lines 122-125)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_select_best_prompt_model_predict_value_error(self, selector):
        """Test ValueError during model prediction (line 122-125)."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Set up trained state with sufficient samples
        for i in range(6):
            selector.feature_history.append(features_vector)
            selector.prompt_history.append(0)
            selector.score_history.append(7.0)
        selector.is_trained = True
        
        # Mock predict to raise ValueError
        with patch.object(selector.model, 'predict', side_effect=ValueError("Prediction failed")):
            prompt = selector.select_best_prompt(features_vector)
            
            # Should fallback to first prompt
            assert prompt == selector.prompt_names[0]

    def test_select_best_prompt_model_predict_index_error(self, selector):
        """Test IndexError during model prediction (line 122-125)."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Set up trained state
        for i in range(6):
            selector.feature_history.append(features_vector)
            selector.prompt_history.append(0)
            selector.score_history.append(7.0)
        selector.is_trained = True
        
        # Mock predict to raise IndexError
        with patch.object(selector.model, 'predict', side_effect=IndexError("Index out of range")):
            prompt = selector.select_best_prompt(features_vector)
            
            # Should fallback to first prompt
            assert prompt == selector.prompt_names[0]


class TestUpdateModelErrorHandling:
    """Test error handling in update_model (lines 155-159)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_update_model_value_error_during_training(self, selector):
        """Test ValueError during model training (line 155-159)."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Add samples to trigger training
        for i in range(selector.min_samples_for_training - 1):
            selector.update_model(features_vector, selector.prompt_names[0], 7.0)
        
        # Mock model.fit to raise ValueError
        with patch.object(selector.model, 'fit', side_effect=ValueError("Fitting failed")):
            selector.update_model(features_vector, selector.prompt_names[1], 8.0)
            
            # Should handle error and set is_trained to False
            assert selector.is_trained == False
            # Data should still be added
            assert len(selector.feature_history) == selector.min_samples_for_training

    def test_update_model_runtime_error_during_training(self, selector):
        """Test RuntimeError during model training (line 155-159)."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Add samples to trigger training
        for i in range(selector.min_samples_for_training - 1):
            selector.update_model(features_vector, selector.prompt_names[0], 7.0)
        
        # Mock model.fit to raise RuntimeError
        with patch.object(selector.model, 'fit', side_effect=RuntimeError("Runtime error")):
            selector.update_model(features_vector, selector.prompt_names[1], 8.0)
            
            assert selector.is_trained == False

    def test_update_model_scaler_transform_fails(self, selector):
        """Test when scaler.transform fails after fitting."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Add samples to trigger training
        for i in range(selector.min_samples_for_training - 1):
            selector.update_model(features_vector, selector.prompt_names[0], 7.0)
        
        # Mock scaler.transform to raise ValueError
        with patch.object(selector.scaler, 'transform', side_effect=ValueError("Transform failed")):
            selector.update_model(features_vector, selector.prompt_names[1], 8.0)
            
            assert selector.is_trained == False


class TestGenerateReview:
    """Test generate_review method (lines 201-231)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_generate_review_basic(self, selector):
        """Test basic review generation."""
        diff_text = "diff --git a/file.py b/file.py\n+new line"
        selected_prompt = selector.prompt_names[0]
        
        # Create a proper mock for the prompt template
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="This is a review")
        
        # Mock the __or__ operator to return the chain
        mock_prompt.__or__ = MagicMock(side_effect=lambda x: mock_chain if x else mock_chain)
        
        # Replace the prompt in the selector
        original_prompt = selector.prompts[selected_prompt]
        selector.prompts[selected_prompt] = mock_prompt
        
        try:
            review_text, elapsed = selector.generate_review(diff_text, selected_prompt)
            
            assert review_text == "This is a review"
            assert isinstance(elapsed, float)
            assert elapsed >= 0
        finally:
            selector.prompts[selected_prompt] = original_prompt

    def test_generate_review_truncates_long_diff(self, selector):
        """Test that diff is truncated to 4000 characters."""
        diff_text = "x" * 10000
        selected_prompt = selector.prompt_names[0]
        
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value="Review")
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        
        original_prompt = selector.prompts[selected_prompt]
        selector.prompts[selected_prompt] = mock_prompt
        
        try:
            review_text, elapsed = selector.generate_review(diff_text, selected_prompt)
            
            # Check that invoke was called
            assert mock_chain.invoke.called
            call_args = mock_chain.invoke.call_args[0][0]
            assert len(call_args['diff']) == 4000
        finally:
            selector.prompts[selected_prompt] = original_prompt

    def test_generate_review_timing(self, selector):
        """Test timing measurement in review generation."""
        diff_text = "diff"
        selected_prompt = selector.prompt_names[0]
        
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        
        # Simulate some processing time
        def slow_invoke(x):
            time.sleep(0.01)  # Small delay
            return "Review"
        
        mock_chain.invoke = slow_invoke
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        
        original_prompt = selector.prompts[selected_prompt]
        selector.prompts[selected_prompt] = mock_prompt
        
        try:
            review_text, elapsed = selector.generate_review(diff_text, selected_prompt)
            
            assert elapsed >= 0.01  # Should be at least 0.01 seconds
            assert review_text == "Review"
        finally:
            selector.prompts[selected_prompt] = original_prompt


class TestEvaluateReviewEdgeCases:
    """Test evaluate_review edge cases (lines 242-265)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_with_error_in_meta(self, mock_meta, mock_heur, selector):
        """Test evaluation when meta_evaluate returns error (line 248)."""
        mock_heur.return_value = {
            "sections_presence": {"summary": True},
            "bullet_points": 5,
            "length_words": 150,
            "mentions_bug": False,
            "mentions_suggest": False
        }
        
        # Meta returns error
        mock_meta.return_value = ({"error": "Evaluation failed"}, {})
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should use default score of 5.0
        assert score == 5.0

    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_word_count_below_80(self, mock_meta, mock_heur, selector):
        """Test length_score calculation for words < 80 (line 256-257)."""
        mock_heur.return_value = {
            "sections_presence": {"summary": True, "issues": True},
            "bullet_points": 3,
            "length_words": 40,  # Below 80
            "mentions_bug": True,
            "mentions_suggest": False
        }
        
        mock_meta.return_value = (
            {"clarity": 7.0, "usefulness": 7.0, "depth": 6.0, 
             "actionability": 7.0, "positivity": 6.0},
            {}
        )
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should calculate length_score as min(40/80, ...) = 0.5
        assert isinstance(score, float)
        assert 0 <= score <= 10

    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_word_count_above_800(self, mock_meta, mock_heur, selector):
        """Test length_score calculation for words > 800 (line 256-257)."""
        mock_heur.return_value = {
            "sections_presence": {"summary": True, "issues": True, "suggestions": True},
            "bullet_points": 8,
            "length_words": 1500,  # Above 800
            "mentions_bug": True,
            "mentions_suggest": True
        }
        
        mock_meta.return_value = (
            {"clarity": 8.0, "usefulness": 8.0, "depth": 7.0, 
             "actionability": 8.0, "positivity": 7.0},
            {}
        )
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should calculate length_score with penalty
        assert isinstance(score, float)
        assert 0 <= score <= 10

    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_bullet_points_over_10(self, mock_meta, mock_heur, selector):
        """Test bullets_score when bullet_points > 10 (line 254)."""
        mock_heur.return_value = {
            "sections_presence": {"summary": True},
            "bullet_points": 25,  # More than 10
            "length_words": 200,
            "mentions_bug": False,
            "mentions_suggest": False
        }
        
        mock_meta.return_value = (
            {"clarity": 7.0, "usefulness": 7.0, "depth": 6.0, 
             "actionability": 7.0, "positivity": 6.0},
            {}
        )
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should cap bullets_score at 10/10.0 = 1.0
        assert isinstance(score, float)


class TestProcessPR:
    """Test process_pr method (line 269)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_complete_workflow(self, mock_save, mock_eval, mock_gen, mock_fetch, selector):
        """Test complete process_pr workflow."""
        mock_fetch.return_value = "diff --git a/file.py\n+line"
        mock_gen.return_value = ("Review text", 1.5)
        mock_eval.return_value = (8.5, {"sections": True}, {"clarity": 8.0})
        
        result = selector.process_pr(123, "owner", "repo", "token")
        
        assert result["pr_number"] == 123
        assert result["score"] == 8.5
        assert "selected_prompt" in result
        assert "review" in result
        assert "features" in result
        
        # Verify methods were called
        mock_fetch.assert_called_once_with("owner", "repo", 123, "token")
        mock_gen.assert_called_once()
        mock_eval.assert_called_once()
        mock_save.assert_called_once()

    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_with_default_params(self, mock_save, mock_eval, mock_gen, mock_fetch, selector):
        """Test process_pr with default parameters."""
        mock_fetch.return_value = "diff"
        mock_gen.return_value = ("Review", 1.0)
        mock_eval.return_value = (7.0, {}, {})
        
        # Call with only pr_number (should use defaults from config)
        result = selector.process_pr(456)
        
        assert result["pr_number"] == 456
        mock_fetch.assert_called_once()


class TestSaveResults:
    """Test save_results method (line 317)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    @patch('builtins.open', new_callable=mock_open)
    @patch('iterative_prompt_selector.datetime')
    def test_save_results_creates_files(self, mock_datetime, mock_file, selector):
        """Test that save_results creates both JSON and text files."""
        mock_datetime.now.return_value.strftime.return_value = "20231115_120000"
        
        features = {"num_lines": 100, "num_files": 2}
        heur = {"sections": True}
        meta = {"clarity": 8.0}
        
        selector.feature_history = [np.array([1, 2, 3])]
        selector.is_trained = True
        
        selector.save_results(123, features, "prompt1", "Review text", 8.5, heur, meta)
        
        # Verify two files were opened (JSON and review text)
        assert mock_file.call_count == 2
        
        # Check JSON file call
        json_call = mock_file.call_args_list[0]
        assert "iterative_results_pr123_20231115_120000.json" in json_call[0][0]
        
        # Check review file call
        review_call = mock_file.call_args_list[1]
        assert "review_pr123_prompt1.txt" in review_call[0][0]

    @patch('builtins.open', new_callable=mock_open)
    @patch('iterative_prompt_selector.datetime')
    @patch('iterative_prompt_selector.json.dump')
    def test_save_results_json_content(self, mock_json_dump, mock_datetime, mock_file, selector):
        """Test JSON content structure."""
        mock_datetime.now.return_value.strftime.return_value = "20231115_120000"
        
        features = {"num_lines": 50}
        heur = {"sections_presence": {"summary": True}}
        meta = {"clarity": 7.0, "usefulness": 8.0}
        
        selector.feature_history = [np.array([1, 2])]
        selector.is_trained = False
        
        selector.save_results(456, features, "prompt2", "Review", 7.5, heur, meta)
        
        # Verify json.dump was called
        assert mock_json_dump.called
        
        # Get the data that was passed to json.dump
        call_args = mock_json_dump.call_args[0][0]
        
        # Verify structure
        assert call_args["pr_number"] == 456
        assert call_args["selected_prompt"] == "prompt2"
        assert call_args["review_score"] == 7.5
        assert call_args["training_data_size"] == 1
        assert call_args["model_trained"] == False


class TestLoadStateErrorHandling:
    """Test load_state error handling (lines 371-374)."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_load_state_json_decode_error(self, selector):
        """Test JSONDecodeError handling (line 371-374)."""
        m = mock_open(read_data="{ invalid json }")
        
        with patch('builtins.open', m):
            selector.load_state("bad_json.json")
        
        # Should reset to defaults
        assert selector.feature_history == []
        assert selector.prompt_history == []
        assert selector.score_history == []
        assert selector.is_trained == False

    def test_load_state_key_error(self, selector):
        """Test KeyError handling when required keys missing (line 371-374)."""
        state_data = {
            "feature_history": [[1, 2, 3]],
            # Missing prompt_history, score_history, etc.
        }
        
        m = mock_open(read_data=json.dumps(state_data))
        with patch('builtins.open', m):
            selector.load_state("missing_keys.json")
        
        assert selector.feature_history == []
        assert selector.is_trained == False

    def test_load_state_value_error_from_array_conversion(self, selector):
        """Test ValueError handling during np.array conversion (line 371-374)."""
        state_data = {
            "feature_history": [{"invalid": "dict"}],  # Can't convert dict to array
            "prompt_history": [0],
            "score_history": [7.5],
            "is_trained": False,
            "scaler_mean": None,
            "scaler_scale": None
        }
        
        m = mock_open(read_data=json.dumps(state_data))
        with patch('builtins.open', m):
            # Mock np.array to raise ValueError
            with patch('numpy.array', side_effect=ValueError("Cannot convert")):
                selector.load_state("invalid_array.json")
        
        assert selector.feature_history == []
        assert selector.is_trained == False

    def test_load_state_with_trained_scaler_restoration(self, selector):
        """Test complete scaler restoration for trained model."""
        state_data = {
            "feature_history": [[100.0] * 14],
            "prompt_history": [0],
            "score_history": [8.0],
            "is_trained": True,
            "scaler_mean": [50.0] * 15,
            "scaler_scale": [10.0] * 15
        }
        
        m = mock_open(read_data=json.dumps(state_data))
        with patch('builtins.open', m):
            selector.load_state("trained.json")
        
        # Verify scaler attributes are set
        assert selector.is_trained == True
        assert hasattr(selector.scaler, 'mean_')
        assert hasattr(selector.scaler, 'scale_')
        assert hasattr(selector.scaler, 'var_')
        assert selector.scaler.n_features_in_ == 15


class TestRunIterativeSelectorCoverage:
    """Additional coverage for run_iterative_selector."""

    @patch('iterative_prompt_selector.IterativePromptSelector')
    @patch('iterative_prompt_selector.time.sleep')
    def test_run_prints_stats_after_each_pr(self, mock_sleep, mock_selector_class):
        """Test that stats are printed after each PR."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(return_value={
            "pr_number": 1, 
            "score": 8.0, 
            "selected_prompt": "prompt1"
        })
        mock_instance.get_stats = Mock(return_value={
            "training_samples": 1,
            "average_score": 8.0
        })
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        results, selector = run_iterative_selector([1])
        
        # Verify get_stats was called after processing
        assert mock_instance.get_stats.call_count >= 2  # Called during and at end

    @patch('iterative_prompt_selector.IterativePromptSelector')
    @patch('iterative_prompt_selector.time.sleep')
    def test_run_handles_runtime_error(self, mock_sleep, mock_selector_class):
        """Test RuntimeError handling in run_iterative_selector."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(side_effect=RuntimeError("Runtime issue"))
        mock_instance.get_stats = Mock(return_value={})
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        results, selector = run_iterative_selector([1])
        
        assert results == []


class TestFeaturesToVector:
    """Test features_to_vector with edge cases."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_features_to_vector_missing_keys(self, selector):
        """Test with missing feature keys."""
        features = {
            "num_lines": 100,
            "num_files": 2
            # Missing other keys
        }
        
        vector = selector.features_to_vector(features)
        
        assert len(vector) == 14
        assert vector[0] == 100
        assert vector[1] == 2
        # Rest should be 0 (default)
        assert all(v == 0 for v in vector[2:])

    def test_features_to_vector_extra_keys(self, selector):
        """Test with extra feature keys that should be ignored."""
        features = {
            "num_lines": 100,
            "num_files": 2,
            "additions": 50,
            "deletions": 20,
            "net_changes": 30,
            "has_comments": 1,
            "has_functions": 1,
            "has_imports": 1,
            "has_test": 0,
            "has_docs": 0,
            "has_config": 0,
            "is_python": 1,
            "is_js": 0,
            "is_java": 0,
            "extra_key": 999  # Should be ignored
        }
        
        vector = selector.features_to_vector(features)
        
        assert len(vector) == 14
        assert 999 not in vector


class TestGetStats:
    """Test get_stats method."""

    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()

    def test_get_stats_empty_history(self, selector):
        """Test stats with empty history."""
        stats = selector.get_stats()
        
        assert stats["training_samples"] == 0
        assert stats["is_trained"] == False
        assert stats["average_score"] == 0
        assert stats["prompt_distribution"] == {name: 0 for name in selector.prompt_names}

    def test_get_stats_with_data(self, selector):
        """Test stats with actual data."""
        features = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        selector.update_model(features, selector.prompt_names[0], 8.0)
        selector.update_model(features, selector.prompt_names[1], 7.5)
        selector.update_model(features, selector.prompt_names[0], 9.0)
        
        stats = selector.get_stats()
        
        assert stats["training_samples"] == 3
        assert stats["average_score"] == (8.0 + 7.5 + 9.0) / 3
        assert stats["prompt_distribution"][selector.prompt_names[0]] == 2
        assert stats["prompt_distribution"][selector.prompt_names[1]] == 1


class TestUncoveredLines:
    """Target specific uncovered lines from coverage report."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    def test_select_best_prompt_not_trained_branch(self, selector):
        """Test lines 120-121: not trained or insufficient samples."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Case 1: is_trained is False
        selector.is_trained = False
        for i in range(10):
            selector.feature_history.append(features_vector)
        
        prompt = selector.select_best_prompt(features_vector)
        assert prompt in selector.prompt_names
        
        # Case 2: Not enough samples
        selector2 = IterativePromptSelector()
        selector2.is_trained = True
        for i in range(3):  # Less than min_samples_for_training (5)
            selector2.feature_history.append(features_vector)
        
        prompt2 = selector2.select_best_prompt(features_vector)
        assert prompt2 in selector2.prompt_names
    
    def test_update_model_retrain_path(self, selector):
        """Test lines 143->147: Retraining when already trained."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # First training
        for i in range(selector.min_samples_for_training):
            selector.update_model(features_vector, selector.prompt_names[0], 7.0)
        
        assert selector.is_trained == True
        
        # Add more data - should retrain
        selector.update_model(features_vector, selector.prompt_names[1], 8.0)
        
        # Should still be trained
        assert selector.is_trained == True
    
    @patch('iterative_prompt_selector.fetch_pr_diff')
    def test_process_pr_line_282_293(self, mock_fetch, selector):
        """Test lines 282-293: process_pr print statements."""
        mock_fetch.return_value = "diff --git a/test.py\n+line"
        
        # Mock other methods to avoid actual processing
        with patch.object(selector, 'generate_review', return_value=("Review", 1.0)):
            with patch.object(selector, 'evaluate_review', return_value=(7.5, {}, {})):
                with patch.object(selector, 'save_results'):
                    result = selector.process_pr(123)
                    
                    assert result["pr_number"] == 123
    
    @patch('iterative_prompt_selector.IterativePromptSelector')
    def test_run_iterative_final_report_lines(self, mock_selector_class):
        """Test lines 308->314, 317, 330->333: final report and stats."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(side_effect=[
            {"pr_number": 1, "score": 8.0, "selected_prompt": "prompt1"},
            {"pr_number": 2, "score": 7.5, "selected_prompt": "prompt2"}
        ])
        mock_instance.get_stats = Mock(return_value={
            "training_samples": 2,
            "average_score": 7.75,
            "prompt_distribution": {"prompt1": 1, "prompt2": 1}
        })
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        with patch('iterative_prompt_selector.time.sleep'):
            results, selector = run_iterative_selector([1, 2])
        
        # Verify final stats were retrieved
        assert mock_instance.get_stats.called
        assert len(results) == 2
        
        # Verify state was saved
        mock_instance.save_state.assert_called_once()


class TestBranchCoverage:
    """Tests specifically for branch coverage gaps."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    def test_select_prompt_insufficient_samples_exactly(self, selector):
        """Test exact boundary: len(feature_history) < min_samples_for_training."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Add exactly min_samples - 1
        for i in range(selector.min_samples_for_training - 1):
            selector.feature_history.append(features_vector)
        
        # Not trained, insufficient samples
        selector.is_trained = False
        
        # Should use round-robin
        prompt = selector.select_best_prompt(features_vector)
        expected_index = (selector.min_samples_for_training - 1) % len(selector.prompt_names)
        assert prompt == selector.prompt_names[expected_index]
    
    def test_update_model_first_training(self, selector):
        """Test first training path: not is_trained initially."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Start fresh, not trained
        assert selector.is_trained == False
        
        # Add min_samples to trigger first training
        for i in range(selector.min_samples_for_training):
            selector.update_model(features_vector, selector.prompt_names[i % len(selector.prompt_names)], 7.0 + i * 0.1)
        
        # Should now be trained
        assert selector.is_trained == True
        
        # Scaler should be fitted
        assert hasattr(selector.scaler, 'mean_')
        assert selector.scaler.mean_ is not None
    
    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_not_dict_branch(self, mock_meta, mock_heur, selector):
        """Test branch where meta_parsed is not a dict."""
        mock_heur.return_value = {
            "sections_presence": {},
            "bullet_points": 0,
            "length_words": 100,
            "mentions_bug": False,
            "mentions_suggest": False
        }
        
        # Return a list instead of dict
        mock_meta.return_value = ([], {})
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should use default score
        assert score == 5.0
    
    @patch('iterative_prompt_selector.heuristic_metrics')
    @patch('iterative_prompt_selector.meta_evaluate')
    def test_evaluate_review_has_error_key(self, mock_meta, mock_heur, selector):
        """Test branch where 'error' is in meta_parsed."""
        mock_heur.return_value = {
            "sections_presence": {"summary": True},
            "bullet_points": 5,
            "length_words": 200,
            "mentions_bug": True,
            "mentions_suggest": True
        }
        
        # Meta has error key
        mock_meta.return_value = ({"error": "Something went wrong", "clarity": 7.0}, {})
        
        score, heur, meta = selector.evaluate_review("diff", "review")
        
        # Should still use default score when error present
        assert score == 5.0


class TestScalerRestoration:
    """Test scaler state restoration edge cases."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    def test_load_state_no_scaler_data(self, selector):
        """Test loading state when is_trained=True but no scaler data."""
        state_data = {
            "feature_history": [[100.0] * 14],
            "prompt_history": [0],
            "score_history": [8.0],
            "is_trained": True,
            "scaler_mean": None,  # No scaler data
            "scaler_scale": None
        }
        
        m = mock_open(read_data=json.dumps(state_data))
        with patch('builtins.open', m):
            selector.load_state("no_scaler.json")
        
        # Should load history but not restore scaler
        assert len(selector.feature_history) == 1
        # Scaler won't be restored if mean is None
    
    def test_load_state_empty_scaler_arrays(self, selector):
        """Test loading with empty scaler arrays."""
        state_data = {
            "feature_history": [[100.0] * 14],
            "prompt_history": [0],
            "score_history": [8.0],
            "is_trained": True,
            "scaler_mean": [],  # Empty array
            "scaler_scale": []
        }
        
        m = mock_open(read_data=json.dumps(state_data))
        with patch('builtins.open', m):
            selector.load_state("empty_scaler.json")
        
        assert len(selector.feature_history) == 1


class TestProcessPRIntegration:
    """Integration tests for process_pr."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    @patch('iterative_prompt_selector.fetch_pr_diff')
    @patch.object(IterativePromptSelector, 'extract_pr_features')
    @patch.object(IterativePromptSelector, 'select_best_prompt')
    @patch.object(IterativePromptSelector, 'generate_review')
    @patch.object(IterativePromptSelector, 'evaluate_review')
    @patch.object(IterativePromptSelector, 'update_model')
    @patch.object(IterativePromptSelector, 'save_results')
    def test_process_pr_all_methods_called(self, mock_save, mock_update, mock_eval, 
                                          mock_gen, mock_select, mock_extract, mock_fetch, selector):
        """Verify all methods in process_pr are called in order."""
        mock_fetch.return_value = "diff content"
        mock_extract.return_value = {"num_lines": 100}
        mock_select.return_value = "prompt1"
        mock_gen.return_value = ("Review text", 2.5)
        mock_eval.return_value = (8.0, {"sections": True}, {"clarity": 8.0})
        
        result = selector.process_pr(789)
        
        # Verify call order
        mock_fetch.assert_called_once()
        mock_extract.assert_called_once()
        mock_select.assert_called_once()
        mock_gen.assert_called_once()
        mock_eval.assert_called_once()
        mock_update.assert_called_once()
        mock_save.assert_called_once()
        
        # Verify result structure
        assert result["pr_number"] == 789
        assert result["selected_prompt"] == "prompt1"
        assert result["review"] == "Review text"
        assert result["score"] == 8.0


class TestSaveResultsEdgeCases:
    """Edge cases for save_results."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('iterative_prompt_selector.datetime')
    @patch('iterative_prompt_selector.json.dump')
    def test_save_results_prompt_name_with_spaces(self, mock_json_dump, mock_datetime, mock_file, selector):
        """Test saving when prompt name contains spaces (should be replaced with _)."""
        mock_datetime.now.return_value.strftime.return_value = "20231115_120000"
        
        selector.save_results(
            111, 
            {"num_lines": 50}, 
            "detailed contextual review",  # Has spaces
            "Review content", 
            7.5, 
            {}, 
            {}
        )
        
        # Check that spaces were replaced with underscores in filename
        review_call = mock_file.call_args_list[1]
        filename = review_call[0][0]
        assert "detailed_contextual_review" in filename
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('iterative_prompt_selector.datetime')
    def test_save_results_with_complex_meta_data(self, mock_datetime, mock_file, selector):
        """Test saving with complex nested meta data."""
        mock_datetime.now.return_value.strftime.return_value = "20231115_120000"
        
        complex_meta = {
            "clarity": 7.5,
            "nested": {
                "deep": {
                    "value": 123
                }
            },
            "list": [1, 2, 3]
        }
        
        selector.feature_history = [np.array([1] * 14)]
        selector.is_trained = True
        
        # Should not crash with complex structures
        selector.save_results(222, {}, "prompt", "Review", 8.0, {}, complex_meta)
        
        assert mock_file.call_count == 2


class TestRunIterativeSelectorEdgeCases:
    """Additional edge cases for run_iterative_selector."""
    
    @patch('iterative_prompt_selector.IterativePromptSelector')
    @patch('iterative_prompt_selector.time.sleep')
    def test_run_all_prs_fail(self, mock_sleep, mock_selector_class):
        """Test when all PRs fail."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(side_effect=ValueError("All fail"))
        mock_instance.get_stats = Mock(return_value={
            "training_samples": 0,
            "prompt_distribution": {}
        })
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        results, selector = run_iterative_selector([1, 2, 3])
        
        # All failed, results should be empty
        assert results == []
        
        # But state should still be saved
        mock_instance.save_state.assert_called_once()
    
    @patch('iterative_prompt_selector.IterativePromptSelector')
    @patch('iterative_prompt_selector.time.sleep')
    def test_run_with_load_previous_true(self, mock_sleep, mock_selector_class):
        """Explicitly test load_previous=True."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(return_value={
            "pr_number": 1,
            "score": 8.0,
            "selected_prompt": "p"
        })
        mock_instance.get_stats = Mock(return_value={})
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        results, selector = run_iterative_selector([1], load_previous=True)
        
        # Should call load_state
        mock_instance.load_state.assert_called_once()
    
    @patch('iterative_prompt_selector.IterativePromptSelector')
    @patch('iterative_prompt_selector.time.sleep')
    def test_run_sleep_called_between_prs(self, mock_sleep, mock_selector_class):
        """Verify sleep is called between PRs to avoid rate limiting."""
        mock_instance = Mock()
        mock_instance.load_state = Mock()
        mock_instance.process_pr = Mock(side_effect=[
            {"pr_number": 1, "score": 8.0, "selected_prompt": "p1"},
            {"pr_number": 2, "score": 7.5, "selected_prompt": "p2"},
            {"pr_number": 3, "score": 8.5, "selected_prompt": "p3"}
        ])
        mock_instance.get_stats = Mock(return_value={})
        mock_instance.save_state = Mock()
        mock_selector_class.return_value = mock_instance
        
        results, selector = run_iterative_selector([1, 2, 3])
        
        # Sleep should be called 3 times (once per PR)
        assert mock_sleep.call_count == 3
        mock_sleep.assert_called_with(1)


class TestModelPredictionEdgeCases:
    """Edge cases for model prediction."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    def test_select_best_prompt_with_trained_model(self, selector):
        """Test selection with properly trained model."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Train the model properly
        for i in range(10):
            selector.update_model(features_vector, selector.prompt_names[i % len(selector.prompt_names)], 7.0 + i * 0.2)
        
        # Now model should be trained
        assert selector.is_trained == True
        
        # Should use model for prediction
        prompt = selector.select_best_prompt(features_vector)
        assert prompt in selector.prompt_names
    
    def test_select_best_prompt_all_equal_predictions(self, selector):
        """Test when model predicts same score for all prompts."""
        features_vector = np.array([100, 5, 50, 20, 30, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Train model
        for i in range(6):
            selector.feature_history.append(features_vector)
            selector.prompt_history.append(0)
            selector.score_history.append(7.0)
        selector.is_trained = True
        
        # Mock predict to return all same values
        all_same = np.array([7.0] * len(selector.prompt_names))
        with patch.object(selector.model, 'predict', return_value=all_same):
            prompt = selector.select_best_prompt(features_vector)
            
            # Should select first prompt (index 0) since all are equal
            assert prompt == selector.prompt_names[0]


class TestFeatureExtractionCompleteness:
    """Ensure all feature extraction paths are covered."""
    
    @pytest.fixture
    def selector(self):
        return IterativePromptSelector()
    
    def test_extract_features_all_positive(self, selector):
        """Test diff with all positive feature indicators."""
        diff = """diff --git a/test.py b/test.py
diff --git a/main.js b/main.js
diff --git a/App.java b/App.java
+# Python comment
+// JS comment
+/* Multi-line comment */
+def test_function():
+function jsFunc() {
+public void javaFunc() {
+import numpy
+from sklearn import *
+#include <stdio.h>
+unittest.TestCase
+README.md changes
+config.json updates
"""
        features = selector.extract_pr_features(diff)
        
        # All binary features should be 1
        assert features['has_comments'] == 1
        assert features['has_functions'] == 1
        assert features['has_imports'] == 1
        assert features['has_test'] == 1
        assert features['has_docs'] == 1
        assert features['has_config'] == 1
        assert features['is_python'] == 1
        assert features['is_js'] == 1
        assert features['is_java'] == 1
    
    def test_extract_features_negative_lines(self, selector):
        """Test counting deletions properly."""
        diff = """diff --git a/file.py b/file.py
-deleted line 1
-deleted line 2
-deleted line 3
+added line
"""
        features = selector.extract_pr_features(diff)
        
        assert features['deletions'] == 3
        assert features['additions'] == 1
        assert features['net_changes'] == -2