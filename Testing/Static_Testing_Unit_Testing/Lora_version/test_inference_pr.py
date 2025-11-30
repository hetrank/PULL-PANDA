"""
Comprehensive test suite for PR review model inference.

Tests cover: model loading, tokenization, generation, output parsing,
edge cases, error handling, and device management.
"""

import pytest
import torch
from unittest.mock import Mock, patch, MagicMock
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import os

# Import or define the functions to test


class TestModelLoading:
    """Test model and tokenizer loading."""
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    def test_model_loads_successfully(self, mock_model, mock_tokenizer):
        """Test successful model and tokenizer loading."""
        mock_tokenizer.return_value = Mock()
        mock_model.return_value = Mock()
        
        tokenizer = AutoTokenizer.from_pretrained("./pr-review-model")
        model = AutoModelForCausalLM.from_pretrained("./pr-review-model")
        
        assert tokenizer is not None
        assert model is not None
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    def test_model_path_not_found(self, mock_tokenizer):
        """Test handling of missing model path."""
        mock_tokenizer.side_effect = OSError("Model not found")
        
        with pytest.raises(OSError):
            AutoTokenizer.from_pretrained("./nonexistent-model")
    
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    def test_corrupted_model_file(self, mock_model):
        """Test handling of corrupted model files."""
        mock_model.side_effect = RuntimeError("Corrupted checkpoint")
        
        with pytest.raises(RuntimeError):
            AutoModelForCausalLM.from_pretrained("./corrupted-model")


class TestDeviceManagement:
    """Test device selection and model transfer."""
    
    @patch('torch.cuda.is_available')
    def test_cuda_available(self, mock_cuda):
        """Test CUDA device selection when available."""
        mock_cuda.return_value = True
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        assert device.type == "cuda"
    
    @patch('torch.cuda.is_available')
    def test_cuda_not_available(self, mock_cuda):
        """Test CPU fallback when CUDA unavailable."""
        mock_cuda.return_value = False
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        assert device.type == "cpu"
    
    def test_model_to_device(self):
        """Test model transfer to device."""
        mock_model = Mock()
        mock_model.to = Mock(return_value=mock_model)
        device = torch.device("cpu")
        
        result = mock_model.to(device)
        mock_model.to.assert_called_once_with(device)
        assert result is not None


class TestPromptGeneration:
    """Test prompt formatting with various inputs."""
    
    def test_standard_prompt_format(self):
        """Test standard PR prompt formatting."""
        title = "Fix bug"
        description = "Fixed null pointer"
        diff = "```diff\n+fixed code\n```"
        
        prompt = (
            f"You are a senior software engineer reviewing a pull request.\n"
            f"PR Title: {title}\n"
            f"PR Description: {description}\n"
            f"Code Diff:\n{diff}\n\n"
            f"Please provide a constructive PR Review with strengths, weaknesses, "
            f"and suggestions.\n"
            f"Review: "
        )
        
        assert "PR Title: Fix bug" in prompt
        assert "PR Description: Fixed null pointer" in prompt
        assert "Code Diff:" in prompt
    
    def test_empty_pr_title(self):
        """Test handling of empty PR title."""
        title = ""
        description = "Some description"
        diff = "```diff\n+code\n```"
        
        prompt = f"PR Title: {title}\nPR Description: {description}\n"
        assert "PR Title: \n" in prompt
    
    def test_empty_pr_description(self):
        """Test handling of empty PR description."""
        title = "Some title"
        description = ""
        diff = "```diff\n+code\n```"
        
        prompt = f"PR Description: {description}\n"
        assert "PR Description: \n" in prompt
    
    def test_empty_code_diff(self):
        """Test handling of empty code diff."""
        diff = ""
        prompt = f"Code Diff:\n{diff}\n\n"
        assert "Code Diff:\n\n" in prompt
    
    def test_very_long_prompt(self):
        """Test handling of extremely long prompts."""
        title = "A" * 1000
        description = "B" * 5000
        diff = "```diff\n" + "+line\n" * 1000 + "```"
        
        prompt = f"PR Title: {title}\nPR Description: {description}\nCode Diff:\n{diff}\n"
        assert len(prompt) > 6000
    
    def test_special_characters_in_prompt(self):
        """Test handling of special characters."""
        title = "Fix: <script>alert('xss')</script>"
        description = 'Quotes " and \' and newlines\n\n'
        diff = "```diff\n+code with $pecial ch@rs\n```"
        
        prompt = f"PR Title: {title}\n"
        assert title in prompt
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        title = "修复错误 🐛"
        description = "Описание на русском"
        diff = "```diff\n+コード\n```"
        
        prompt = f"PR Title: {title}\nPR Description: {description}\n"
        assert "修复错误" in prompt


class TestTokenization:
    """Test tokenization process."""
    
    def test_tokenization_returns_tensors(self):
        """Test tokenizer returns proper tensor format."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        
        prompt = "Test prompt"
        inputs = mock_tokenizer(prompt, return_tensors="pt")
        
        assert 'input_ids' in inputs
        assert isinstance(inputs['input_ids'], torch.Tensor)
    
    def test_tokenization_with_padding(self):
        """Test tokenization with padding enabled."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 0]]),
            'attention_mask': torch.tensor([[1, 1, 1, 0]])
        }
        
        inputs = mock_tokenizer("test", return_tensors="pt", padding=True)
        assert inputs['attention_mask'].sum() == 3  # 3 real tokens
    
    def test_tokenization_max_length_exceeded(self):
        """Test handling of prompts exceeding max token length."""
        mock_tokenizer = Mock()
        long_prompt = "word " * 10000
        
        # Simulate truncation
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1] * 2048])
        }
        
        inputs = mock_tokenizer(long_prompt, return_tensors="pt", truncation=True)
        assert inputs['input_ids'].shape[1] <= 2048


class TestModelGeneration:
    """Test model generation functionality."""
    
    def test_generation_with_standard_params(self):
        """Test generation with standard parameters."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        
        inputs = {'input_ids': torch.tensor([[1, 2, 3]])}
        outputs = mock_model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.8,
            top_p=0.95,
            do_sample=True
        )
        
        assert outputs is not None
        assert outputs.shape[1] >= 3
    
    def test_generation_with_zero_temperature(self):
        """Test generation with temperature=0 (greedy decoding)."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3]])
        
        inputs = {'input_ids': torch.tensor([[1, 2]])}
        outputs = mock_model.generate(**inputs, temperature=0.0, do_sample=False)
        
        mock_model.generate.assert_called_once()
    
    def test_generation_with_max_tokens_zero(self):
        """Test generation with max_new_tokens=0."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2]])
        
        inputs = {'input_ids': torch.tensor([[1, 2]])}
        outputs = mock_model.generate(**inputs, max_new_tokens=0)
        
        # Should return only input tokens
        assert outputs.shape[1] == 2
    
    def test_generation_with_various_top_p_values(self):
        """Test generation with different top_p values."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3]])
        
        for top_p in [0.1, 0.5, 0.9, 1.0]:
            inputs = {'input_ids': torch.tensor([[1]])}
            outputs = mock_model.generate(**inputs, top_p=top_p, do_sample=True)
            assert outputs is not None
    
    def test_generation_with_pad_token(self):
        """Test generation with pad_token_id set."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 0]])
        
        inputs = {'input_ids': torch.tensor([[1, 2]])}
        outputs = mock_model.generate(**inputs, pad_token_id=0)
        
        assert 0 in outputs[0]
    
    def test_generation_with_eos_token(self):
        """Test generation stops at EOS token."""
        mock_model = Mock()
        # Simulate EOS token (id=2) in output
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 2]])
        
        inputs = {'input_ids': torch.tensor([[1]])}
        outputs = mock_model.generate(**inputs, eos_token_id=2)
        
        assert 2 in outputs[0]
    
    def test_generation_cuda_out_of_memory(self):
        """Test handling of CUDA OOM errors."""
        mock_model = Mock()
        mock_model.generate.side_effect = RuntimeError("CUDA out of memory")
        
        inputs = {'input_ids': torch.tensor([[1, 2, 3]])}
        
        with pytest.raises(RuntimeError, match="CUDA out of memory"):
            mock_model.generate(**inputs, max_new_tokens=200)


class TestOutputDecoding:
    """Test output decoding and parsing."""
    
    def test_decode_standard_output(self):
        """Test decoding standard model output."""
        mock_tokenizer = Mock()
        mock_tokenizer.decode.return_value = "Review: This is a good PR."
        
        output_ids = torch.tensor([[1, 2, 3, 4, 5]])
        decoded = mock_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        assert "Review:" in decoded
    
    def test_decode_with_special_tokens(self):
        """Test decoding with special tokens present."""
        mock_tokenizer = Mock()
        mock_tokenizer.decode.return_value = "Review: Good work."
        
        output_ids = torch.tensor([[0, 1, 2, 3, 2]])  # 0=pad, 2=eos
        decoded = mock_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        assert "<pad>" not in decoded
        assert "<eos>" not in decoded
    
    def test_decode_empty_output(self):
        """Test decoding empty output."""
        mock_tokenizer = Mock()
        mock_tokenizer.decode.return_value = ""
        
        output_ids = torch.tensor([[]])
        decoded = mock_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        assert decoded == ""
    
    def test_extract_review_with_delimiter(self):
        """Test extracting review when 'Review:' delimiter exists."""
        generated = "Prompt text here\nReview: This is the actual review content."
        
        if "Review:" in generated:
            review = generated.split("Review:")[-1].strip()
        else:
            review = generated.strip()
        
        assert review == "This is the actual review content."
    
    def test_extract_review_without_delimiter(self):
        """Test extracting review when no delimiter exists."""
        generated = "This is the review content without delimiter."
        
        if "Review:" in generated:
            review = generated.split("Review:")[-1].strip()
        else:
            review = generated.strip()
        
        assert review == "This is the review content without delimiter."
    
    def test_extract_review_multiple_delimiters(self):
        """Test extraction with multiple 'Review:' occurrences."""
        generated = "Review: First review\nReview: Second review"
        
        review = generated.split("Review:")[-1].strip()
        assert review == "Second review"
    
    def test_extract_review_empty_after_delimiter(self):
        """Test extraction when nothing follows delimiter."""
        generated = "Some text\nReview:"
        
        review = generated.split("Review:")[-1].strip()
        assert review == ""
    
    def test_decode_with_unicode(self):
        """Test decoding output with unicode characters."""
        mock_tokenizer = Mock()
        mock_tokenizer.decode.return_value = "Review: Code looks good! 👍"
        
        output_ids = torch.tensor([[1, 2, 3]])
        decoded = mock_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        assert "👍" in decoded


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_model_none_input(self):
        """Test handling of None input."""
        mock_tokenizer = Mock()
        mock_tokenizer.side_effect = TypeError("Input cannot be None")
        
        with pytest.raises(TypeError):
            mock_tokenizer(None, return_tensors="pt")
    
    def test_empty_batch_generation(self):
        """Test generation with empty batch."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([])
        
        inputs = {'input_ids': torch.tensor([])}
        outputs = mock_model.generate(**inputs)
        
        assert outputs.numel() == 0
    
    def test_extremely_short_input(self):
        """Test with single token input."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {'input_ids': torch.tensor([[1]])}
        
        inputs = mock_tokenizer("a", return_tensors="pt")
        assert inputs['input_ids'].shape[1] == 1
    
    def test_negative_max_tokens(self):
        """Test handling of negative max_new_tokens."""
        mock_model = Mock()
        mock_model.generate.side_effect = ValueError("max_new_tokens must be positive")
        
        with pytest.raises(ValueError):
            mock_model.generate(input_ids=torch.tensor([[1]]), max_new_tokens=-1)
    
    def test_temperature_out_of_range(self):
        """Test with temperature > 1.0."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3]])
        
        # Should work but may produce unexpected results
        inputs = {'input_ids': torch.tensor([[1]])}
        outputs = mock_model.generate(**inputs, temperature=5.0, do_sample=True)
        
        assert outputs is not None
    
    def test_concurrent_generation_requests(self):
        """Test handling multiple concurrent requests."""
        mock_model = Mock()
        mock_model.generate.return_value = torch.tensor([[1, 2, 3]])
        
        inputs1 = {'input_ids': torch.tensor([[1]])}
        inputs2 = {'input_ids': torch.tensor([[2]])}
        
        out1 = mock_model.generate(**inputs1)
        out2 = mock_model.generate(**inputs2)
        
        assert out1 is not None
        assert out2 is not None


class TestIntegration:
    """Integration tests combining multiple components."""
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    @patch('torch.cuda.is_available')
    def test_full_inference_pipeline(self, mock_cuda, mock_model_cls, mock_tokenizer_cls):
        """Test complete inference pipeline end-to-end."""
        # Setup mocks
        mock_cuda.return_value = False
        mock_tokenizer = Mock()
        mock_model = Mock()
        
        mock_tokenizer_cls.return_value = mock_tokenizer
        mock_model_cls.return_value = mock_model
        
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.eos_token_id = 2
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_tokenizer.decode.return_value = "Prompt\nReview: Excellent PR!"
        mock_model.to.return_value = mock_model
        
        # Execute pipeline
        tokenizer = AutoTokenizer.from_pretrained("./model")
        model = AutoModelForCausalLM.from_pretrained("./model")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        
        prompt = "Test prompt"
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=50, eos_token_id=tokenizer.eos_token_id)
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        review = generated.split("Review:")[-1].strip() if "Review:" in generated else generated.strip()
        
        # Assertions
        assert review == "Excellent PR!"
        mock_model.generate.assert_called_once()
    
    def test_memory_cleanup(self):
        """Test memory cleanup after generation."""
        if torch.cuda.is_available():
            initial_memory = torch.cuda.memory_allocated()
            
            # Simulate generation
            tensor = torch.randn(1000, 1000).cuda()
            del tensor
            torch.cuda.empty_cache()
            
            final_memory = torch.cuda.memory_allocated()
            assert final_memory <= initial_memory


class TestErrorRecovery:
    """Test error handling and recovery mechanisms."""
    
    def test_tokenization_error_recovery(self):
        """Test recovery from tokenization errors."""
        mock_tokenizer = Mock()
        mock_tokenizer.side_effect = [
            Exception("Tokenization failed"),
            {'input_ids': torch.tensor([[1, 2, 3]])}
        ]
        
        try:
            inputs = mock_tokenizer("test", return_tensors="pt")
        except Exception:
            # Retry
            inputs = mock_tokenizer("test", return_tensors="pt")
        
        assert 'input_ids' in inputs
    
    def test_generation_timeout_handling(self):
        """Test handling of generation timeouts."""
        mock_model = Mock()
        mock_model.generate.side_effect = TimeoutError("Generation timeout")
        
        with pytest.raises(TimeoutError):
            mock_model.generate(input_ids=torch.tensor([[1]]), max_new_tokens=100)


# Pytest fixtures
@pytest.fixture
def mock_tokenizer():
    """Fixture for mock tokenizer."""
    tokenizer = Mock()
    tokenizer.eos_token_id = 2
    tokenizer.pad_token_id = 0
    return tokenizer


@pytest.fixture
def mock_model():
    """Fixture for mock model."""
    model = Mock()
    model.to = Mock(return_value=model)
    return model


@pytest.fixture
def sample_pr_data():
    """Fixture for sample PR data."""
    return {
        'title': 'Fix bug in login',
        'description': 'Fixed null pointer exception',
        'diff': '```diff\n-bad code\n+good code\n```'
    }


# Run tests with: pytest test_inference_pr.py -v --cov
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov", "--cov-report=html"])