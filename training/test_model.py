"""
Test the fine-tuned CodeLlama model's accuracy on generating Three.js code.

Accuracy is defined as the sum of Qwen3VL ratings across n test examples.

Usage:
    python test_model.py --model-path ./models/threejs_codellama/threejs_codellama_lora_merged --n 10
    python test_model.py --model-path ./models/threejs_codellama/threejs_codellama_lora_merged --test-data training/training_data.json --n 20
"""

import argparse
import json
import os
import sys
import tempfile
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add pipeline to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pipeline'))
from load_code import load_and_render_threejs
from eval_screenshot import extract_rating, create_evaluation_prompt
import requests
import base64


def generate_threejs_code(model, tokenizer, description: str, max_new_tokens: int = 512) -> str:
    """
    Generate Three.js code from a scene description using the fine-tuned model.
    
    Args:
        model: Loaded model
        tokenizer: Loaded tokenizer
        description: Scene description text
        max_new_tokens: Maximum number of tokens to generate
    
    Returns:
        Generated Three.js code as a string
    """
    # Create prompt in CodeLlama format
    prompt = f"""<s>[INST] Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting
- Include any animations or interactions if described

Return only the JavaScript code without markdown formatting. [/INST]"""
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    # Decode
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract code (everything after [/INST])
    if "[/INST]" in generated_text:
        code = generated_text.split("[/INST]")[-1].strip()
    else:
        code = generated_text
    
    return code


def evaluate_screenshot_with_qwen3vl(screenshot_path: str, reference_description: str) -> Optional[float]:
    """
    Evaluate a screenshot against a reference description using Qwen3VL.
    
    Args:
        screenshot_path: Path to the screenshot image
        reference_description: Reference description to compare against
    
    Returns:
        Rating (0.0-1.0) or None if evaluation failed
    """
    try:
        # Read and encode image
        with open(screenshot_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        # Create evaluation prompt
        prompt = create_evaluation_prompt(reference_description)
        
        # Send request to Qwen3VL API
        response = requests.post(
            "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate",
            json={
                "image": {"image_base64": base64_image},
                "prompt": prompt
            },
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        if "annotation" in result:
            annotation = result["annotation"]
            rating = extract_rating(annotation)
            return rating
        
        return None
        
    except Exception as e:
        print(f"  ⚠️  Error evaluating screenshot: {e}")
        return None


async def test_single_example(
    model,
    tokenizer,
    description: str,
    example_idx: int,
    total: int,
    temp_dir: str
) -> Dict:
    """
    Test a single example: generate code, render, and evaluate.
    
    Returns:
        Dictionary with test results
    """
    print(f"\n[{example_idx + 1}/{total}] Testing example...")
    print(f"  Description: {description[:100]}..." if len(description) > 100 else f"  Description: {description}")
    
    result = {
        "description": description,
        "rating": None,
        "error": None,
        "code_generated": False,
        "screenshot_created": False,
    }
    
    try:
        # Step 1: Generate code
        print("  Generating code...")
        code = generate_threejs_code(model, tokenizer, description)
        result["code_generated"] = True
        result["code_length"] = len(code)
        
        # Step 2: Render screenshot
        print("  Rendering screenshot...")
        screenshot_path = os.path.join(temp_dir, f"screenshot_{example_idx}.jpg")
        
        await load_and_render_threejs(
            code,
            output_path=screenshot_path,
            keep_server_running=False,
            project_dir=temp_dir
        )
        
        if os.path.exists(screenshot_path):
            result["screenshot_created"] = True
        else:
            result["error"] = "Screenshot not created"
            return result
        
        # Step 3: Evaluate with Qwen3VL
        print("  Evaluating with Qwen3VL...")
        rating = evaluate_screenshot_with_qwen3vl(screenshot_path, description)
        
        if rating is not None:
            result["rating"] = rating
            print(f"  ✓ Rating: {rating:.3f}")
        else:
            result["error"] = "Could not extract rating from Qwen3VL response"
            print(f"  ✗ Failed to get rating")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"  ✗ Error: {e}")
    
    return result


def load_test_data(data_file: str, n: int = None, use_validation: bool = True) -> List[Dict]:
    """
    Load test data from training_data.json.
    
    Args:
        data_file: Path to training_data.json
        n: Number of examples to use (None = all)
        use_validation: If True, use validation split (last 20%), else use training split
    
    Returns:
        List of test examples with descriptions
    """
    with open(data_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    # Split into train/val (80/20)
    split_idx = int(len(all_data) * 0.8)
    
    if use_validation:
        test_data = all_data[split_idx:]
        print(f"Using validation set: {len(test_data)} examples")
    else:
        test_data = all_data[:split_idx]
        print(f"Using training set: {len(test_data)} examples")
    
    # Limit to n examples if specified
    if n is not None and n < len(test_data):
        test_data = test_data[:n]
        print(f"Limited to {n} examples for testing")
    
    return test_data


async def main():
    parser = argparse.ArgumentParser(description="Test fine-tuned CodeLlama model accuracy")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the fine-tuned model directory"
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "training_data.json"),
        help="Path to training_data.json for test examples"
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of test examples to evaluate"
    )
    parser.add_argument(
        "--use-training-set",
        action="store_true",
        help="Use training set instead of validation set for testing"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file to save detailed results"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate per example"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Testing Fine-tuned CodeLlama Model")
    print("=" * 60)
    print(f"\nModel: {args.model_path}")
    print(f"Test examples: {args.n}")
    print(f"Test set: {'Training' if args.use_training_set else 'Validation'}")
    
    # Load model
    print("\nLoading model...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.model_path)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        print("✓ Model loaded")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return
    
    # Load test data
    print(f"\nLoading test data from {args.test_data}...")
    try:
        test_data = load_test_data(
            args.test_data,
            n=args.n,
            use_validation=not args.use_training_set
        )
    except Exception as e:
        print(f"✗ Error loading test data: {e}")
        return
    
    if len(test_data) == 0:
        print("✗ No test data found")
        return
    
    # Create temporary directory for screenshots
    temp_dir = tempfile.mkdtemp(prefix="threejs_test_")
    print(f"\nUsing temp directory: {temp_dir}")
    
    # Test each example
    results = []
    for i, example in enumerate(test_data):
        description = example.get('description', '')
        if not description:
            continue
        
        result = await test_single_example(
            model,
            tokenizer,
            description,
            i,
            len(test_data),
            temp_dir
        )
        results.append(result)
    
    # Calculate summary statistics
    successful_results = [r for r in results if r["rating"] is not None]
    ratings = [r["rating"] for r in successful_results]
    
    total_score = sum(ratings) if ratings else 0.0
    num_tested = len(successful_results)
    num_failed = len(results) - num_tested
    average_rating = total_score / num_tested if num_tested > 0 else 0.0
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Total examples tested: {len(results)}")
    print(f"Successful evaluations: {num_tested}")
    print(f"Failed evaluations: {num_failed}")
    print(f"\nSum of Qwen3VL ratings: {total_score:.3f}")
    print(f"Average rating: {average_rating:.3f}")
    print(f"Number of examples with ratings: {num_tested}")
    
    if ratings:
        print(f"\nRating statistics:")
        print(f"  Min: {min(ratings):.3f}")
        print(f"  Max: {max(ratings):.3f}")
        print(f"  Median: {sorted(ratings)[len(ratings)//2]:.3f}")
    
    # Save detailed results
    summary = {
        "model_path": args.model_path,
        "total_examples": len(results),
        "successful_evaluations": num_tested,
        "failed_evaluations": num_failed,
        "sum_of_ratings": total_score,
        "average_rating": average_rating,
        "num_tested": num_tested,
        "results": results,
    }
    
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Detailed results saved to {output_path}")
    print("=" * 60)
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())

