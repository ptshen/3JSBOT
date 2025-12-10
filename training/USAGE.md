# Usage Guide: Training CodeLlama for Three.js Code Generation

## Overview

This training pipeline fine-tunes CodeLlama to generate Three.js code from scene descriptions. The process involves:

1. **Data Preparation**: Pair existing descriptions (.md) with Three.js code files (.js)
2. **Training**: Fine-tune CodeLlama using SFT with LoRA
3. **Evaluation**: Test the model on new descriptions

## Quick Start

### Option 1: Modal Training (Recommended)

1. **Prepare training data** (run locally):
```bash
cd /Users/patrick/Documents/school/nlp/final_project
python training/prepare_training_data.py \
    --screenshots-dir image_to_prompt/screenshots \
    --scripts-dir training/extracted_scripts \
    --output training/training_data.json
```

2. **Deploy and train on Modal**:
```bash
cd training
modal deploy train_threejs_modal.py
modal run train_threejs_modal.py
```

### Option 2: Local Training

1. **Prepare training data** (same as above)

2. **Train locally** (requires GPU):
```bash
python training/train_threejs.py
```

## Detailed Steps

### Step 1: Data Preparation

The `prepare_training_data.py` script:

- Loads all `.md` description files from `image_to_prompt/screenshots/`
- Matches them with corresponding `.js` code files from `training/extracted_scripts/`
- Creates training pairs (description, code)
- Saves all pairs to `training_data.json`

**Example output:**
```json
[
  {
    "description": "This three.js rendered scene displays...",
    "code": "import * as THREE from 'three';\n...",
    "filename": "webgl_cubes",
    "md_file": "webgl_cubes.md",
    "js_file": "webgl_cubes_module.js"
  }
]
```

**Parameters:**
- `--screenshots-dir`: Directory containing .md files (default: `image_to_prompt/screenshots`)
- `--scripts-dir`: Directory containing .js files (default: `training/extracted_scripts`)
- `--output`: Output JSON file path (default: `training_data.json`)

**Note**: The script matches files by base name. For example, `webgl_cubes.md` pairs with `webgl_cubes_module.js`.

### Step 2: Training

The training script (`train_threejs_modal.py` or `train_threejs.py`):

1. Loads prepared training data
2. Tokenizes description→code pairs
3. Fine-tunes CodeLlama with LoRA
4. Saves the fine-tuned model

**Training Configuration:**
- Model: `codellama/CodeLlama-7b-Instruct-hf`
- Method: LoRA (r=8, alpha=16)
- Batch size: 2 × 4 accumulation = 8 effective
- Learning rate: 2e-4
- Epochs: 3

### Step 3: Evaluation

After training, evaluate the model:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("./threejs_codellama_lora_merged")
tokenizer = AutoTokenizer.from_pretrained("./threejs_codellama_lora_merged")

# Generate code for a description
description = "A scene with rotating cubes..."
prompt = f"""<s>[INST] Generate Three.js code for: {description} [/INST]"""

inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=512)
code = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Render and evaluate
from pipeline.run_pipeline import run_pipeline
results = run_pipeline(description)
print(f"Score: {results['rating']}")
```

## Adapting the Original Notebook

To convert `train.ipynb` to work with Three.js:

1. **Change model**: Replace `meta-llama/Llama-3.2-1B` with `codellama/CodeLlama-7b-Instruct-hf`

2. **Change dataset loading**: Replace GSM8K loading with:
```python
from prepare_training_data import load_screenshots_dataset
dataset = load_screenshots_dataset("image_to_prompt/screenshots")
```

3. **Change prompt format**: Use CodeLlama's instruction format:
```python
def create_prompt(description):
    return f"""<s>[INST] Generate Three.js code for: {description} [/INST]"""
```

4. **Change evaluation**: Replace math evaluation with screenshot rendering + Qwen3VL scoring

5. **Update tokenization**: Include code in training examples (not just descriptions)

## Modal Setup

1. **Install Modal**:
```bash
pip install modal
modal setup
```

2. **Set up secrets** (for HuggingFace token):
```bash
modal secret create huggingface HF_TOKEN=your_token_here
```

3. **Deploy**:
```bash
modal deploy train_threejs_modal.py
```

## Troubleshooting

### "training_data.json not found"
- Run `prepare_training_data.py` first
- Check that the output path is correct

### "No matching JS file" warnings
- Ensure `.js` files are named as `{base_name}_module.js` to match `{base_name}.md` files
- Check that `extracted_scripts/` directory contains the code files
- Verify file naming matches between .md and .js files

### "Out of memory" errors
- Reduce batch size in `TrainingArguments`
- Use gradient checkpointing (already enabled)
- Use a smaller model or reduce `r` in LoRA config

### "Empty training_data.json"
- Check that both .md and .js files exist
- Verify the directory paths are correct
- Ensure file names match (excluding `_module.js` suffix)

## Next Steps

- Experiment with different LoRA configurations
- Try reinforcement learning (RL) using Qwen3VL scores as rewards
- Fine-tune on specific Three.js features (e.g., only WebGL examples)
- Create a validation loop that evaluates during training


