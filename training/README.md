# Three.js Code Generation Training

This directory contains scripts and notebooks for fine-tuning CodeLlama to generate Three.js code from image descriptions.

## Recent Changes

**Simplified Workflow**: The training pipeline has been simplified to use existing Three.js code files from the official repository instead of generating code. This means:

- ✅ **No code generation step**: We directly pair descriptions (`.md` files) with existing code (`.js` files)
- ✅ **No Qwen3VL evaluation during data prep**: All matching pairs are included (no score filtering)
- ✅ **Faster data preparation**: Simply matches files instead of generating and evaluating code
- ✅ **Higher quality training data**: Uses ground truth code from the official Three.js examples

The `prepare_training_data.py` script now simply matches `.md` files with corresponding `_module.js` files from the `extracted_scripts/` directory.

## Files

- `train_threejs_modal.py` - Modal-compatible training script for cloud training
- `prepare_training_data.py` - Script to pair descriptions (.md) with code (.js) files
- `test_model.py` - **Test script to evaluate model accuracy with Qwen3VL**
- `use_model.py` - Example script for generating code with the fine-tuned model
- `view_metrics.py` - Script to view training metrics from JSON file
- `train_threejs.py` - Local training script (alternative to Modal)
- `train_threejs.ipynb` - Jupyter notebook version (to be created)
- `extracted_scripts/` - Directory containing Three.js code files (from official repository)

## Workflow

### Step 1: Prepare Training Data

Pair existing descriptions with their corresponding Three.js code files:

```bash
python training/prepare_training_data.py \
    --screenshots-dir image_to_prompt/screenshots \
    --scripts-dir training/extracted_scripts \
    --output training/training_data.json
```

This will:
1. Load all .md description files from the screenshots directory
2. Match them with corresponding .js code files from extracted_scripts (removing `_module.js` suffix)
3. Create training pairs (description, code)
4. Save all pairs to `training_data.json`

### Step 2: Train on Modal

Deploy and run training on Modal:

```bash
cd training
modal deploy train_threejs_modal.py
modal run train_threejs_modal.py
```

Or use the Jupyter notebook for interactive training.

## Training Approach

The training uses **Supervised Fine-Tuning (SFT)** with **LoRA**:

1. **Input**: Description from .md file
2. **Output**: Three.js JavaScript code
3. **Training**: Fine-tune CodeLlama on description→code pairs from the official Three.js repository

### Model Configuration

- **Base Model**: `codellama/CodeLlama-7b-Instruct-hf`
- **Method**: LoRA (Low-Rank Adaptation)
- **LoRA Config**:
  - `r=8`
  - `lora_alpha=16`
  - `lora_dropout=0.05`
  - Target modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`

### Training Hyperparameters

- **Epochs**: 50
- **Batch size**: 2 per device × 4 gradient accumulation = 8 effective
- **Learning rate**: 2e-4
- **Scheduler**: Cosine with 3% warmup
- **Max sequence length**: 2048 tokens
- **GPU**: B200

## Dataset Structure

The training data JSON file contains:

```json
[
  {
    "description": "Scene description from .md file...",
    "code": "Three.js code from extracted_scripts...",
    "filename": "webgl_example",
    "md_file": "webgl_example.md",
    "js_file": "webgl_example_module.js"
  },
  ...
]
```

Each entry pairs a description (from `image_to_prompt/screenshots/*.md`) with its corresponding Three.js code (from `training/extracted_scripts/*_module.js`).

## Evaluation

After training, test the model's accuracy using the testing script:

```bash
python training/test_model.py \
    --model-path ./models/threejs_codellama/threejs_codellama_lora_merged \
    --n 20 \
    --output test_results.json
```

This will:
1. Load the fine-tuned model
2. Generate code for n test examples (from validation set by default)
3. Render each generated code to a screenshot
4. Evaluate each screenshot with Qwen3VL to get a rating (0.0-1.0)
5. Report the **sum of all ratings** and number of examples tested

**Accuracy Metric**: Sum of Qwen3VL ratings across n examples

**Options**:
- `--n`: Number of test examples (default: 10)
- `--test-data`: Path to training_data.json (default: training/training_data.json)
- `--use-training-set`: Use training set instead of validation set
- `--output`: Output file for detailed results (default: test_results.json)
- `--max-tokens`: Maximum tokens to generate per example (default: 512)

**Example Output**:
```
Sum of Qwen3VL ratings: 15.234
Average rating: 0.762
Number of examples with ratings: 20
```

## Notes

- **Data Source**: The training uses ground truth code examples from the official Three.js repository (stored in `extracted_scripts/`)
- **No Filtering**: All matching description-code pairs are included in the training set (no Qwen3VL score filtering needed)
- **File Matching**: Files are matched by base name - `{base_name}.md` pairs with `{base_name}_module.js`
- **Modal Requirements**: Training requires GPU (B200 configured)
- **Training Time**: ~10-20 hours for 500+ examples with 50 epochs on B200
- **Dependencies**: The training script no longer requires Playwright or Qwen3VL API access (removed from Modal image)

## What Was Removed

The following features were removed to simplify the workflow:

- ❌ Code generation using CodeLlama API during data preparation
- ❌ Screenshot rendering and Qwen3VL evaluation during data prep
- ❌ Score-based filtering of training examples
- ❌ Playwright and browser automation dependencies in training script

These were replaced with direct file pairing since we have access to the original Three.js code files.

