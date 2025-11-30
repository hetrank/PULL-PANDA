"""
Fine-tuned model inference for PR reviews.

This script loads a fine-tuned language model and generates code reviews
for GitHub Pull Requests using the trained model.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Load fine-tuned model
MODEL_PATH = "./pr-review-model"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Device set to use {device}")

# Example PR input
PR_TITLE = "Improve error handling"
PR_DESCRIPTION = "Added better error messages for invalid inputs."
CODE_DIFF = """```diff
-    if not user_input:
-        print("Error")
-        return
+    if not user_input:
+        raise ValueError("Invalid input: user input cannot be empty")
```"""

# Match training format more explicitly
PROMPT = (
    f"You are a senior software engineer reviewing a pull request.\n"
    f"PR Title: {PR_TITLE}\n"
    f"PR Description: {PR_DESCRIPTION}\n"
    f"Code Diff:\n{CODE_DIFF}\n\n"
    f"Please provide a constructive PR Review with strengths, weaknesses, "
    f"and suggestions.\n"
    f"Review: "
)


inputs = tokenizer(PROMPT, return_tensors="pt").to(device)

# Generate review
outputs = model.generate(
    **inputs,
    max_new_tokens=200,
    temperature=0.8,
    top_p=0.95,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
    eos_token_id=tokenizer.eos_token_id
)

generated = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Extract review text
if "Review:" in generated:
    review = generated.split("Review:")[-1].strip()
else:
    review = generated.strip()

print("📝 Model Review:", review if review else "[No output generated]")
