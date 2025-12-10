"""
Fine-tune CodeLlama for Three.js code generation from image descriptions.

This script adapts the GSM8K training approach to:
1. Load descriptions from .md files in screenshots folder
2. Fine-tune CodeLlama to generate Three.js code from descriptions
3. Evaluate generated code by rendering screenshots and scoring with Qwen3VL
4. Train using SFT (Supervised Fine-Tuning) with LoRA

Modal-compatible for cloud training.
"""

import os
import sys
import json
import re
import glob
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, AutoPeftModelForCausalLM
from datasets import Dataset
import requests
import base64

# Add pipeline directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))
from load_code import render_threejs, read_js_from_file
from generate_code import extract_code_from_markdown


# Configuration
MODEL_NAME = "codellama/CodeLlama-7b-Instruct-hf"  # CodeLlama model
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'image_to_prompt', 'screenshots')
EVAL_API_URL = "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate"
MAX_LEN = 2048  # Maximum sequence length
BUDGET = MAX_LEN - 1


def load_screenshots_dataset(screenshots_dir: str) -> List[Dict[str, str]]:
    """
    Load all .md files from screenshots directory.
    
    Each .md file contains a description of a Three.js scene.
    Returns a list of dictionaries with 'description' and 'filename' keys.
    """
    md_files = glob.glob(os.path.join(screenshots_dir, "*.md"))
    dataset = []
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract description (skip the first line which is usually the filename)
                lines = content.strip().split('\n')
                description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else content.strip()
                
                dataset.append({
                    'description': description,
                    'filename': os.path.basename(md_file),
                    'filepath': md_file
                })
        except Exception as e:
            print(f"Error loading {md_file}: {e}")
            continue
    
    print(f"Loaded {len(dataset)} descriptions from {screenshots_dir}")
    return dataset


def create_prompt(description: str) -> str:
    """
    Create a prompt for CodeLlama to generate Three.js code from description.
    """
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


def extract_rating(text: str) -> float:
    """Extract a 0-1 rating from Qwen3VL's response."""
    import re
    # First, try to find "RATING:" prefix followed by a number
    rating_prefix_pattern = r'RATING:\s*([0-9]*\.?[0-9]+|\.\d+)'
    match = re.search(rating_prefix_pattern, text, re.IGNORECASE)
    if match:
        try:
            rating = float(match.group(1))
            return max(0.0, min(1.0, rating))
        except ValueError:
            pass
    
    # Also check for percentage after RATING:
    rating_percent_pattern = r'RATING:\s*(\d+)%'
    match = re.search(rating_percent_pattern, text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1)) / 100.0
        except ValueError:
            pass
    
    # Fallback: Look for patterns like "0.85", "0.9", "1.0", etc.
    patterns = [
        r'\b1\.0\b',
        r'\b0\.\d{1,2}\b',
        r'\b0?\.\d+\b',
        r'\b\d+%\b',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            match = matches[0]
            if '%' in match:
                return max(0.0, min(1.0, float(match.replace('%', '')) / 100.0))
            else:
                rating = float(match)
                return max(0.0, min(1.0, rating))
    
    return None


def create_evaluation_prompt(reference_description: str) -> str:
    """Create a prompt for evaluating image accuracy against a reference description."""
    return f"""Compare the provided image to the following reference description and evaluate how accurately the image matches the description.

REFERENCE DESCRIPTION:
{reference_description}

Your task:
1. Carefully analyze the image and identify all key elements, objects, attributes, spatial relationships, and visual features
2. Compare each aspect of the image to the reference description
3. Consider:
   - Presence/absence of described objects
   - Accuracy of attributes (colors, sizes, positions, states)
   - Spatial relationships and layout
   - Actions or interactions if described
   - Overall scene composition

4. Provide a numerical rating from 0.0 to 1.0 where:
   - 1.0 = Perfect match, all elements accurately match the description
   - 0.8-0.9 = Very high accuracy, minor discrepancies
   - 0.6-0.7 = Good match, some differences but core elements present
   - 0.4-0.5 = Moderate match, significant differences but some elements correct
   - 0.2-0.3 = Poor match, few elements match
   - 0.0-0.1 = No match or completely different

5. Format your response as:
   RATING: [number between 0.0 and 1.0]
   ANALYSIS: [brief explanation of what matches and what doesn't]

Be precise and objective in your evaluation. Remember that the image is a static screenshot from a Three.js animation."""


def evaluate_code_with_qwen3vl(
    generated_code: str,
    reference_description: str,
    screenshot_path: str = None,
    temp_dir: str = None
) -> Dict:
    """
    Generate screenshot from code and evaluate with Qwen3VL.
    
    Returns dict with 'rating', 'analysis', 'screenshot_path', and 'errors'.
    """
    import tempfile
    import asyncio
    from load_code import load_and_render_threejs
    
    results = {
        'rating': None,
        'analysis': None,
        'screenshot_path': None,
        'errors': []
    }
    
    # Create temporary directory for screenshot if not provided
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="threejs_eval_")
        cleanup_temp = True
    else:
        cleanup_temp = False
    
    try:
        # Step 1: Render the code to screenshot
        screenshot_path = os.path.join(temp_dir, "screenshot.jpg")
        
        # Use asyncio to run the async render function
        try:
            asyncio.run(load_and_render_threejs(
                generated_code,
                output_path=screenshot_path,
                keep_server_running=False,
                project_dir=temp_dir
            ))
        except Exception as e:
            results['errors'].append(f"Rendering error: {e}")
            return results
        
        if not os.path.exists(screenshot_path):
            results['errors'].append("Screenshot file not created")
            return results
        
        results['screenshot_path'] = screenshot_path
        
        # Step 2: Evaluate with Qwen3VL
        try:
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            eval_prompt = create_evaluation_prompt(reference_description)
            
            response = requests.post(
                EVAL_API_URL,
                json={
                    "image": {"image_base64": base64_image},
                    "prompt": eval_prompt
                },
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "annotation" in result:
                annotation = result["annotation"]
                rating = extract_rating(annotation)
                
                results['rating'] = rating
                results['analysis'] = annotation
            else:
                results['errors'].append("Unexpected response format from evaluation API")
                
        except Exception as e:
            results['errors'].append(f"Evaluation error: {e}")
            
    finally:
        # Clean up temporary directory if we created it
        if cleanup_temp and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    return results


class PromptMaskedCollator:
    """Collator that masks prompt tokens in labels."""
    
    def __init__(self, tokenizer, pad_to_multiple_of=8):
        self.tok = tokenizer
        self.pad_to_multiple_of = pad_to_multiple_of

    def __call__(self, features):
        prompt_len = torch.tensor([f["prompt_len"] for f in features], dtype=torch.long)
        
        feats_wo_plen = [{k: v for k, v in f.items() if k not in ["prompt_len", "description", "filename"]} for f in features]
        
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
        
        # Mask prompt tokens in labels
        labels = input_ids.clone()
        labels[ar < plen] = -100  # Mask prompt tokens
        labels[attn == 0] = -100  # Mask padding tokens
        
        batch["labels"] = labels
        return batch


def tokenize_batch(batch, tokenizer, system_prompt_ids, max_len=MAX_LEN):
    """
    Tokenize a batch of descriptions.
    
    Returns dict with 'input_ids', 'prompt_len', 'description', 'filename'.
    """
    descriptions = [d.rstrip() for d in batch["description"]]
    
    # Create prompts
    prompts = [create_prompt(desc) for desc in descriptions]
    
    # Tokenize prompts
    enc = tokenizer(prompts, add_special_tokens=False, padding=False, truncation=False)
    
    input_ids_list = []
    prompt_len_list = []
    
    for prompt_ids in enc["input_ids"]:
        # Combine system prompt (if any) with prompt
        ids = system_prompt_ids + prompt_ids if len(system_prompt_ids) > 0 else prompt_ids
        
        # Truncate if too long
        if len(ids) > max_len:
            excess = len(ids) - max_len
            ids = ids[excess:]
        
        input_ids_list.append(ids)
        prompt_len_list.append(len(ids))  # For now, we'll mask everything except the last token
    
    return {
        "input_ids": input_ids_list,
        "prompt_len": prompt_len_list,
        "description": batch["description"],
        "filename": batch["filename"]
    }


def main():
    """Main training function."""
    
    print("=" * 60)
    print("CodeLlama Fine-tuning for Three.js Code Generation")
    print("=" * 60)
    
    # Load dataset
    print("\nLoading dataset...")
    dataset = load_screenshots_dataset(SCREENSHOTS_DIR)
    
    if len(dataset) == 0:
        print("ERROR: No descriptions found!")
        return
    
    # Split into train/val (80/20)
    split_idx = int(len(dataset) * 0.8)
    train_data = dataset[:split_idx]
    val_data = dataset[split_idx:]
    
    print(f"Train: {len(train_data)} examples")
    print(f"Val: {len(val_data)} examples")
    
    # Initialize tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    tokenizer.padding_side = "right"
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    tokenizer.truncation_side = "left"
    
    # System prompt IDs (empty for now, can add if needed)
    system_prompt_ids = []
    
    # Tokenize datasets
    print("\nTokenizing datasets...")
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    def tokenize_fn(examples):
        return tokenize_batch(examples, tokenizer, system_prompt_ids, MAX_LEN)
    
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
    print("\nLoading model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map="auto",
        torch_dtype=torch.float16,
        attn_implementation="sdpa",
    )
    
    model.config.use_cache = False
    
    # Configure LoRA
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
    
    # Initialize collator
    collator = PromptMaskedCollator(tokenizer)
    
    # Training arguments
    output_dir = "./threejs_codellama_lora"
    
    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
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
        bf16=False,
        fp16=True,
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
        group_by_length=True,
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_tok,
        eval_dataset=val_tok,
        data_collator=collator,
    )
    
    # Train
    print("\nStarting training...")
    trainer.train()
    
    # Save model
    print("\nSaving model...")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    
    # Merge LoRA weights
    print("\nMerging LoRA weights...")
    peft_model = AutoPeftModelForCausalLM.from_pretrained(
        output_dir, torch_dtype=torch.float16, device_map="auto"
    )
    merged = peft_model.merge_and_unload()
    merged.save_pretrained(f"{output_dir}_merged", safe_serialization=True)
    tokenizer.save_pretrained(f"{output_dir}_merged")
    
    print(f"\nTraining complete! Model saved to {output_dir}_merged")


if __name__ == "__main__":
    main()

