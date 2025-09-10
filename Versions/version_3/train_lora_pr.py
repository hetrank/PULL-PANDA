from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import load_dataset

# Load base model
model_name = "gpt2"   # can swap later with LLaMA, Mistral, etc.
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_name)

# Load dataset
dataset = load_dataset("json", data_files="train.jsonl")

# Preprocessing function (handles batched=True)
def preprocess(examples):
    # Concatenate prompt + completion for each example
    texts = [p + c for p, c in zip(examples["prompt"], examples["completion"])]

    # Tokenize the list
    tokenized = tokenizer(
        texts,
        truncation=True,
        max_length=128,
        padding="max_length"
    )

    # Add labels (copy of input_ids, so loss is computed)
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

# Apply preprocessing, remove original columns
tokenized = dataset.map(preprocess, batched=True, remove_columns=["prompt", "completion"])

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
    train_dataset=tokenized["train"],
    tokenizer=tokenizer,
)

# Train
trainer.train()
trainer.save_model("./pr-review-model")
print("✅ Training complete. Model saved to ./pr-review-model")
