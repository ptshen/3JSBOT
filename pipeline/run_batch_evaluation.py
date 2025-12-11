#!/usr/bin/env python3
"""
Batch evaluation script for Three.js code generation pipeline.

Features:
- Tiered execution scoring (0.0-1.0)
- Visual accuracy via direct Qwen-VL rating (default) or BERTScore (optional)
- Additive composite score: 0.7 * execution + 0.3 * visual
- Full output storage for paper appendix

Usage:
    python run_batch_evaluation.py --n 20
    python run_batch_evaluation.py --all --output-dir ./evaluation_outputs
    python run_batch_evaluation.py --n 20 --use-bertscore  # experimental
"""

import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from playwright.async_api import async_playwright

# Add pipeline directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from load_code import process_js_code

# Default API endpoints
DEFAULT_GEN_API = "https://patbshen--ollama-ollama-serve.modal.run/v1/chat/completions"
DEFAULT_EVAL_API = "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate"

# Try to import BERTScore (optional)
try:
    from bert_score import score as bert_score
    BERTSCORE_AVAILABLE = True
except ImportError:
    BERTSCORE_AVAILABLE = False


# =============================================================================
# Error Classification
# =============================================================================

ERROR_CATEGORIES = {
    "deprecated_api": [
        "BoxBufferGeometry is not a constructor",
        "PlaneBufferGeometry is not a constructor",
        "SphereBufferGeometry is not a constructor",
        "CylinderBufferGeometry is not a constructor",
    ],
    "undefined_variable": ["is not defined", "ReferenceError"],
    "null_reference": ["Cannot read properties of null", "Cannot read properties of undefined"],
    "type_error": ["is not a function", "is not a constructor", "TypeError"],
    "syntax_error": ["SyntaxError", "Unexpected token"],
    "module_error": ["Failed to resolve module", "Module not found"],
}


def classify_error(error_msg: str) -> Tuple[str, str]:
    """Classify a JS error into category and severity."""
    error_lower = error_msg.lower()
    for category, patterns in ERROR_CATEGORIES.items():
        for pattern in patterns:
            if pattern.lower() in error_lower:
                severity = "critical" if category in ["syntax_error", "module_error"] else "runtime"
                return category, severity
    return "unknown", "runtime"


def calculate_execution_score(js_errors: List[str], render_success: bool) -> Tuple[float, str]:
    """
    Calculate execution score based on errors and render success.
    
    Returns:
        Tuple of (score, status)
        - 0.0, "crashed": Complete failure
        - 0.25, "critical_errors": Syntax/module errors
        - 0.5, "runtime_errors": Runtime errors but rendered
        - 1.0, "clean": No errors
    """
    if not render_success:
        return 0.0, "crashed"
    
    if not js_errors:
        return 1.0, "clean"
    
    has_critical = any(classify_error(e)[1] == "critical" for e in js_errors)
    return (0.25, "critical_errors") if has_critical else (0.5, "runtime_errors")


# =============================================================================
# Code Generation
# =============================================================================

def extract_code_from_markdown(content: str) -> str:
    """Extract JavaScript code from markdown code blocks."""
    pattern = r'```(?:javascript|js)?\s*\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else content.strip()


def generate_code_via_api(prompt: str, api_url: str, model: str = "codellama:7b") -> Tuple[str, bool, str]:
    """Generate Three.js code using the API."""
    full_prompt = f"""Generate Three.js code for the following scene description:

{prompt}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting

Return only the JavaScript code without any explanations."""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "stream": False
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            return extract_code_from_markdown(content), True, ""
        return "", False, "No choices in API response"
    except Exception as e:
        return "", False, str(e)


# =============================================================================
# Visual Accuracy Evaluation
# =============================================================================

def get_image_caption(screenshot_path: str, api_url: str) -> Tuple[str, bool]:
    """
    Get Qwen-VL to caption/describe the screenshot.
    
    Uses the SAME prompt as the original data generation (screenshot_to_prompt.py)
    for consistent BERTScore comparison.
    
    Returns:
        Tuple of (caption_text, success)
    """
    try:
        with open(screenshot_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        # IMPORTANT: This prompt matches the original prompt used in 
        # image_to_prompt/screenshot_to_prompt.py for generating training descriptions.
        # Using the same prompt ensures BERTScore comparison is meaningful.
        prompt = "You are a world class 3D artist. Given this screenshot of three.js generated output, write a detailed description of the scene."

        response = requests.post(
            api_url,
            json={"image": {"image_base64": base64_image}, "prompt": prompt},
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if "annotation" in result:
            return result["annotation"], True
        return "", False
    except Exception as e:
        return f"Error: {e}", False


def calculate_bertscore(caption: str, reference: str) -> float:
    """
    Calculate BERTScore between caption and reference description.
    
    Returns:
        F1 score (0.0-1.0)
    """
    if not BERTSCORE_AVAILABLE:
        return 0.0
    
    try:
        # BERTScore returns (Precision, Recall, F1)
        P, R, F1 = bert_score([caption], [reference], lang="en", verbose=False)
        return float(F1[0])
    except Exception as e:
        print(f"    ⚠️  BERTScore error: {e}")
        return 0.0


def get_direct_rating(screenshot_path: str, reference: str, api_url: str) -> Tuple[float, str]:
    """
    Get direct rating from Qwen-VL with lenient partial-credit scoring.
    
    Returns:
        Tuple of (rating, analysis)
    """
    try:
        with open(screenshot_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = f"""Rate how well this 3D rendered image captures elements from the description.

DESCRIPTION:
{reference[:500]}

SCORING GUIDE (give partial credit):
- 0.0: Completely black/empty, or no recognizable 3D content
- 0.2: Has some 3D shapes but wrong type/color
- 0.4: Has correct basic shapes (spheres, cubes, etc.) but wrong arrangement
- 0.6: Correct shapes AND colors, but missing environment/lighting details
- 0.8: Good match - main objects correct with some lighting/composition
- 1.0: Excellent match - objects, colors, arrangement, and lighting all match

Focus on: Are the RIGHT TYPES of shapes present? Are colors approximately correct?
Ignore: Complex environments, exact positioning, advanced lighting effects.

Respond with ONLY a number between 0.0 and 1.0."""

        response = requests.post(
            api_url,
            json={"image": {"image_base64": base64_image}, "prompt": prompt},
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if "annotation" in result:
            text = result["annotation"]
            # Extract number
            match = re.search(r'([0-9]*\.?[0-9]+)', text)
            if match:
                rating = float(match.group(1))
                return max(0.0, min(1.0, rating)), text
        return 0.0, "Could not extract rating"
    except Exception as e:
        return 0.0, f"Error: {e}"


# =============================================================================
# Rendering with Error Capture
# =============================================================================

class RenderResult:
    """Result of rendering attempt."""
    def __init__(self):
        self.success = False
        self.screenshot_path = None
        self.js_errors: List[str] = []
        self.console_logs: List[str] = []
        self.error_message = None
        self.execution_score = 0.0
        self.execution_status = "crashed"
        self.error_categories: Dict[str, int] = {}


async def render_with_error_capture(
    js_code: str,
    output_path: str,
    project_dir: str,
    browser,
    server_url: str
) -> RenderResult:
    """Render Three.js code and capture all errors."""
    result = RenderResult()
    
    try:
        processed_js = process_js_code(js_code)
        
        import json as json_module
        import_map = {"imports": {"three": "../build/three.module.js", "three/addons/": "./jsm/"}}
        
        html_content = f"""<!DOCTYPE html>
<html><head>
    <meta charset="UTF-8">
    <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #000; }}
        canvas {{ display: block; width: 100vw; height: 100vh; }}
    </style>
    <script type="importmap">{json_module.dumps(import_map)}</script>
    <script type="module">
        import * as THREE from 'three';
        window.THREE = THREE;
        {processed_js}
    </script>
</head><body><div id="container"></div></body></html>"""
        
        html_path = os.path.join(project_dir, "index.html")
        with open(html_path, "w") as f:
            f.write(html_content)
        
        page = await browser.new_page()
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        
        def on_error(err):
            error_str = str(err)
            result.js_errors.append(error_str)
            category, _ = classify_error(error_str)
            result.error_categories[category] = result.error_categories.get(category, 0) + 1
        
        page.on('pageerror', on_error)
        
        html_url = f"{server_url}/project/index.html"
        try:
            await page.goto(html_url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            result.error_message = f"Page load failed: {e}"
            await page.close()
            return result
        
        try:
            await page.wait_for_function(
                '() => typeof THREE !== "undefined"',
                timeout=10000
            )
        except:
            result.error_message = "Three.js failed to load"
            await page.close()
            return result
        
        try:
            await page.wait_for_function('''
                () => {
                    const c = document.querySelector('canvas');
                    return c && c.width > 0 && c.height > 0;
                }
            ''', timeout=10000)
        except:
            result.error_message = "Canvas not ready"
            await page.close()
            return result
        
        # Wait for render
        await asyncio.sleep(2.0)
        
        canvas = await page.query_selector('canvas')
        if canvas:
            await canvas.screenshot(path=output_path, type='jpeg', quality=90)
        else:
            await page.screenshot(path=output_path, type='jpeg', quality=90)
        
        result.success = True
        result.screenshot_path = output_path
        await page.close()
        
    except Exception as e:
        result.error_message = str(e)
    
    result.execution_score, result.execution_status = calculate_execution_score(
        result.js_errors, result.success
    )
    return result


# =============================================================================
# Asset Management
# =============================================================================

def setup_project_structure(output_dir: str, pipeline_dir: str) -> Tuple[str, str]:
    """Set up project structure with assets copied ONCE."""
    project_dir = os.path.join(output_dir, "render_workspace", "project")
    build_parent_dir = os.path.join(output_dir, "render_workspace")
    
    os.makedirs(project_dir, exist_ok=True)
    
    # Copy build directory
    build_src = os.path.join(pipeline_dir, "build")
    build_dst = os.path.join(build_parent_dir, "build")
    if os.path.exists(build_src) and not os.path.exists(build_dst):
        print(f"  Copying build directory...")
        shutil.copytree(build_src, build_dst)
    
    # Copy other assets
    for asset_dir in ["jsm", "textures", "models", "sounds", "fonts", "files", "luts", "ies", "materialx"]:
        src = os.path.join(pipeline_dir, asset_dir)
        dst = os.path.join(project_dir, asset_dir)
        if os.path.exists(src) and not os.path.exists(dst):
            print(f"  Copying {asset_dir} directory...")
            shutil.copytree(src, dst)
    
    return project_dir, build_parent_dir


# =============================================================================
# Main Evaluation
# =============================================================================

async def run_batch_evaluation(
    data_file: str,
    n: Optional[int],
    use_validation: bool,
    gen_api_url: str,
    eval_api_url: str,
    model: str,
    output_dir: str,
    use_bertscore: bool
) -> Dict:
    """Run batch evaluation."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(output_dir, f"run_{timestamp}")
    examples_dir = os.path.join(run_dir, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    
    print("=" * 70)
    print("THREE.JS BATCH EVALUATION")
    print("=" * 70)
    print(f"\nOutput: {run_dir}")
    print(f"Model: {model}")
    if use_bertscore and not BERTSCORE_AVAILABLE:
        print("Warning: --use-bertscore requested but bert-score not installed.")
        print("  Install with: pip install bert-score")
        print("  Falling back to direct Qwen rating.\n")
        use_bertscore = False
    
    print(f"Visual accuracy method: {'BERTScore (experimental)' if use_bertscore else 'Direct Qwen rating'}")
    print(f"Scoring: 0.7 × Execution + 0.3 × Visual (additive)")
    
    # Load data
    print(f"\nLoading data...")
    with open(data_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    split_idx = int(len(all_data) * 0.8)
    eval_data = all_data[split_idx:] if use_validation else all_data[:split_idx]
    print(f"Using {'validation' if use_validation else 'training'} set: {len(eval_data)} examples")
    
    if n is not None and n < len(eval_data):
        eval_data = eval_data[:n]
        print(f"Limited to {n} examples")
    
    # Setup
    print(f"\nSetting up (copying assets once)...")
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir, build_parent_dir = setup_project_structure(run_dir, pipeline_dir)
    
    # Start server
    print(f"\nStarting HTTP server...")
    import http.server, socketserver, threading, socket
    os.chdir(build_parent_dir)
    
    for port in range(8000, 8100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                break
        except OSError:
            continue
    
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    server_url = f"http://localhost:{port}"
    print(f"Server: {server_url}")
    
    # Start browser
    print(f"\nStarting browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    
    print(f"\nEvaluating {len(eval_data)} examples...")
    print("-" * 70)
    
    start_time = time.time()
    results = []
    total_errors_by_category = {}
    
    for i, example in enumerate(eval_data):
        description = example.get('description', '')
        if not description:
            continue
        
        example_dir = os.path.join(examples_dir, f"{i:03d}")
        os.makedirs(example_dir, exist_ok=True)
        
        print(f"\n[{i + 1}/{len(eval_data)}] Evaluating...")
        print(f"    Desc: {description[:50]}...")
        
        result = {
            "idx": i,
            "description": description,
            "execution_score": 0.0,
            "execution_status": "crashed",
            "visual_accuracy": 0.0,
            "final_score": 0.0,
            "js_errors": [],
            "caption": None,
            "error": None,
        }
        
        # Save description
        with open(os.path.join(example_dir, "description.txt"), "w") as f:
            f.write(description)
        
        # Step 1: Generate code
        print("    → Generating code...")
        code, gen_success, gen_error = generate_code_via_api(description, gen_api_url, model)
        
        if not gen_success:
            result["error"] = f"Code gen failed: {gen_error}"
            print(f"    ✗ Code generation failed")
            results.append(result)
            continue
        
        with open(os.path.join(example_dir, "generated_code.js"), "w") as f:
            f.write(code)
        
        # Step 2: Render
        print("    → Rendering...")
        screenshot_path = os.path.join(example_dir, "screenshot.jpg")
        render_result = await render_with_error_capture(code, screenshot_path, project_dir, browser, server_url)
        
        result["execution_score"] = render_result.execution_score
        result["execution_status"] = render_result.execution_status
        result["js_errors"] = render_result.js_errors
        
        for cat, count in render_result.error_categories.items():
            total_errors_by_category[cat] = total_errors_by_category.get(cat, 0) + count
        
        if render_result.js_errors:
            print(f"    ⚠️  {len(render_result.js_errors)} JS error(s)")
        
        if not render_result.success:
            result["error"] = render_result.error_message
            print(f"    ✗ Render failed")
            # Still calculate final score (execution only)
            result["final_score"] = 0.7 * result["execution_score"]
            results.append(result)
            continue
        
        print(f"    ✓ Rendered (exec: {render_result.execution_status}, score: {render_result.execution_score})")
        
        # Step 3: Visual accuracy
        print("    → Evaluating visual accuracy...")
        
        if use_bertscore:
            # BERTScore method: caption + semantic similarity
            caption, cap_success = get_image_caption(screenshot_path, eval_api_url)
            result["caption"] = caption
            
            if cap_success and caption:
                # Use a simplified version of description for comparison
                ref_text = description[:1000]  # Truncate for efficiency
                visual_score = calculate_bertscore(caption, ref_text)
                result["visual_accuracy"] = visual_score
                print(f"    ✓ BERTScore: {visual_score:.3f}")
            else:
                print(f"    ⚠️  Caption failed")
        else:
            # Direct rating method
            rating, analysis = get_direct_rating(screenshot_path, description, eval_api_url)
            result["visual_accuracy"] = rating
            result["caption"] = analysis
            print(f"    ✓ Direct rating: {rating:.3f}")
        
        # Calculate final composite score (ADDITIVE: 70% execution + 30% visual)
        result["final_score"] = 0.7 * result["execution_score"] + 0.3 * result["visual_accuracy"]
        print(f"    ★ Final: {result['final_score']:.3f} = 0.7×{result['execution_score']:.1f} + 0.3×{result['visual_accuracy']:.3f}")
        
        # Save evaluation
        with open(os.path.join(example_dir, "evaluation.json"), "w") as f:
            json.dump(result, f, indent=2)
        
        results.append(result)
    
    elapsed = time.time() - start_time
    
    # Cleanup
    await browser.close()
    await playwright.stop()
    httpd.shutdown()
    
    # Calculate metrics
    total = len(results)
    
    exec_scores = [r["execution_score"] for r in results]
    visual_scores = [r["visual_accuracy"] for r in results]
    final_scores = [r["final_score"] for r in results]
    
    status_counts = {}
    for r in results:
        s = r["execution_status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    
    avg_exec = sum(exec_scores) / total if total else 0
    avg_visual = sum(visual_scores) / total if total else 0
    avg_final = sum(final_scores) / total if total else 0
    
    # Summary
    summary = {
        "metadata": {
            "timestamp": timestamp,
            "model": model,
            "total_examples": total,
            "elapsed_seconds": elapsed,
            "visual_method": "bertscore" if use_bertscore else "direct_rating",
            "scoring_formula": "0.7 * execution + 0.3 * visual",
        },
        "metrics": {
            "avg_execution_score": avg_exec,
            "avg_visual_accuracy": avg_visual,
            "avg_final_score": avg_final,
            "execution_breakdown": status_counts,
            "error_categories": total_errors_by_category,
        },
        "results": results,
    }
    
    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nTime: {elapsed:.1f}s ({elapsed/total:.1f}s/example)")
    
    print("\nEXECUTION BREAKDOWN:")
    for status in ["clean", "runtime_errors", "critical_errors", "crashed"]:
        count = status_counts.get(status, 0)
        pct = count/total*100 if total else 0
        score = {"clean": 1.0, "runtime_errors": 0.5, "critical_errors": 0.25, "crashed": 0.0}[status]
        print(f"  {status:20s}: {count:3d} ({pct:5.1f}%) [score={score}]")
    
    print(f"\nAVERAGE SCORES:")
    print(f"  Execution:      {avg_exec:.3f}")
    print(f"  Visual:         {avg_visual:.3f}")
    print(f"  ─────────────────────")
    print(f"  FINAL SCORE:    {avg_final:.3f}")
    print(f"  (0.7×{avg_exec:.3f} + 0.3×{avg_visual:.3f})")
    
    if total_errors_by_category:
        print(f"\nERROR CATEGORIES:")
        for cat, count in sorted(total_errors_by_category.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")
    
    # Save
    with open(os.path.join(run_dir, "results.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    # Markdown summary
    md = f"""# Evaluation Results

**Model:** {model}  
**Examples:** {total}  
**Time:** {elapsed:.1f}s  
**Visual Method:** {'BERTScore' if use_bertscore else 'Direct Qwen Rating'}

## Scores

| Metric | Value |
|--------|-------|
| Execution | {avg_exec:.3f} |
| Visual | {avg_visual:.3f} |
| **Final** | **{avg_final:.3f}** |

## Execution Breakdown

| Status | Count | % | Score |
|--------|-------|---|-------|
| Clean | {status_counts.get('clean', 0)} | {status_counts.get('clean', 0)/total*100:.1f}% | 1.0 |
| Runtime Errors | {status_counts.get('runtime_errors', 0)} | {status_counts.get('runtime_errors', 0)/total*100:.1f}% | 0.5 |
| Critical Errors | {status_counts.get('critical_errors', 0)} | {status_counts.get('critical_errors', 0)/total*100:.1f}% | 0.25 |
| Crashed | {status_counts.get('crashed', 0)} | {status_counts.get('crashed', 0)/total*100:.1f}% | 0.0 |

## Formula

```
Final Score = 0.7 × Execution Score + 0.3 × Visual Accuracy
            = 0.7 × {avg_exec:.3f} + 0.3 × {avg_visual:.3f}
            = {avg_final:.3f}
```
"""
    
    with open(os.path.join(run_dir, "summary.md"), "w") as f:
        f.write(md)
    
    print(f"\n✓ Results saved to: {run_dir}/")
    print("=" * 70)
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Batch evaluation for Three.js code generation")
    parser.add_argument("--n", type=int, default=None, help="Number of examples")
    parser.add_argument("--all", action="store_true", help="Evaluate all")
    parser.add_argument("--data", type=str, 
                        default=os.path.join(os.path.dirname(__file__), "..", "training", "training_data.json"))
    parser.add_argument("--use-training-set", action="store_true")
    parser.add_argument("--gen-api", type=str, default=DEFAULT_GEN_API)
    parser.add_argument("--eval-api", type=str, default=DEFAULT_EVAL_API)
    parser.add_argument("--model", type=str, default="codellama:7b")
    parser.add_argument("--output-dir", type=str, 
                        default=os.path.join(os.path.dirname(__file__), "..", "evaluation_outputs"))
    parser.add_argument("--use-bertscore", action="store_true", help="Use BERTScore instead of direct Qwen rating (experimental)")
    
    args = parser.parse_args()
    
    n = None if args.all else (args.n or 10)
    use_bertscore = args.use_bertscore
    
    asyncio.run(run_batch_evaluation(
        data_file=args.data,
        n=n,
        use_validation=not args.use_training_set,
        gen_api_url=args.gen_api,
        eval_api_url=args.eval_api,
        model=args.model,
        output_dir=args.output_dir,
        use_bertscore=use_bertscore
    ))


if __name__ == "__main__":
    main()
