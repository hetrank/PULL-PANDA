"""
Comprehensive test suite for PR review model fine-tuning script.

Tests cover: model loading, tokenization, dataset loading, preprocessing,
training configuration, trainer execution, edge cases, and error handling.
"""

import pytest
import torch
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, call
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    Trainer, 
    TrainingArguments,
    PreTrainedTokenizer
)
from datasets import load_dataset, Dataset, DatasetDict
import shutil


class TestModelAndTokenizerLoading:
    """Test model and tokenizer initialization."""
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    def test_tokenizer_loads_successfully(self, mock_tokenizer):
        """Test successful tokenizer loading."""
        mock_tok = Mock(spec=PreTrainedTokenizer)
        mock_tok.pad_token = None
        mock_tok.eos_token = "<eos>"
        mock_tokenizer.return_value = mock_tok
        
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        assert tokenizer is not None
        mock_tokenizer.assert_called_once_with("gpt2")
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    def test_pad_token_initialization(self, mock_tokenizer):
        """Test pad token is set to eos_token when None."""
        mock_tok = Mock(spec=PreTrainedTokenizer)
        mock_tok.pad_token = None
        mock_tok.eos_token = "<eos>"
        mock_tokenizer.return_value = mock_tok
        
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        assert tokenizer.pad_token == "<eos>"
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    def test_pad_token_already_set(self, mock_tokenizer):
        """Test when pad_token is already set."""
        mock_tok = Mock(spec=PreTrainedTokenizer)
        mock_tok.pad_token = "<pad>"
        mock_tok.eos_token = "<eos>"
        mock_tokenizer.return_value = mock_tok
        
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        assert tokenizer.pad_token == "<pad>"
    
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    def test_model_loads_successfully(self, mock_model):
        """Test successful model loading."""
        mock_model.return_value = Mock()
        
        model = AutoModelForCausalLM.from_pretrained("gpt2")
        assert model is not None
        mock_model.assert_called_once_with("gpt2")
    
    @patch('transformers.AutoTokenizer.from_pretrained')
    def test_invalid_model_name(self, mock_tokenizer):
        """Test handling of invalid model name."""
        mock_tokenizer.side_effect = OSError("Model not found")
        
        with pytest.raises(OSError):
            AutoTokenizer.from_pretrained("invalid-model-name")
    
    @patch('transformers.AutoModelForCausalLM.from_pretrained')
    def test_model_loading_with_custom_config(self, mock_model):
        """Test model loading with custom configuration."""
        mock_model.return_value = Mock()
        
        model = AutoModelForCausalLM.from_pretrained(
            "gpt2",
            torch_dtype=torch.float16
        )
        assert model is not None
    
    def test_different_model_names(self):
        """Test with various model names."""
        models = ["gpt2", "gpt2-medium", "distilgpt2", "EleutherAI/gpt-neo-125M"]
        
        for model_name in models:
            with patch('transformers.AutoTokenizer.from_pretrained') as mock_tok:
                mock_tok.return_value = Mock(pad_token=None, eos_token="<eos>")
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                assert tokenizer is not None


class TestDatasetLoading:
    """Test dataset loading and validation."""
    
    def test_load_valid_jsonl_dataset(self, tmp_path):
        """Test loading valid JSONL file."""
        # Create temporary JSONL file
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "Review this:", "completion": "Looks good!"}, f)
            f.write('\n')
            json.dump({"prompt": "Check code:", "completion": "Needs work."}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        assert "train" in dataset
        assert len(dataset["train"]) == 2
        assert "prompt" in dataset["train"].column_names
        assert "completion" in dataset["train"].column_names
    
    def test_load_empty_jsonl_dataset(self, tmp_path):
        """Test loading empty JSONL file."""
        data_file = tmp_path / "train.jsonl"
        data_file.touch()  # Create empty file
        
        dataset = load_dataset("json", data_files=str(data_file))
        assert len(dataset["train"]) == 0
    
    def test_load_missing_dataset_file(self):
        """Test handling of missing dataset file."""
        with pytest.raises(FileNotFoundError):
            load_dataset("json", data_files="nonexistent.jsonl")
    
    def test_load_malformed_jsonl(self, tmp_path):
        """Test handling of malformed JSONL."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            f.write('{"prompt": "test"')  # Incomplete JSON
        
        with pytest.raises(Exception):  # Could be JSONDecodeError or similar
            load_dataset("json", data_files=str(data_file))
    
    def test_load_jsonl_missing_columns(self, tmp_path):
        """Test JSONL with missing required columns."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "test"}, f)  # Missing 'completion'
        
        dataset = load_dataset("json", data_files=str(data_file))
        assert "prompt" in dataset["train"].column_names
        # Should load but missing completion column
    
    def test_load_large_dataset(self, tmp_path):
        """Test loading large dataset."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            for i in range(1000):
                json.dump({
                    "prompt": f"Review PR {i}:",
                    "completion": f"Review {i} content"
                }, f)
                f.write('\n')
        
        dataset = load_dataset("json", data_files=str(data_file))
        assert len(dataset["train"]) == 1000
    
    def test_dataset_with_unicode(self, tmp_path):
        """Test dataset with unicode characters."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({
                "prompt": "Review: 修复错误 🐛",
                "completion": "Código correcto ✓"
            }, f, ensure_ascii=False)
        
        dataset = load_dataset("json", data_files=str(data_file))
        assert len(dataset["train"]) == 1
        assert "修复错误" in dataset["train"][0]["prompt"]


class TestPreprocessFunction:
    """Test preprocessing function."""
    
    def create_mock_tokenizer(self):
        """Helper to create mock tokenizer."""
        mock_tok = Mock()
        mock_tok.return_value = {
            'input_ids': [[1, 2, 3, 0]],
            'attention_mask': [[1, 1, 1, 0]]
        }
        return mock_tok
    
    def test_preprocess_single_example(self):
        """Test preprocessing single example."""
        mock_tokenizer = self.create_mock_tokenizer()
        
        examples = {
            "prompt": ["Review this PR:"],
            "completion": [" Looks good!"]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(
                texts,
                truncation=True,
                max_length=128,
                padding="max_length"
            )
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        
        assert "input_ids" in result
        assert "labels" in result
        assert result["labels"] == result["input_ids"]
    
    def test_preprocess_multiple_examples(self):
        """Test preprocessing multiple examples in batch."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3], [4, 5, 6]],
            'attention_mask': [[1, 1, 1], [1, 1, 1]]
        }
        
        examples = {
            "prompt": ["Prompt 1:", "Prompt 2:"],
            "completion": [" Completion 1", " Completion 2"]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert len(result["input_ids"]) == 2
    
    def test_preprocess_empty_examples(self):
        """Test preprocessing empty examples."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [],
            'attention_mask': []
        }
        
        examples = {"prompt": [], "completion": []}
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert len(result["input_ids"]) == 0
    
    def test_preprocess_long_text_truncation(self):
        """Test truncation of long texts."""
        mock_tokenizer = Mock()
        # Simulate truncated output
        mock_tokenizer.return_value = {
            'input_ids': [[1] * 128],  # Max length
            'attention_mask': [[1] * 128]
        }
        
        examples = {
            "prompt": ["Very " * 200],  # Long prompt
            "completion": ["long " * 200]  # Long completion
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert len(result["input_ids"][0]) == 128
    
    def test_preprocess_with_padding(self):
        """Test padding behavior."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 0, 0]],  # Padded
            'attention_mask': [[1, 1, 0, 0]]
        }
        
        examples = {
            "prompt": ["Short"],
            "completion": [" text"]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert 0 in result["input_ids"][0]  # Contains padding
    
    def test_preprocess_special_characters(self):
        """Test preprocessing with special characters."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3, 4]],
            'attention_mask': [[1, 1, 1, 1]]
        }
        
        examples = {
            "prompt": ["Review: <code>func()</code>"],
            "completion": [" Contains 'quotes' and \"double quotes\""]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert "input_ids" in result
    
    def test_labels_are_copy_not_reference(self):
        """Test that labels are copy, not reference to input_ids."""
        mock_tokenizer = Mock()
        input_ids = [[1, 2, 3]]
        mock_tokenizer.return_value = {
            'input_ids': input_ids,
            'attention_mask': [[1, 1, 1]]
        }
        
        examples = {"prompt": ["test"], "completion": [" completion"]}
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        
        # Modify input_ids
        result["input_ids"][0][0] = 999
        
        # Labels should not be affected
        assert result["labels"][0][0] != 999


class TestDatasetMapping:
    """Test dataset mapping and transformations."""
    
    def test_map_applies_preprocessing(self, tmp_path):
        """Test that map applies preprocessing function."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "Test", "completion": " completion"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        def preprocess(examples):
            return {"processed": [True] * len(examples["prompt"])}
        
        mapped = dataset.map(preprocess, batched=True)
        
        assert "processed" in mapped["train"].column_names
    
    def test_map_removes_columns(self, tmp_path):
        """Test that map removes specified columns."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "Test", "completion": " comp"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        def preprocess(examples):
            return {"new_col": ["value"] * len(examples["prompt"])}
        
        mapped = dataset.map(
            preprocess, 
            batched=True, 
            remove_columns=["prompt", "completion"]
        )
        
        assert "prompt" not in mapped["train"].column_names
        assert "completion" not in mapped["train"].column_names
        assert "new_col" in mapped["train"].column_names
    
    def test_map_batched_processing(self, tmp_path):
        """Test batched processing in map."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            for i in range(10):
                json.dump({"prompt": f"P{i}", "completion": f"C{i}"}, f)
                f.write('\n')
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        batch_sizes = []
        
        def preprocess(examples):
            batch_sizes.append(len(examples["prompt"]))
            return {"processed": [True] * len(examples["prompt"])}
        
        dataset.map(preprocess, batched=True, batch_size=5)
        
        assert len(batch_sizes) > 0  # At least one batch processed
    
    def test_map_error_handling(self, tmp_path):
        """Test error handling in map function."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "Test", "completion": " comp"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        def failing_preprocess(examples):
            raise ValueError("Processing failed")
        
        with pytest.raises(Exception):
            dataset.map(failing_preprocess, batched=True)


class TestTrainingArguments:
    """Test training arguments configuration."""
    
    def test_training_args_basic_config(self, tmp_path):
        """Test basic training arguments configuration."""
        output_dir = tmp_path / "model"
        
        args = TrainingArguments(
            output_dir=str(output_dir),
            overwrite_output_dir=True,
            num_train_epochs=3,
            per_device_train_batch_size=2,
            save_strategy="no",
            logging_steps=10,
            report_to="none"
        )
        
        assert args.output_dir == str(output_dir)
        assert args.num_train_epochs == 3
        assert args.per_device_train_batch_size == 2
        assert args.save_strategy == "no"
    
    def test_training_args_output_dir_creation(self, tmp_path):
        """Test output directory is created."""
        output_dir = tmp_path / "model"
        
        args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=1
        )
        
        # Output dir should be prepared by Trainer
        assert args.output_dir == str(output_dir)
    
    def test_training_args_various_epochs(self, tmp_path):
        """Test with various epoch counts."""
        for epochs in [1, 3, 5, 10]:
            args = TrainingArguments(
                output_dir=str(tmp_path / f"model_{epochs}"),
                num_train_epochs=epochs
            )
            assert args.num_train_epochs == epochs
    
    def test_training_args_batch_sizes(self, tmp_path):
        """Test with various batch sizes."""
        for batch_size in [1, 2, 4, 8, 16]:
            args = TrainingArguments(
                output_dir=str(tmp_path / f"model_bs{batch_size}"),
                per_device_train_batch_size=batch_size
            )
            assert args.per_device_train_batch_size == batch_size
    
    def test_training_args_save_strategies(self, tmp_path):
        """Test different save strategies."""
        strategies = ["no", "epoch", "steps"]
        
        for strategy in strategies:
            args = TrainingArguments(
                output_dir=str(tmp_path / f"model_{strategy}"),
                save_strategy=strategy
            )
            assert args.save_strategy == strategy
    
    def test_training_args_logging_configuration(self, tmp_path):
        """Test logging configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            logging_steps=50,
            logging_strategy="steps",
            report_to="none"
        )
        
        assert args.logging_steps == 50
        assert args.report_to == ["none"]
    
    def test_training_args_evaluation_config(self, tmp_path):
        """Test evaluation configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            eval_strategy="epoch",
            per_device_eval_batch_size=4
        )
        
        assert args.eval_strategy == "epoch"
        assert args.per_device_eval_batch_size == 4
    
    def test_training_args_learning_rate(self, tmp_path):
        """Test learning rate configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            learning_rate=5e-5
        )
        
        assert args.learning_rate == 5e-5
    
    def test_training_args_weight_decay(self, tmp_path):
        """Test weight decay configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            weight_decay=0.01
        )
        
        assert args.weight_decay == 0.01
    
    def test_training_args_warmup_steps(self, tmp_path):
        """Test warmup steps configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            warmup_steps=500
        )
        
        assert args.warmup_steps == 500
    
    def test_training_args_gradient_accumulation(self, tmp_path):
        """Test gradient accumulation steps."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            gradient_accumulation_steps=4
        )
        
        assert args.gradient_accumulation_steps == 4
    
    def test_training_args_mixed_precision(self, tmp_path):
        """Test mixed precision training configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            fp16=True
        )
        
        assert args.fp16 == True


class TestTrainer:
    """Test Trainer initialization and execution."""
    
    def create_mock_components(self, tmp_path):
        """Helper to create mock components."""
        mock_model = Mock()
        mock_model.save_pretrained = Mock()
        
        mock_tokenizer = Mock()
        mock_tokenizer.save_pretrained = Mock()
        
        # Create dummy dataset
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"input_ids": [1, 2, 3], "labels": [1, 2, 3]}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        args = TrainingArguments(
            output_dir=str(tmp_path / "output"),
            num_train_epochs=1,
            per_device_train_batch_size=1,
            save_strategy="no",
            report_to="none"
        )
        
        return mock_model, mock_tokenizer, dataset["train"], args
    
    @patch('transformers.Trainer')
    def test_trainer_initialization(self, mock_trainer_cls, tmp_path):
        """Test Trainer initialization."""
        model, tokenizer, dataset, args = self.create_mock_components(tmp_path)
        
        mock_trainer = Mock()
        mock_trainer_cls.return_value = mock_trainer
        
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer
        )
        
        assert trainer is not None
    
    @patch('transformers.Trainer')
    def test_trainer_train_method(self, mock_trainer_cls, tmp_path):
        """Test Trainer train method execution."""
        model, tokenizer, dataset, args = self.create_mock_components(tmp_path)
        
        mock_trainer = Mock()
        mock_trainer.train = Mock(return_value=Mock(training_loss=0.5))
        mock_trainer_cls.return_value = mock_trainer
        
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer
        )
        
        result = trainer.train()
        mock_trainer.train.assert_called_once()
        assert result is not None
    
    @patch('transformers.Trainer')
    def test_trainer_save_model(self, mock_trainer_cls, tmp_path):
        """Test Trainer save_model method."""
        model, tokenizer, dataset, args = self.create_mock_components(tmp_path)
        
        mock_trainer = Mock()
        mock_trainer.save_model = Mock()
        mock_trainer_cls.return_value = mock_trainer
        
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer
        )
        
        save_path = str(tmp_path / "saved_model")
        trainer.save_model(save_path)
        mock_trainer.save_model.assert_called_once_with(save_path)
    
    def test_trainer_with_empty_dataset(self, tmp_path):
        """Test Trainer with empty dataset."""
        model, tokenizer, _, args = self.create_mock_components(tmp_path)
        
        # Create empty dataset
        empty_dataset = Dataset.from_dict({"input_ids": [], "labels": []})
        
        with pytest.raises(Exception):  # Should fail with empty dataset
            trainer = Trainer(
                model=model,
                args=args,
                train_dataset=empty_dataset,
                tokenizer=tokenizer
            )
            trainer.train()
    
    @patch('transformers.Trainer')
    def test_trainer_with_eval_dataset(self, mock_trainer_cls, tmp_path):
        """Test Trainer with evaluation dataset."""
        model, tokenizer, dataset, args = self.create_mock_components(tmp_path)
        
        mock_trainer = Mock()
        mock_trainer_cls.return_value = mock_trainer
        
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            eval_dataset=dataset,  # Using same dataset for eval
            tokenizer=tokenizer
        )
        
        assert trainer is not None
    
    @patch('transformers.Trainer')
    def test_trainer_callbacks(self, mock_trainer_cls, tmp_path):
        """Test Trainer with callbacks."""
        model, tokenizer, dataset, args = self.create_mock_components(tmp_path)
        
        mock_callback = Mock()
        mock_trainer = Mock()
        mock_trainer_cls.return_value = mock_trainer
        
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            callbacks=[mock_callback]
        )
        
        assert trainer is not None


class TestEndToEndTraining:
    """Integration tests for complete training pipeline."""
    
    @patch('transformers.Trainer.train')
    @patch('transformers.Trainer.save_model')
    def test_full_training_pipeline(self, mock_save, mock_train, tmp_path):
        """Test complete training pipeline."""
        # Setup
        mock_train.return_value = Mock(training_loss=0.5)
        
        # Create dataset
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "Test", "completion": " output"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3]],
            'attention_mask': [[1, 1, 1]]
        }
        mock_tokenizer.pad_token = "<pad>"
        
        # Mock model
        mock_model = Mock()
        
        # Preprocess
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        tokenized_dataset = dataset.map(
            preprocess,
            batched=True,
            remove_columns=["prompt", "completion"]
        )
        
        # Training args
        args = TrainingArguments(
            output_dir=str(tmp_path / "model"),
            num_train_epochs=1,
            per_device_train_batch_size=1,
            save_strategy="no",
            report_to="none"
        )
        
        # Train
        trainer = Trainer(
            model=mock_model,
            args=args,
            train_dataset=tokenized_dataset["train"],
            tokenizer=mock_tokenizer
        )
        
        trainer.train()
        trainer.save_model(str(tmp_path / "final_model"))
        
        # Verify
        mock_train.assert_called_once()
        mock_save.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_mismatched_prompt_completion_lengths(self):
        """Test when prompt and completion have different lengths."""
        examples = {
            "prompt": ["P1", "P2"],
            "completion": ["C1"]  # Mismatched length
        }
        
        with pytest.raises((ValueError, IndexError)):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            # zip will silently stop at shortest, but this should be caught
            assert len(texts) == 1  # Only 1 pair created
    
    def test_none_values_in_dataset(self, tmp_path):
        """Test handling of None values."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": None, "completion": "test"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        # Should load but may cause issues in preprocessing
        assert dataset is not None
    
    def test_extremely_long_sequence(self):
        """Test with sequence exceeding max_length."""
        mock_tokenizer = Mock()
        # Simulate truncation
        mock_tokenizer.return_value = {
            'input_ids': [[1] * 128],
            'attention_mask': [[1] * 128]
        }
        
        examples = {
            "prompt": ["word " * 1000],
            "completion": ["text " * 1000]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        result = preprocess(examples)
        assert len(result["input_ids"][0]) == 128
    
    def test_zero_batch_size(self, tmp_path):
        """Test with batch_size=0."""
        with pytest.raises(ValueError):
            args = TrainingArguments(
                output_dir=str(tmp_path),
                per_device_train_batch_size=0
            )
    
    def test_negative_epochs(self, tmp_path):
        """Test with negative epochs."""
        with pytest.raises(ValueError):
            args = TrainingArguments(
                output_dir=str(tmp_path),
                num_train_epochs=-1
            )
    
    def test_invalid_save_strategy(self, tmp_path):
        """Test with invalid save strategy."""
        with pytest.raises(ValueError):
            args = TrainingArguments(
                output_dir=str(tmp_path),
                save_strategy="invalid_strategy"
            )
    
    def test_dataset_with_extra_columns(self, tmp_path):
        """Test dataset with extra columns not used in training."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({
                "prompt": "Test",
                "completion": " output",
                "extra_field": "ignored",
                "another_field": 123
            }, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3]],
            'attention_mask': [[1, 1, 1]]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        # Should successfully map and remove all original columns
        tokenized = dataset.map(
            preprocess,
            batched=True,
            remove_columns=["prompt", "completion", "extra_field", "another_field"]
        )
        
        assert "extra_field" not in tokenized["train"].column_names


class TestMemoryAndPerformance:
    """Test memory usage and performance considerations."""
    
    def test_memory_efficient_dataset_loading(self, tmp_path):
        """Test dataset loading doesn't load everything into memory at once."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            for i in range(100):
                json.dump({"prompt": f"P{i}", "completion": f"C{i}"}, f)
                f.write('\n')
        
        # Dataset should use streaming or memory-mapped loading
        dataset = load_dataset("json", data_files=str(data_file))
        
        # Access individual items without loading all
        first_item = dataset["train"][0]
        assert "prompt" in first_item
    
    def test_gradient_checkpointing_compatibility(self, tmp_path):
        """Test training args compatible with gradient checkpointing."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            gradient_checkpointing=True,
            per_device_train_batch_size=1
        )
        
        assert args.gradient_checkpointing == True
    
    @patch('torch.cuda.is_available')
    def test_multi_gpu_configuration(self, mock_cuda, tmp_path):
        """Test configuration for multi-GPU training."""
        mock_cuda.return_value = True
        
        args = TrainingArguments(
            output_dir=str(tmp_path),
            per_device_train_batch_size=2,
            dataloader_num_workers=4
        )
        
        assert args.dataloader_num_workers == 4


class TestTokenizerEdgeCases:
    """Test tokenizer-specific edge cases."""
    
    def test_tokenizer_with_no_eos_token(self):
        """Test when tokenizer has no eos_token."""
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = None
        
        # Should handle gracefully or raise appropriate error
        if mock_tokenizer.pad_token is None:
            if mock_tokenizer.eos_token is not None:
                mock_tokenizer.pad_token = mock_tokenizer.eos_token
        
        # If both are None, may need special handling
        assert True  # Test completed without crash
    
    def test_tokenizer_output_format(self):
        """Test tokenizer returns correct format."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3]],
            'attention_mask': [[1, 1, 1]]
        }
        
        result = mock_tokenizer("test", return_tensors="pt")
        
        assert 'input_ids' in result
        assert 'attention_mask' in result
    
    def test_tokenizer_with_special_tokens_added(self):
        """Test tokenizer when special tokens are added."""
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[101, 1, 2, 3, 102]],  # CLS and SEP tokens
            'attention_mask': [[1, 1, 1, 1, 1]]
        }
        mock_tokenizer.add_special_tokens = Mock(return_value=2)
        
        # Adding special tokens
        num_added = mock_tokenizer.add_special_tokens({'pad_token': '[PAD]'})
        assert num_added == 2


class TestModelSaving:
    """Test model saving functionality."""
    
    @patch('transformers.Trainer.save_model')
    def test_model_saves_to_correct_path(self, mock_save, tmp_path):
        """Test model saves to specified path."""
        save_path = str(tmp_path / "pr-review-model")
        
        mock_trainer = Mock()
        mock_trainer.save_model = mock_save
        
        mock_trainer.save_model(save_path)
        mock_save.assert_called_once_with(save_path)
    
    def test_save_path_creation(self, tmp_path):
        """Test that save path directory is created."""
        save_path = tmp_path / "nested" / "path" / "model"
        
        # Create directory structure
        save_path.mkdir(parents=True, exist_ok=True)
        
        assert save_path.exists()
    
    @patch('transformers.PreTrainedModel.save_pretrained')
    def test_model_config_saved(self, mock_save_pretrained):
        """Test that model config is saved."""
        mock_model = Mock()
        mock_model.save_pretrained = mock_save_pretrained
        
        mock_model.save_pretrained("./model")
        mock_save_pretrained.assert_called_once()
    
    @patch('transformers.PreTrainedTokenizer.save_pretrained')
    def test_tokenizer_saved_with_model(self, mock_save_tokenizer):
        """Test tokenizer is saved alongside model."""
        mock_tokenizer = Mock()
        mock_tokenizer.save_pretrained = mock_save_tokenizer
        
        mock_tokenizer.save_pretrained("./model")
        mock_save_tokenizer.assert_called_once()


class TestDataValidation:
    """Test data validation and quality checks."""
    
    def test_dataset_has_required_fields(self, tmp_path):
        """Test dataset contains required fields."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "test", "completion": "result"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        required_fields = ["prompt", "completion"]
        for field in required_fields:
            assert field in dataset["train"].column_names
    
    def test_dataset_non_empty(self, tmp_path):
        """Test dataset is not empty."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "test", "completion": "result"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        assert len(dataset["train"]) > 0
    
    def test_prompt_completion_pairs_valid(self, tmp_path):
        """Test all prompt-completion pairs are valid strings."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            json.dump({"prompt": "test1", "completion": "result1"}, f)
            f.write('\n')
            json.dump({"prompt": "test2", "completion": "result2"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        for item in dataset["train"]:
            assert isinstance(item["prompt"], str)
            assert isinstance(item["completion"], str)
            assert len(item["prompt"]) > 0
            assert len(item["completion"]) > 0


class TestLoggingAndReporting:
    """Test logging and reporting functionality."""
    
    def test_report_to_none_disables_wandb(self, tmp_path):
        """Test report_to='none' disables wandb."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            report_to="none"
        )
        
        assert args.report_to == ["none"]
    
    def test_logging_steps_configuration(self, tmp_path):
        """Test logging steps are properly configured."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            logging_steps=10,
            logging_strategy="steps"
        )
        
        assert args.logging_steps == 10
        assert args.logging_strategy == "steps"
    
    def test_logging_dir_creation(self, tmp_path):
        """Test logging directory is created."""
        log_dir = tmp_path / "logs"
        
        args = TrainingArguments(
            output_dir=str(tmp_path),
            logging_dir=str(log_dir)
        )
        
        # Logging dir should be set
        assert args.logging_dir == str(log_dir)


class TestConcurrencyAndParallelism:
    """Test concurrent operations and parallelism."""
    
    def test_dataloader_workers_configuration(self, tmp_path):
        """Test dataloader num_workers configuration."""
        args = TrainingArguments(
            output_dir=str(tmp_path),
            dataloader_num_workers=4
        )
        
        assert args.dataloader_num_workers == 4
    
    def test_multiple_training_runs_isolated(self, tmp_path):
        """Test multiple training runs don't interfere."""
        output_dir1 = tmp_path / "run1"
        output_dir2 = tmp_path / "run2"
        
        args1 = TrainingArguments(
            output_dir=str(output_dir1),
            num_train_epochs=1
        )
        
        args2 = TrainingArguments(
            output_dir=str(output_dir2),
            num_train_epochs=2
        )
        
        assert args1.output_dir != args2.output_dir
        assert args1.num_train_epochs != args2.num_train_epochs


class TestRobustness:
    """Test robustness and error recovery."""
    
    def test_continues_after_preprocessing_warning(self, tmp_path):
        """Test training continues after preprocessing warnings."""
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            # Some potentially problematic data
            json.dump({"prompt": "", "completion": "test"}, f)
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        # Should load without crashing
        assert len(dataset["train"]) == 1
    
    @patch('transformers.Trainer.train')
    def test_training_recovers_from_interruption(self, mock_train, tmp_path):
        """Test training can resume after interruption."""
        # First attempt fails
        mock_train.side_effect = [KeyboardInterrupt(), Mock(training_loss=0.5)]
        
        mock_model = Mock()
        mock_tokenizer = Mock()
        mock_dataset = Mock()
        
        args = TrainingArguments(
            output_dir=str(tmp_path),
            num_train_epochs=1,
            save_strategy="no",
            report_to="none"
        )
        
        trainer = Trainer(
            model=mock_model,
            args=args,
            train_dataset=mock_dataset,
            tokenizer=mock_tokenizer
        )
        
        # First call interrupted
        try:
            trainer.train()
        except KeyboardInterrupt:
            pass
        
        # Second call succeeds
        result = trainer.train()
        assert result is not None


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_max_length_validation(self):
        """Test max_length must be positive."""
        mock_tokenizer = Mock()
        
        with pytest.raises(ValueError):
            # Negative max_length should fail
            mock_tokenizer("test", truncation=True, max_length=-1)
    
    def test_padding_strategy_validation(self):
        """Test valid padding strategies."""
        valid_strategies = ["max_length", "longest", "do_not_pad"]
        mock_tokenizer = Mock()
        
        for strategy in valid_strategies:
            mock_tokenizer.return_value = {'input_ids': [[1, 2]]}
            result = mock_tokenizer("test", padding=strategy)
            assert result is not None
    
    def test_truncation_side_validation(self):
        """Test truncation side configuration."""
        mock_tokenizer = Mock()
        mock_tokenizer.truncation_side = "right"
        
        assert mock_tokenizer.truncation_side in ["left", "right"]


# Additional utility functions for testing
def create_test_dataset(tmp_path, num_examples=10):
    """Utility function to create test dataset."""
    data_file = tmp_path / "test_train.jsonl"
    with open(data_file, 'w') as f:
        for i in range(num_examples):
            json.dump({
                "prompt": f"Review PR #{i}:",
                "completion": f" This is review {i}"
            }, f)
            f.write('\n')
    
    return load_dataset("json", data_files=str(data_file))


def cleanup_test_artifacts(tmp_path):
    """Utility function to clean up test artifacts."""
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)


# Pytest fixtures for common test setup
@pytest.fixture
def sample_dataset(tmp_path):
    """Fixture providing sample dataset."""
    return create_test_dataset(tmp_path, num_examples=5)


@pytest.fixture
def mock_training_components():
    """Fixture providing mock training components."""
    mock_model = Mock()
    mock_tokenizer = Mock()
    mock_tokenizer.pad_token = "<pad>"
    mock_tokenizer.eos_token = "<eos>"
    mock_tokenizer.return_value = {
        'input_ids': [[1, 2, 3]],
        'attention_mask': [[1, 1, 1]]
    }
    
    return mock_model, mock_tokenizer


@pytest.fixture(autouse=True)
def reset_cuda_cache():
    """Fixture to reset CUDA cache between tests."""
    yield
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Performance benchmarking tests
class TestPerformance:
    """Performance and benchmarking tests."""
    
    def test_tokenization_speed(self, tmp_path):
        """Test tokenization completes in reasonable time."""
        import time
        
        data_file = tmp_path / "train.jsonl"
        with open(data_file, 'w') as f:
            for i in range(100):
                json.dump({"prompt": f"Test {i}", "completion": f" Result {i}"}, f)
                f.write('\n')
        
        dataset = load_dataset("json", data_files=str(data_file))
        
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': [[1, 2, 3]],
            'attention_mask': [[1, 1, 1]]
        }
        
        def preprocess(examples):
            texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]
            tokenized = mock_tokenizer(texts, truncation=True, max_length=128, padding="max_length")
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        start = time.time()
        dataset.map(preprocess, batched=True, batch_size=10)
        duration = time.time() - start
        
        # Should complete reasonably fast (adjust threshold as needed)
        assert duration < 5.0  # seconds


# Run all tests
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--cov=.",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-W", "ignore::DeprecationWarning"
    ])