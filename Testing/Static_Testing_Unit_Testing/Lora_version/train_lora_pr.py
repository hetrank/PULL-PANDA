"""
Fine-tuning script for PR review model.

This script fine-tunes a causal language model (GPT-2 by default) on a dataset
of pull request reviews to generate automated code reviews.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import load_dataset

# Load base model
MODEL_NAME = "gpt2"   # can swap later with LLaMA, Mistral, etc.
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# Load dataset
dataset = load_dataset("json", data_files="train.jsonl")


def preprocess(examples):
    """
    Preprocess examples by tokenizing prompts and completions.
    
    Args:
        examples: Dictionary containing 'prompt' and 'completion' fields.
        
    Returns:
        Dictionary with tokenized inputs and labels for training.
    """
    # Concatenate prompt + completion for each example
    texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]

    # Tokenize the list
    tokenized_data = tokenizer(
        texts,
        truncation=True,
        max_length=128,
        padding="max_length"
    )

    # Add labels (copy of input_ids, so loss is computed)
    tokenized_data["labels"] = tokenized_data["input_ids"].copy()
    return tokenized_data


# Apply preprocessing, remove original columns
tokenized_dataset = dataset.map(
    preprocess,
    batched=True,
    remove_columns=["prompt", "completion"]
)

# Training args
args = TrainingArguments(
    output_dir="./pr-review-model",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_strategy="no",
    logging_steps=10,
    report_to="none",   # disable wandb by default
)

# Trainer
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_dataset["train"],
    tokenizer=tokenizer,
)

# Train
trainer.train()
trainer.save_model("./pr-review-model")
print("✅ Training complete. Model saved to ./pr-review-model")
