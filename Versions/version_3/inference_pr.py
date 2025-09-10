from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load fine-tuned model
model_path = "./pr-review-model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Device set to use {device}")

# Example PR input
pr_title = "Improve error handling"
pr_description = "Added better error messages for invalid inputs."
code_diff = """```diff
-    if not user_input:
-        print("Error")
-        return
+    if not user_input:
+        raise ValueError("Invalid input: user input cannot be empty")
```"""

# Match training format more explicitly
prompt = (
    f"You are a senior software engineer reviewing a pull request.\n"
    f"PR Title: {pr_title}\n"
    f"PR Description: {pr_description}\n"
    f"Code Diff:\n{code_diff}\n\n"
    f"Please provide a constructive PR Review with strengths, weaknesses, and suggestions.\n"
    f"Review: "
)


inputs = tokenizer(prompt, return_tensors="pt").to(device)

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
