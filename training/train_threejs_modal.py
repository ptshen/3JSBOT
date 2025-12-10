"""
Fine-tune CodeLlama for Three.js code generation - Modal-compatible version.

This script:
1. Loads prepared training data (description, code pairs) from training_data.json
2. Fine-tunes CodeLlama on the dataset using SFT with LoRA

Designed to run on Modal for cloud training.

Note: Run prepare_training_data.py first to create training_data.json
"""

import modal
import os
import json
import re
import glob
from pathlib import Path
from typing import List, Dict, Optional
import tempfile

# Modal setup
app = modal.App("threejs-codellama-training")

# Create a persistent volume for storing the trained model
model_volume = modal.Volume.from_name("threejs-codellama-models", create_if_missing=True)

# Define Modal image with all dependencies
project_root = os.path.join(os.path.dirname(__file__), "..")
training_data_path = os.path.join(project_root, "training", "training_data.json")

image = (
    modal.Image.debian_slim()
    .apt_install("git", "curl", "build-essential")
    .pip_install(
        "torch>=2.0.0",
        "transformers>=4.35.0",
        "peft>=0.6.0",
        "datasets>=2.14.0",
        "accelerate>=0.24.0",
        "bitsandbytes>=0.41.0",
    )
    # Add training data file to image
    .add_local_file(
        training_data_path,
        "/root/training_data.json",
        copy=True
    )
)


@app.function(
    image=image,
    volumes={"/models": model_volume},  # Mount volume for persistent storage
    gpu="b200",  # Use B200 for training
    timeout=3600 * 24,  # 24 hour timeout (increased for 50 epochs)
    secrets=[modal.Secret.from_name("huggingface")],  # For HF token
)
def train_codellama_threejs():
    """
    Main training function that runs on Modal.
    """
    import sys
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model, AutoPeftModelForCausalLM
    from datasets import Dataset
    
    # Configuration
    MODEL_NAME = "codellama/CodeLlama-7b-Instruct-hf"
    MAX_LEN = 2048
    OUTPUT_DIR = "/models/threejs_codellama_lora"  # Save to volume for persistence
    
    print("=" * 60)
    print("CodeLlama Fine-tuning for Three.js Code Generation")
    print("=" * 60)
    
    # Load training data (must be prepared beforehand with prepare_training_data.py)
    # File is included in the image at /root/training_data.json
    training_data_file = "/root/training_data.json"
    
    if not os.path.exists(training_data_file):
        print("\nERROR: training_data.json not found!")
        print("Please run prepare_training_data.py first to create training data.")
        print("This script pairs .md descriptions with .js code files.")
        return
    
    print("\nLoading prepared training data...")
    with open(training_data_file, 'r', encoding='utf-8') as f:
        training_pairs = json.load(f)
    
    if len(training_pairs) == 0:
        print("ERROR: training_data.json is empty!")
        return
    
    print(f"Loaded {len(training_pairs)} training pairs")
    
    # Split training pairs (80/20)
    split_idx = int(len(training_pairs) * 0.8)
    train_data = [{'description': d['description'], 'code': d['code'], 'filename': d.get('filename', '')} 
                 for d in training_pairs[:split_idx]]
    val_data = [{'description': d['description'], 'code': d['code'], 'filename': d.get('filename', '')} 
               for d in training_pairs[split_idx:]]
    
    print(f"Train examples: {len(train_data)}")
    print(f"Validation examples: {len(val_data)}")
    
    # Initialize tokenizer and model
    print("\nLoading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    tokenizer.padding_side = "right"
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    tokenizer.truncation_side = "left"
    
    # Create prompt function
    def create_prompt(description: str, code: str = None) -> str:
        if code:
            # Full prompt with code (for training)
            prompt = f"""<s>[INST] Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting
- Include any animations or interactions if described

Return only the JavaScript code without markdown formatting. [/INST]
{code}"""
        else:
            # Prompt only (for inference)
            prompt = f"""<s>[INST] Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting
- Include any animations or interactions if described

Return only the JavaScript code without markdown formatting. [/INST]"""
        return prompt
    
    # Tokenize function
    def tokenize_batch(batch, tokenizer, max_len=MAX_LEN):
        descriptions = [d.rstrip() for d in batch["description"]]
        codes = batch.get("code", [None] * len(descriptions))
        
        # Create full prompts with code
        prompts = [create_prompt(desc, code) for desc, code in zip(descriptions, codes)]
        
        enc = tokenizer(prompts, add_special_tokens=False, padding=False, truncation=False)
        
        input_ids_list = []
        prompt_len_list = []
        
        for i, prompt_ids in enumerate(enc["input_ids"]):
            # Find where the code starts (after [/INST])
            prompt_text = prompts[i]
            inst_end = prompt_text.find("[/INST]")
            if inst_end != -1:
                prompt_part = prompt_text[:inst_end + len("[/INST]")]
                prompt_ids_only = tokenizer(prompt_part, add_special_tokens=False)["input_ids"]
                prompt_len = len(prompt_ids_only)
            else:
                prompt_len = len(prompt_ids)  # Fallback: mask everything
            
            if len(prompt_ids) > max_len:
                excess = len(prompt_ids) - max_len
                prompt_ids = prompt_ids[excess:]
                prompt_len = max(0, prompt_len - excess)
            
            input_ids_list.append(prompt_ids)
            prompt_len_list.append(prompt_len)
        
        return {
            "input_ids": input_ids_list,
            "prompt_len": prompt_len_list,
        }
    
    # Create datasets
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    def tokenize_fn(examples):
        return tokenize_batch(examples, tokenizer, MAX_LEN)
    
    print("\nTokenizing datasets...")
    train_tok = train_dataset.map(
        tokenize_fn,
        batched=True,
        batch_size=1024,
        remove_columns=train_dataset.column_names,
        desc="Tokenizing train set"
    )
    
    val_tok = val_dataset.map(
        tokenize_fn,
        batched=True,
        batch_size=1024,
        remove_columns=val_dataset.column_names,
        desc="Tokenizing val set"
    )
    
    # Initialize model with LoRA
    print("\nLoading model with LoRA...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map="auto",
        torch_dtype=torch.float16,
        attn_implementation="sdpa",
    )
    
    model.config.use_cache = False
    
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    
    model = get_peft_model(model, lora_config)
    model.enable_input_require_grads()
    model.train()
    
    model.print_trainable_parameters()
    
    # Collator
    class PromptMaskedCollator:
        def __init__(self, tokenizer, pad_to_multiple_of=8):
            self.tok = tokenizer
            self.pad_to_multiple_of = pad_to_multiple_of

        def __call__(self, features):
            prompt_len = torch.tensor([f["prompt_len"] for f in features], dtype=torch.long)
            
            feats_wo_plen = [{k: v for k, v in f.items() if k != "prompt_len"} for f in features]
            
            batch = self.tok.pad(
                feats_wo_plen,
                padding=True,
                return_tensors="pt",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
            
            input_ids = batch["input_ids"]
            attn = batch["attention_mask"]
            
            T = input_ids.size(1)
            ar = torch.arange(T, device=input_ids.device).unsqueeze(0)
            plen = prompt_len.unsqueeze(1).to(device=input_ids.device)
            
            labels = input_ids.clone()
            labels[ar < plen] = -100
            labels[attn == 0] = -100
            
            batch["labels"] = labels
            return batch
    
    collator = PromptMaskedCollator(tokenizer)
    
    # Compute metrics function for evaluation
    # Note: The Trainer automatically computes loss, so we just compute perplexity from it
    def compute_metrics(eval_pred):
        """Compute perplexity from evaluation predictions."""
        from transformers import EvalPrediction
        import numpy as np
        
        # eval_pred is an EvalPrediction object with predictions and label_ids
        if isinstance(eval_pred, EvalPrediction):
            predictions = eval_pred.predictions
            labels = eval_pred.label_ids
        else:
            predictions, labels = eval_pred
        
        # Convert to numpy if needed
        if isinstance(predictions, torch.Tensor):
            predictions = predictions.cpu().numpy()
        if isinstance(labels, torch.Tensor):
            labels = labels.cpu().numpy()
        
        # The loss is already computed by the Trainer, so we'll compute perplexity
        # from the logits if available, otherwise we'll use the loss from metrics
        # For now, we'll just return empty dict - perplexity will be computed from loss
        return {}
    
    # Training arguments
    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=50,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=100,
        save_total_limit=3,
        fp16=True,
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
        group_by_length=True,
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        greater_is_better=False,
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_tok,
        eval_dataset=val_tok,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )
    
    # Check for existing checkpoints to resume from
    checkpoint_dir = None
    if os.path.exists(OUTPUT_DIR):
        # Look for checkpoint directories (format: checkpoint-{step})
        import glob
        checkpoint_dirs = glob.glob(os.path.join(OUTPUT_DIR, "checkpoint-*"))
        if checkpoint_dirs:
            # Sort by step number and get the latest
            checkpoint_dirs.sort(key=lambda x: int(x.split("-")[-1]))
            checkpoint_dir = checkpoint_dirs[-1]
            print(f"\nFound existing checkpoint: {checkpoint_dir}")
            print("Resuming training from checkpoint...")
        else:
            # Check if there's a training state file (for Trainer resume)
            training_state_file = os.path.join(OUTPUT_DIR, "trainer_state.json")
            if os.path.exists(training_state_file):
                print(f"\nFound training state file: {training_state_file}")
                print("Resuming training from last checkpoint...")
                checkpoint_dir = True  # True means auto-detect latest checkpoint
    
    # Train
    print("\nStarting training...")
    if checkpoint_dir:
        train_result = trainer.train(resume_from_checkpoint=checkpoint_dir)
    else:
        train_result = trainer.train()
    
    # Print training metrics
    train_loss = train_result.metrics.get('train_loss', 0)
    train_perplexity = torch.exp(torch.tensor(train_loss)).item()
    
    print("\n" + "=" * 60)
    print("Training Metrics:")
    print("=" * 60)
    print(f"Train Loss: {train_loss:.4f}")
    print(f"Train Perplexity: {train_perplexity:.4f}")
    print(f"Train Runtime: {train_result.metrics.get('train_runtime', 'N/A'):.2f}s")
    print(f"Train Samples Per Second: {train_result.metrics.get('train_samples_per_second', 'N/A'):.2f}")
    
    # Evaluate on validation set
    print("\nEvaluating on validation set...")
    eval_results = trainer.evaluate()
    
    eval_loss = eval_results.get('eval_loss', 0)
    eval_perplexity = torch.exp(torch.tensor(eval_loss)).item()
    
    print("\n" + "=" * 60)
    print("Validation Metrics:")
    print("=" * 60)
    print(f"Validation Loss: {eval_loss:.4f}")
    print(f"Validation Perplexity: {eval_perplexity:.4f}")
    print(f"Validation Runtime: {eval_results.get('eval_runtime', 'N/A'):.2f}s")
    
    # Also evaluate on training set (sample)
    print("\nEvaluating on training set (sample)...")
    sample_size = min(100, len(train_tok))
    train_eval_results = trainer.evaluate(eval_dataset=train_tok.select(range(sample_size)))
    
    train_sample_loss = train_eval_results.get('eval_loss', 0)
    train_sample_perplexity = torch.exp(torch.tensor(train_sample_loss)).item()
    
    print("\n" + "=" * 60)
    print(f"Training Set Metrics (sample of {sample_size}):")
    print("=" * 60)
    print(f"Train Loss (sample): {train_sample_loss:.4f}")
    print(f"Train Perplexity (sample): {train_sample_perplexity:.4f}")
    
    # Save metrics to file
    metrics_file = os.path.join(OUTPUT_DIR, "training_metrics.json")
    all_metrics = {
        "train": {
            **train_result.metrics,
            "train_perplexity": train_perplexity,
        },
        "validation": {
            **eval_results,
            "eval_perplexity": eval_perplexity,
        },
        "train_sample": {
            **train_eval_results,
            "eval_perplexity": train_sample_perplexity,
            "sample_size": sample_size,
        },
    }
    with open(metrics_file, 'w') as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\n✓ Metrics saved to {metrics_file}")
    
    # Save model
    print("\nSaving model...")
    trainer.save_model()
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # Merge LoRA weights
    print("\nMerging LoRA weights...")
    peft_model = AutoPeftModelForCausalLM.from_pretrained(
        OUTPUT_DIR, torch_dtype=torch.float16, device_map="auto"
    )
    merged = peft_model.merge_and_unload()
    merged_output_dir = f"{OUTPUT_DIR}_merged"
    merged.save_pretrained(merged_output_dir, safe_serialization=True)
    tokenizer.save_pretrained(merged_output_dir)
    
    # Commit volume to persist the model
    print("\nCommitting model to persistent volume...")
    # The volume is automatically committed when the function completes
    # Files written to /models are persisted in the volume
    
    print(f"\nTraining complete! Model saved to {merged_output_dir}")
    print(f"Model persisted in Modal Volume: threejs-codellama-models")
    print(f"Use download_model.py to download the model locally")
    
    # Upload to HuggingFace Hub (optional)
    # model.push_to_hub("your-username/threejs-codellama")
    # tokenizer.push_to_hub("your-username/threejs-codellama")


@app.local_entrypoint()
def main():
    """Entry point for Modal."""
    train_codellama_threejs.remote()


if __name__ == "__main__":
    with app.run():
        train_codellama_threejs.remote()

