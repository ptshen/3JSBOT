#!/usr/bin/env python3
"""
Complete pipeline for Three.js code generation, rendering, and evaluation.

Flow:
1. Takes user prompt as argument
2. Generates Three.js code using generate_code.py
3. Renders the code and captures screenshot using load_code.py
4. Evaluates the screenshot against the original prompt using eval_screenshot.py
"""

import sys
import os
import subprocess
import json

# Add the pipeline directory to the path so we can import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

import requests
import base64

# Import functions from other pipeline modules
from generate_code import generate_threejs_code
from load_code import render_threejs, read_js_from_file

# Import eval functions - need to define them here since eval_screenshot.py is a script
def extract_rating(text: str) -> float:
    """Extract a 0-1 rating from the model's response."""
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

Be precise and objective in your evaluation."""


def run_pipeline(prompt: str, gen_code_file: str = "gen_code.js", screenshot_file: str = "screenshot.jpg") -> dict:
    """
    Run the complete pipeline: generate code, render, and evaluate.
    
    Args:
        prompt: The user prompt describing the Three.js scene to generate
        gen_code_file: Path to save the generated JavaScript code (default: "gen_code.js")
        screenshot_file: Path to save the screenshot (default: "screenshot.jpg")
    
    Returns:
        Dictionary containing the pipeline results including rating and analysis
    """
    results = {
        "prompt": prompt,
        "gen_code_file": gen_code_file,
        "screenshot_file": screenshot_file,
        "rating": None,
        "analysis": None,
        "errors": []
    }
    
    print("=" * 60)
    print("THREE.JS PIPELINE")
    print("=" * 60)
    print(f"Prompt: {prompt}\n")
    
    # Step 1: Generate Three.js code
    print("Step 1: Generating Three.js code...")
    print("-" * 60)
    print("INPUT PROMPT:")
    print(prompt)
    print("\n" + "-" * 60)
    try:
        generated_code = generate_threejs_code(prompt, gen_code_file)
        print(f"\n✓ Code generated and saved to {gen_code_file}")
        print("\nGENERATED CODE OUTPUT:")
        print("=" * 60)
        print(generated_code)
        print("=" * 60)
        print()
    except Exception as e:
        error_msg = f"Error generating code: {e}"
        print(f"✗ {error_msg}")
        results["errors"].append(error_msg)
        return results
    
    # Step 2: Render the code and capture screenshot
    print("Step 2: Rendering Three.js scene and capturing screenshot...")
    print("-" * 60)
    try:
        # Read the generated code
        js_code = read_js_from_file(gen_code_file)
        print("INPUT CODE (being rendered):")
        print("=" * 60)
        print(js_code)
        print("=" * 60)
        print()
        
        # Render and save screenshot
        script_dir = os.path.dirname(os.path.abspath(__file__))
        screenshot_path = os.path.join(script_dir, screenshot_file)
        
        print(f"Rendering scene and saving to: {screenshot_path}")
        render_threejs(js_code, output_path=screenshot_path, keep_server_running=False)
        print(f"\n✓ Screenshot saved to {screenshot_path}")
        print(f"OUTPUT: Screenshot file created at {screenshot_path}\n")
    except Exception as e:
        error_msg = f"Error rendering scene: {e}"
        print(f"✗ {error_msg}")
        results["errors"].append(error_msg)
        return results
    
    # Step 3: Evaluate the screenshot against the original prompt
    print("Step 3: Evaluating screenshot against reference description...")
    print("-" * 60)
    try:
        # Read and encode the screenshot
        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")
        
        print(f"INPUT SCREENSHOT: {screenshot_path}")
        print(f"INPUT REFERENCE DESCRIPTION: {prompt}")
        print()
        
        with open(screenshot_path, "rb") as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Create evaluation prompt using the original user prompt as reference
        eval_prompt = create_evaluation_prompt(prompt)
        
        print("EVALUATION PROMPT SENT TO API:")
        print("=" * 60)
        print(eval_prompt)
        print("=" * 60)
        print()
        
        # Send request to evaluation API
        print("Sending request to evaluation API...")
        response = requests.post(
            "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate",
            json={
                "image": {"image_base64": base64_image},
                "prompt": eval_prompt
            },
            timeout=120
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        
        if "annotation" in result:
            annotation = result["annotation"]
            rating = extract_rating(annotation)
            
            results["rating"] = rating
            results["analysis"] = annotation
            
            print("EVALUATION OUTPUT:")
            print("=" * 60)
            if rating is not None:
                print(f"Rating: {rating:.2f}/1.0")
            else:
                print("Rating: Could not be extracted")
            print("\nFull Analysis:")
            print(annotation)
            print("=" * 60)
            print()
        else:
            raise ValueError("Unexpected response format from evaluation API")
        
    except Exception as e:
        error_msg = f"Error evaluating screenshot: {e}"
        print(f"✗ {error_msg}")
        results["errors"].append(error_msg)
        return results
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    
    return results


def main():
    """Main entry point for the pipeline."""
    if len(sys.argv) < 2:
        print("Usage: python3 run_pipeline.py <prompt>")
        print("\nExample:")
        print('  python3 run_pipeline.py "Create a 3D house with four walls, a floor, and a roof"')
        print("\nThe pipeline will:")
        print("  1. Generate Three.js code from the prompt")
        print("  2. Render the scene and save screenshot.jpg")
        print("  3. Evaluate how well the screenshot matches the prompt")
        sys.exit(1)
    
    # Join all arguments after the script name to allow prompts with spaces
    prompt = " ".join(sys.argv[1:])
    
    # Run the pipeline
    results = run_pipeline(prompt)
    
    # Print final results summary
    if results["rating"] is not None:
        print(f"\nFinal Rating: {results['rating']:.2f}/1.0")
        if results["rating"] >= 0.8:
            print("Status: ✓ Excellent match!")
        elif results["rating"] >= 0.6:
            print("Status: ✓ Good match")
        elif results["rating"] >= 0.4:
            print("Status: ⚠ Moderate match")
        else:
            print("Status: ✗ Poor match")
    
    # Save results to JSON file
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    # Exit with error code if there were errors
    if results["errors"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

