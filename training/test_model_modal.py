"""
Test the fine-tuned model directly on Modal without downloading.

Usage:
    modal run test_model_modal.py --n 20
"""

import modal
import os
import json
import asyncio
import tempfile
from pathlib import Path

app = modal.App("threejs-codellama-test")

# Use the same volume where the model was saved
model_volume = modal.Volume.from_name("threejs-codellama-models", create_if_missing=False)

image = (
    modal.Image.debian_slim()
    .apt_install("git", "curl", "build-essential")
    .pip_install(
        "torch>=2.0.0",
        "transformers>=4.35.0",
        "peft>=0.6.0",
        "playwright>=1.40.0",
        "requests>=2.31.0",
    )
    .run_commands("playwright install chromium")
    .run_commands("playwright install-deps chromium")
    # Add training data
    .add_local_file(
        os.path.join(os.path.dirname(__file__), "training_data.json"),
        "/root/training_data.json",
        copy=True
    )
    # Add pipeline files
    .add_local_dir(
        os.path.join(os.path.dirname(__file__), "..", "pipeline"),
        remote_path="/root/project/pipeline"
    )
)


@app.function(
    image=image,
    volumes={"/models": model_volume},
    gpu="T4",  # Use T4 for inference (cheaper than B200)
    timeout=3600 * 2,  # 2 hour timeout
)
def test_model_on_modal(n: int = 20):
    """Test the model directly on Modal."""
    import sys
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import base64
    import requests
    
    sys.path.insert(0, "/root/project/pipeline")
    from load_code import load_and_render_threejs
    from eval_screenshot import extract_rating, create_evaluation_prompt
    
    MODEL_PATH = "/models/threejs_codellama_lora_merged"
    
    print("=" * 60)
    print("Testing Fine-tuned CodeLlama Model on Modal")
    print("=" * 60)
    
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        print("Available paths in /models:")
        if os.path.exists("/models"):
            for item in os.listdir("/models"):
                print(f"  - {item}")
        return {"error": "Model not found"}
    
    # Load model
    print(f"\nLoading model from {MODEL_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    print("✓ Model loaded")
    
    # Load test data
    print("\nLoading test data...")
    with open("/root/training_data.json", 'r') as f:
        all_data = json.load(f)
    
    # Use validation set
    split_idx = int(len(all_data) * 0.8)
    test_data = all_data[split_idx:][:n]
    print(f"Testing on {len(test_data)} examples")
    
    # Test each example
    results = []
    total_score = 0.0
    successful = 0
    
    for i, example in enumerate(test_data):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(test_data)}] Testing Example")
        print(f"{'='*60}")
        description = example.get('description', '')
        filename = example.get('filename', f'example_{i+1}')
        
        print(f"\n📝 Test Description (Prompt):")
        print(f"{'-'*60}")
        print(description)
        print(f"{'-'*60}")
        print(f"📁 Filename: {filename}")
        
        rating = None
        error_msg = None
        generated_code = None
        full_prompt = None
        
        try:
            # Generate code
            print(f"\n🔧 Generating code...")
            prompt = f"""<s>[INST] Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting
- Include any animations or interactions if described

Return only the JavaScript code without markdown formatting. [/INST]"""
            
            full_prompt = prompt
            print(f"\n📋 Full Prompt (No Truncation):")
            print(f"{'='*60}")
            print(prompt)
            print(f"{'='*60}")
            print(f"Prompt length: {len(prompt)} characters")
            
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                # Clear CUDA cache before generation to free up memory
                torch.cuda.empty_cache()
                
                outputs = model.generate(
                    **inputs, 
                    max_new_tokens=2048,  # Reduced to avoid OOM - can generate ~1500-2000 lines of code
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    # Memory-efficient generation settings
                    use_cache=True,  # Use KV cache to reduce memory
                )
                
                # Clear cache after generation
                torch.cuda.empty_cache()
            full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            if "[/INST]" in full_response:
                generated_code = full_response.split("[/INST]")[-1].strip()
            else:
                generated_code = full_response.strip()
            
            print(f"\n💻 Generated Code (Full - No Truncation):")
            print(f"{'='*60}")
            print(generated_code)
            print(f"{'='*60}")
            print(f"Code length: {len(generated_code)} characters")
            print(f"Number of lines: {len(generated_code.split(chr(10)))}")
            
            # Render screenshot
            print("\n🖼️  Rendering screenshot...")
            temp_dir = tempfile.mkdtemp()
            screenshot_path = os.path.join(temp_dir, "screenshot.jpg")
            
            # Use local Three.js files from pipeline directory (not CDN)
            pipeline_dir = "/root/project/pipeline"
            
            try:
                asyncio.run(load_and_render_threejs(
                    generated_code, 
                    screenshot_path, 
                    project_dir=temp_dir,
                    pipeline_dir=pipeline_dir
                ))
                
                # Check if screenshot was created
                if not os.path.exists(screenshot_path):
                    raise Exception("Screenshot file was not created")
                
            except Exception as render_error:
                # Rendering error - assign score of 0
                error_msg = f"Rendering error: {str(render_error)}"
                rating = 0.0
                print(f"  ✗ {error_msg} → Score: 0.0")
                total_score += rating
                successful += 1
                results.append({
                    "description": description,
                    "filename": filename,
                    "prompt": full_prompt,
                    "generated_code": generated_code,
                    "rating": rating,
                    "qwen3vl_rating": 0.0,
                    "error": error_msg
                })
                continue
            
            # Evaluate with Qwen3VL
            print("  Evaluating with Qwen3VL...")
            with open(screenshot_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            eval_prompt = create_evaluation_prompt(description)
            response = requests.post(
                "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate",
                json={"image": {"image_base64": base64_image}, "prompt": eval_prompt},
                timeout=120
            )
            response.raise_for_status()
            
            annotation = response.json().get("annotation", "")
            rating = extract_rating(annotation)
            
            print(f"\n📊 Qwen3VL Evaluation:")
            print(f"{'-'*60}")
            print(f"Analysis: {annotation}")
            print(f"{'-'*60}")
            
            if rating is not None:
                total_score += rating
                successful += 1
                print(f"\n✓ Qwen3VL Rating: {rating:.3f}")
            else:
                # If we can't extract rating, check if there was an error in the response
                error_msg = "Failed to extract rating from Qwen3VL response"
                rating = 0.0
                print(f"\n✗ {error_msg} → Score: 0.0")
                total_score += rating
                successful += 1
            
            results.append({
                "description": description,
                "filename": filename,
                "prompt": full_prompt,
                "generated_code": generated_code,
                "rating": rating,
                "qwen3vl_rating": rating,
                "qwen3vl_analysis": annotation,
                "error": error_msg
            })
            
        except requests.exceptions.RequestException as e:
            # API error - assign score of 0
            error_msg = f"Qwen3VL API error: {str(e)}"
            rating = 0.0
            print(f"  ✗ {error_msg} → Score: 0.0")
            total_score += rating
            successful += 1
            results.append({
                "description": description,
                "filename": filename,
                "prompt": full_prompt,
                "generated_code": generated_code if generated_code else None,
                "rating": rating,
                "qwen3vl_rating": 0.0,
                "error": error_msg
            })
            
        except Exception as e:
            # Other errors - assign score of 0
            error_msg = f"Unexpected error: {str(e)}"
            rating = 0.0
            print(f"  ✗ {error_msg} → Score: 0.0")
            total_score += rating
            successful += 1
            results.append({
                "description": description,
                "filename": filename,
                "prompt": full_prompt if 'full_prompt' in locals() else None,
                "generated_code": generated_code if 'generated_code' in locals() else None,
                "rating": rating,
                "qwen3vl_rating": 0.0,
                "error": error_msg
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Total examples tested: {len(test_data)}")
    print(f"Examples with scores: {successful}")
    print(f"\nSum of Qwen3VL ratings: {total_score:.3f}")
    print(f"Average Qwen3VL rating: {total_score/successful if successful > 0 else 0:.3f}")
    print(f"Number of examples tested: {successful}")
    
    # Count errors
    errors = [r for r in results if r.get("error")]
    if errors:
        print(f"\nExamples with errors (score = 0.0): {len(errors)}")
        for err in errors[:5]:  # Show first 5 errors
            print(f"  - {err.get('error', 'Unknown error')[:80]}")
    
    return {
        "total_examples": len(test_data),
        "successful": successful,
        "sum_of_ratings": total_score,
        "average_rating": total_score/successful if successful > 0 else 0,
        "num_tested": successful,
        "results": results
    }


@app.local_entrypoint()
def main(n: int = 20):
    """Entry point. Usage: modal run test_model_modal.py --n 20"""
    print(f"Testing with {n} examples...")
    result = test_model_on_modal.remote(n)
    print("\n" + "=" * 60)
    print("Final Results:")
    print(json.dumps(result, indent=2))
    print("=" * 60)

