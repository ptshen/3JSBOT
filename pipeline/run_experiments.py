#!/usr/bin/env python3
"""
Experiment runner for comparing different prompt strategies.

Tests:
1. Baseline (zero-shot)
2. Improved system prompt
3. Few-shot examples
4. All combined
5. Chain-of-Thought
6. Plan-then-Code
7. Self-Refinement
8. Combined variants of above

Usage:
    python run_experiments.py --n 20
    python run_experiments.py --n 50 --experiment improved_prompt
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

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from load_code import process_js_code

# API endpoints
GEN_API = "https://patbshen--ollama-ollama-serve.modal.run/v1/chat/completions"
EVAL_API = "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate"

# =============================================================================
# PROMPT CONFIGURATIONS
# =============================================================================

# Baseline: Simple prompt (current)
BASELINE_SYSTEM = ""
BASELINE_USER = """Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting

Return only the JavaScript code without any explanations."""

# Improved: Better system prompt with Three.js best practices
IMPROVED_SYSTEM = """You are an expert Three.js developer. Generate clean, working Three.js code.

CRITICAL Three.js Rules:
1. Use modern Three.js (r150+): Use BoxGeometry, SphereGeometry, PlaneGeometry (NOT BufferGeometry variants)
2. ALWAYS add lighting for MeshStandardMaterial/MeshPhongMaterial to be visible:
   - Add AmbientLight for base illumination
   - Add DirectionalLight or PointLight for shadows/highlights
3. Position camera to see the scene (camera.position.z = 5 or similar)
4. Call renderer.render(scene, camera) at the end
5. Append renderer.domElement to document.body

Common mistakes to AVOID:
- BoxBufferGeometry (deprecated) → use BoxGeometry
- SphereBufferGeometry (deprecated) → use SphereGeometry  
- Missing lights (causes black objects)
- Camera too close or facing wrong direction"""

IMPROVED_USER = """Create a Three.js scene for:

{description}

Output ONLY valid JavaScript code. No explanations."""

# Few-shot: Include working examples
FEWSHOT_SYSTEM = """You are an expert Three.js developer. Here are examples of working Three.js code:

EXAMPLE 1 - Red cube with lighting:
```javascript
import * as THREE from 'three';
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.z = 5;
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Lighting (REQUIRED for materials to be visible)
const ambientLight = new THREE.AmbientLight(0x404040);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(5, 5, 5);
scene.add(directionalLight);

// Red cube
const geometry = new THREE.BoxGeometry(1, 1, 1);
const material = new THREE.MeshStandardMaterial({ color: 0xff0000 });
const cube = new THREE.Mesh(geometry, material);
scene.add(cube);

renderer.render(scene, camera);
```

EXAMPLE 2 - Multiple colored spheres:
```javascript
import * as THREE from 'three';
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.z = 10;
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0x404040));
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(10, 10, 10);
scene.add(light);

const colors = [0xff0000, 0x00ff00, 0x0000ff, 0xffff00];
colors.forEach((color, i) => {
    const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.5, 32, 32),
        new THREE.MeshStandardMaterial({ color })
    );
    sphere.position.x = (i - 1.5) * 2;
    scene.add(sphere);
});

renderer.render(scene, camera);
```

Follow these patterns exactly. Use modern Three.js APIs (BoxGeometry not BoxBufferGeometry)."""

FEWSHOT_USER = """Create a Three.js scene for:

{description}

Output ONLY valid JavaScript code matching the example patterns."""

# Combined: All improvements
COMBINED_SYSTEM = IMPROVED_SYSTEM + "\n\n" + FEWSHOT_SYSTEM.split("You are an expert")[1]
COMBINED_USER = FEWSHOT_USER

# Chain-of-Thought: Simple instructed CoT (baseline CoT)
COT_SYSTEM = """You are an expert Three.js developer. Before writing code, you MUST think step-by-step.

Use modern Three.js APIs (BoxGeometry not BoxBufferGeometry).
Always add lighting (AmbientLight + DirectionalLight) for materials to be visible."""

COT_USER = """Create a Three.js scene for:

{description}

Think step-by-step:
1. OBJECTS: List the main 3D objects needed (cubes, spheres, planes, etc.)
2. COLORS: What colors/materials should each object have?
3. POSITIONS: Where should objects be placed in 3D space?
4. LIGHTING: What lights are needed?
5. CAMERA: Where should the camera be positioned?

After your analysis, output the complete JavaScript code inside ```javascript``` tags."""

# Plan-then-Code: Two-stage structured generation (more rigorous CoT)
PLAN_SYSTEM = """You are a 3D scene planner. Analyze scene descriptions and output a structured JSON plan.
Do NOT write code. Only output a JSON plan."""

PLAN_USER = """Analyze this 3D scene description and create a structured plan:

{description}

Output a JSON plan with this EXACT structure:
```json
{{
  "scene_analysis": "Brief 1-sentence summary of the scene",
  "objects": [
    {{"type": "box|sphere|plane|cylinder|cone|torus", "color": "#hexcolor", "size": [w,h,d], "position": [x,y,z]}}
  ],
  "lights": [
    {{"type": "ambient|directional|point|spot", "color": "#hexcolor", "intensity": 0.0-2.0, "position": [x,y,z]}}
  ],
  "camera": {{"position": [x,y,z], "lookAt": [x,y,z]}},
  "background": "#hexcolor"
}}
```

Be specific with positions and colors. Output ONLY the JSON, nothing else."""

CODE_FROM_PLAN_SYSTEM = """You are a Three.js code generator. Convert JSON scene plans into working Three.js code.

CRITICAL RULES:
- Use modern APIs: BoxGeometry (NOT BoxBufferGeometry), SphereGeometry, etc.
- Always include lights from the plan
- Set camera position exactly as specified
- Output ONLY JavaScript code, no explanations"""

CODE_FROM_PLAN_USER = """Convert this scene plan to Three.js code:

{plan}

Output complete, working JavaScript code. Include:
- Scene, camera, renderer setup
- All objects from the plan with correct colors and positions
- All lights from the plan
- renderer.render(scene, camera) at the end

Output ONLY the code inside ```javascript``` tags."""

# Self-Refinement: Will be handled specially in code (iterative)
SELFREFINE_SYSTEM = IMPROVED_SYSTEM
SELFREFINE_USER = IMPROVED_USER

EXPERIMENTS = {
    "baseline": {
        "name": "Baseline (Zero-shot)",
        "system": BASELINE_SYSTEM,
        "user": BASELINE_USER,
        "temperature": 0.7,
    },
    "baseline_temp0": {
        "name": "Baseline + Temperature=0",
        "system": BASELINE_SYSTEM,
        "user": BASELINE_USER,
        "temperature": 0.0,
    },
    "improved_prompt": {
        "name": "Improved System Prompt",
        "system": IMPROVED_SYSTEM,
        "user": IMPROVED_USER,
        "temperature": 0.0,
    },
    "fewshot": {
        "name": "Few-shot Examples",
        "system": FEWSHOT_SYSTEM,
        "user": FEWSHOT_USER,
        "temperature": 0.0,
    },
    "combined": {
        "name": "Combined (All Improvements)",
        "system": COMBINED_SYSTEM,
        "user": COMBINED_USER,
        "temperature": 0.0,
    },
    "chain_of_thought": {
        "name": "Chain-of-Thought (Instructed)",
        "system": COT_SYSTEM,
        "user": COT_USER,
        "temperature": 0.0,
    },
    "cot_combined": {
        "name": "CoT + Improved Prompt + Few-shot",
        "system": COMBINED_SYSTEM + "\n\nBefore writing code, you MUST think step-by-step.",
        "user": COT_USER,
        "temperature": 0.0,
    },
    "plan_then_code": {
        "name": "Plan-then-Code (Two-stage)",
        "system": PLAN_SYSTEM,
        "user": PLAN_USER,
        "temperature": 0.0,
        "two_stage": True,
        "stage2_system": CODE_FROM_PLAN_SYSTEM,
        "stage2_user": CODE_FROM_PLAN_USER,
    },
    "plan_then_code_combined": {
        "name": "Plan-then-Code + Improved Prompt + Few-shot",
        "system": PLAN_SYSTEM + "\n\n" + IMPROVED_SYSTEM + "\n\n" + FEWSHOT_SYSTEM.split("You are an expert")[1],
        "user": PLAN_USER,
        "temperature": 0.0,
        "two_stage": True,
        "stage2_system": CODE_FROM_PLAN_SYSTEM + "\n\n" + IMPROVED_SYSTEM + "\n\n" + FEWSHOT_SYSTEM.split("You are an expert")[1],
        "stage2_user": CODE_FROM_PLAN_USER,
    },
    "stacked_all": {
        "name": "Stacked Plan+CoT+Few-shot+Self-Refine",
        "system": PLAN_SYSTEM + "\n\n" + IMPROVED_SYSTEM + "\n\n" + FEWSHOT_SYSTEM.split("You are an expert")[1],
        "user": PLAN_USER,
        "temperature": 0.0,
        "two_stage": True,
        "stage2_system": CODE_FROM_PLAN_SYSTEM
        + "\n\n"
        + IMPROVED_SYSTEM
        + "\n\n"
        + FEWSHOT_SYSTEM.split("You are an expert")[1]
        + "\n\nBefore writing code, you MUST think step-by-step.",
        "stage2_user": CODE_FROM_PLAN_USER,
        "max_iterations": 2,
    },
    "self_refine": {
        "name": "Self-Refinement (2 iterations)",
        "system": SELFREFINE_SYSTEM,
        "user": SELFREFINE_USER,
        "temperature": 0.0,
        "max_iterations": 2,
    },
    "self_refine_combined": {
        "name": "Self-Refinement + Improved Prompt + Few-shot",
        "system": COMBINED_SYSTEM,
        "user": SELFREFINE_USER,
        "temperature": 0.0,
        "max_iterations": 2,
    },
}

# =============================================================================
# Error Classification (same as run_batch_evaluation.py)
# =============================================================================

ERROR_CATEGORIES = {
    "deprecated_api": [
        "BoxBufferGeometry is not a constructor",
        "PlaneBufferGeometry is not a constructor",
        "SphereBufferGeometry is not a constructor",
    ],
    "undefined_variable": ["is not defined", "ReferenceError"],
    "null_reference": ["Cannot read properties of null"],
    "type_error": ["is not a function", "is not a constructor"],
    "syntax_error": ["SyntaxError", "Unexpected token"],
}


def classify_error(error_msg: str) -> Tuple[str, str]:
    error_lower = error_msg.lower()
    for category, patterns in ERROR_CATEGORIES.items():
        for pattern in patterns:
            if pattern.lower() in error_lower:
                severity = "critical" if category in ["syntax_error"] else "runtime"
                return category, severity
    return "unknown", "runtime"


def calculate_execution_score(js_errors: List[str], render_success: bool) -> Tuple[float, str]:
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
    pattern = r'```(?:javascript|js)?\s*\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else content.strip()


def generate_code(description: str, experiment: dict, model: str = "codellama:7b") -> Tuple[str, bool, str]:
    """Generate code using the specified experiment configuration."""
    
    messages = []
    if experiment["system"]:
        messages.append({"role": "system", "content": experiment["system"]})
    
    user_prompt = experiment["user"].format(description=description)
    messages.append({"role": "user", "content": user_prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": experiment["temperature"],
        "stream": False
    }
    
    try:
        response = requests.post(GEN_API, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            return extract_code_from_markdown(content), True, content  # Return full content for CoT
        return "", False, "No choices in API response"
    except Exception as e:
        return "", False, str(e)


def generate_plan_then_code(description: str, experiment: dict, model: str = "codellama:7b") -> Tuple[str, bool, str, str]:
    """Two-stage generation: Plan → Code.
    
    Returns: (code, success, error, plan)
    """
    # Stage 1: Generate plan
    messages = [
        {"role": "system", "content": experiment["system"]},
        {"role": "user", "content": experiment["user"].format(description=description)}
    ]
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "stream": False
    }
    
    try:
        response = requests.post(GEN_API, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        
        if "choices" not in data or len(data["choices"]) == 0:
            return "", False, "No plan generated", ""
        
        plan_response = data["choices"][0]["message"]["content"]
        
        # Extract JSON from response
        json_match = re.search(r'```json\s*(.*?)```', plan_response, re.DOTALL)
        if json_match:
            plan = json_match.group(1).strip()
        else:
            # Try to find raw JSON
            plan = plan_response.strip()
        
        # Stage 2: Generate code from plan
        messages2 = [
            {"role": "system", "content": experiment["stage2_system"]},
            {"role": "user", "content": experiment["stage2_user"].format(plan=plan)}
        ]
        
        payload2 = {
            "model": model,
            "messages": messages2,
            "temperature": 0.0,
            "stream": False
        }
        
        response2 = requests.post(GEN_API, json=payload2, timeout=180)
        response2.raise_for_status()
        data2 = response2.json()
        
        if "choices" in data2 and len(data2["choices"]) > 0:
            code_response = data2["choices"][0]["message"]["content"]
            code = extract_code_from_markdown(code_response)
            return code, True, "", plan
        
        return "", False, "No code generated from plan", plan
        
    except Exception as e:
        return "", False, str(e), ""


def refine_code(original_code: str, errors: List[str], experiment: dict, model: str = "codellama:7b") -> Tuple[str, bool, str]:
    """Refine code based on errors (self-refinement)."""
    
    error_summary = "\n".join(f"- {e[:200]}" for e in errors[:5])  # Limit errors
    
    refine_prompt = f"""Your previous Three.js code had these errors:

{error_summary}

Here is the problematic code:
```javascript
{original_code[:2000]}
```

Fix the errors. Common fixes:
- BoxBufferGeometry → BoxGeometry
- SphereBufferGeometry → SphereGeometry  
- Add AmbientLight and DirectionalLight if objects are black
- Define variables before using them

Output ONLY the corrected JavaScript code."""

    messages = []
    if experiment["system"]:
        messages.append({"role": "system", "content": experiment["system"]})
    messages.append({"role": "user", "content": refine_prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "stream": False
    }
    
    try:
        response = requests.post(GEN_API, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            return extract_code_from_markdown(content), True, ""
        return original_code, False, "No response"
    except Exception as e:
        return original_code, False, str(e)


# =============================================================================
# Visual Evaluation
# =============================================================================

def evaluate_visual(screenshot_path: str, description: str) -> Tuple[float, str]:
    """Get visual accuracy rating from Qwen."""
    try:
        with open(screenshot_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = f"""Rate how well this 3D rendered image captures elements from the description.

DESCRIPTION:
{description[:500]}

SCORING GUIDE (give partial credit):
- 0.0: Completely black/empty, or no recognizable 3D content
- 0.2: Has some 3D shapes but wrong type/color
- 0.4: Has correct basic shapes but wrong arrangement
- 0.6: Correct shapes AND colors, but missing details
- 0.8: Good match - main objects correct
- 1.0: Excellent match

Respond with ONLY a number between 0.0 and 1.0."""

        response = requests.post(
            EVAL_API,
            json={"image": {"image_base64": base64_image}, "prompt": prompt},
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if "annotation" in result:
            text = result["annotation"]
            match = re.search(r'([0-9]*\.?[0-9]+)', text)
            if match:
                rating = float(match.group(1))
                return max(0.0, min(1.0, rating)), text
        return 0.0, "Could not parse"
    except Exception as e:
        return 0.0, str(e)


# =============================================================================
# Rendering
# =============================================================================

async def render_code(
    js_code: str,
    output_path: str,
    project_dir: str,
    browser,
    server_url: str
) -> Tuple[bool, List[str]]:
    """Render code and capture errors."""
    js_errors = []
    
    try:
        processed_js = process_js_code(js_code)
        
        import json as json_module
        import_map = {"imports": {"three": "../build/three.module.js", "three/addons/": "./jsm/"}}
        
        html = f"""<!DOCTYPE html>
<html><head>
    <meta charset="UTF-8">
    <style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#000}}canvas{{display:block;width:100vw;height:100vh}}</style>
    <script type="importmap">{json_module.dumps(import_map)}</script>
    <script type="module">
        import * as THREE from 'three';
        window.THREE = THREE;
        {processed_js}
    </script>
</head><body></body></html>"""
        
        with open(os.path.join(project_dir, "index.html"), "w") as f:
            f.write(html)
        
        page = await browser.new_page()
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        page.on('pageerror', lambda err: js_errors.append(str(err)))
        
        try:
            await page.goto(f"{server_url}/project/index.html", wait_until='networkidle', timeout=30000)
            await page.wait_for_function('() => typeof THREE !== "undefined"', timeout=10000)
            await asyncio.sleep(2.0)
            
            canvas = await page.query_selector('canvas')
            if canvas:
                await canvas.screenshot(path=output_path, type='jpeg', quality=90)
            else:
                await page.screenshot(path=output_path, type='jpeg', quality=90)
            
            await page.close()
            return True, js_errors
        except Exception as e:
            await page.close()
            return False, js_errors + [str(e)]
    except Exception as e:
        return False, [str(e)]


# =============================================================================
# Main Experiment Runner
# =============================================================================

async def run_experiment(
    experiment_id: str,
    data: List[dict],
    n: int,
    output_dir: str,
    project_dir: str,
    browser,
    server_url: str
) -> dict:
    """Run a single experiment configuration."""
    
    experiment = EXPERIMENTS[experiment_id]
    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {experiment['name']}")
    print(f"{'='*60}")
    print(f"Temperature: {experiment['temperature']}")
    print(f"System prompt: {'Yes' if experiment['system'] else 'No'}")
    
    exp_dir = os.path.join(output_dir, experiment_id)
    os.makedirs(exp_dir, exist_ok=True)
    
    results = []
    start_time = time.time()
    
    for i, example in enumerate(data[:n]):
        description = example.get('description', '')
        if not description:
            continue
        
        print(f"\n[{i+1}/{n}] ", end="", flush=True)
        
        result = {
            "idx": i,
            "execution_score": 0.0,
            "execution_status": "crashed",
            "visual_accuracy": 0.0,
            "final_score": 0.0,
            "js_errors": [],
        }
        
        # Generate (either single-stage or two-stage)
        plan = None
        if experiment.get("two_stage"):
            code, gen_ok, gen_err, plan = generate_plan_then_code(description, experiment)
            if plan:
                with open(os.path.join(exp_dir, f"{i:03d}_plan.json"), "w") as f:
                    f.write(plan)
        else:
            code, gen_ok, gen_response = generate_code(description, experiment)
        
        if not gen_ok:
            print(f"✗ Gen failed: {gen_response if isinstance(gen_response, str) else 'Unknown error'}")
            results.append(result)
            continue
        
        # Save code
        with open(os.path.join(exp_dir, f"{i:03d}_code.js"), "w") as f:
            f.write(code)
        
        # Render
        screenshot_path = os.path.join(exp_dir, f"{i:03d}_screenshot.jpg")
        render_ok, js_errors = await render_code(code, screenshot_path, project_dir, browser, server_url)
        
        # Self-refinement loop (if enabled)
        max_iters = experiment.get("max_iterations", 1)
        iteration = 1
        while js_errors and iteration < max_iters and render_ok:
            iteration += 1
            print(f"↻", end="", flush=True)  # Show refinement happening
            
            refined_code, refine_ok, _ = refine_code(code, js_errors, experiment)
            if refine_ok and refined_code != code:
                code = refined_code
                # Save refined code
                with open(os.path.join(exp_dir, f"{i:03d}_code_v{iteration}.js"), "w") as f:
                    f.write(code)
                # Re-render
                render_ok, js_errors = await render_code(code, screenshot_path, project_dir, browser, server_url)
        
        result["js_errors"] = js_errors
        result["iterations"] = iteration
        result["execution_score"], result["execution_status"] = calculate_execution_score(js_errors, render_ok)
        
        if not render_ok:
            print(f"✗ Render failed")
            result["final_score"] = 0.7 * result["execution_score"]
            results.append(result)
            continue
        
        # Evaluate
        visual_score, _ = evaluate_visual(screenshot_path, description)
        result["visual_accuracy"] = visual_score
        result["final_score"] = 0.7 * result["execution_score"] + 0.3 * visual_score
        
        status_icon = {"clean": "✓", "runtime_errors": "⚠", "critical_errors": "⚠", "crashed": "✗"}
        print(f"{status_icon.get(result['execution_status'], '?')} exec={result['execution_score']:.1f} vis={visual_score:.2f} final={result['final_score']:.3f}")
        
        results.append(result)
    
    elapsed = time.time() - start_time
    
    # Calculate metrics
    exec_scores = [r["execution_score"] for r in results]
    visual_scores = [r["visual_accuracy"] for r in results]
    final_scores = [r["final_score"] for r in results]
    
    status_counts = {}
    for r in results:
        s = r["execution_status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    
    summary = {
        "experiment": experiment_id,
        "name": experiment["name"],
        "n_examples": len(results),
        "elapsed_seconds": elapsed,
        "avg_execution": sum(exec_scores) / len(exec_scores) if exec_scores else 0,
        "avg_visual": sum(visual_scores) / len(visual_scores) if visual_scores else 0,
        "avg_final": sum(final_scores) / len(final_scores) if final_scores else 0,
        "execution_breakdown": status_counts,
        "results": results,
    }
    
    # Save
    with open(os.path.join(exp_dir, "results.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n--- {experiment['name']} ---")
    print(f"Execution: {summary['avg_execution']:.3f}")
    print(f"Visual:    {summary['avg_visual']:.3f}")
    print(f"FINAL:     {summary['avg_final']:.3f}")
    
    return summary


async def main_async(args):
    """Main async entry point."""
    
    # Load data
    with open(args.data, 'r') as f:
        all_data = json.load(f)
    
    split_idx = int(len(all_data) * 0.8)
    eval_data = all_data[split_idx:]
    print(f"Loaded {len(eval_data)} validation examples")
    
    # Setup output - include experiment type in folder name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    experiment_name = args.experiment if args.experiment else "all"
    output_dir = os.path.join(args.output_dir, f"experiments_{experiment_name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup project structure
    project_dir = os.path.join(output_dir, "workspace", "project")
    build_parent = os.path.join(output_dir, "workspace")
    os.makedirs(project_dir, exist_ok=True)
    
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Copying assets...")
    for asset in ["build", "jsm", "textures", "models"]:
        src = os.path.join(pipeline_dir, asset)
        dst = os.path.join(build_parent if asset == "build" else project_dir, asset)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copytree(src, dst)
    
    # Start server
    import http.server, socketserver, threading, socket
    os.chdir(build_parent)
    
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
    print("Starting browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    
    # Run experiments
    experiments_to_run = [args.experiment] if args.experiment else list(EXPERIMENTS.keys())
    all_summaries = []
    
    for exp_id in experiments_to_run:
        summary = await run_experiment(
            exp_id, eval_data, args.n, output_dir, project_dir, browser, server_url
        )
        all_summaries.append(summary)
    
    # Cleanup
    await browser.close()
    await playwright.stop()
    httpd.shutdown()
    
    # Print comparison
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPARISON")
    print("=" * 70)
    print(f"\n{'Experiment':<30} {'Exec':>8} {'Visual':>8} {'Final':>8}")
    print("-" * 56)
    for s in all_summaries:
        print(f"{s['name']:<30} {s['avg_execution']:>8.3f} {s['avg_visual']:>8.3f} {s['avg_final']:>8.3f}")
    
    # Save comparison
    with open(os.path.join(output_dir, "comparison.json"), "w") as f:
        json.dump(all_summaries, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run prompt experiments")
    parser.add_argument("--n", type=int, default=10, help="Examples per experiment")
    parser.add_argument("--experiment", type=str, choices=list(EXPERIMENTS.keys()),
                        help="Run single experiment (default: all)")
    parser.add_argument("--data", type=str, 
                        default=os.path.join(os.path.dirname(__file__), "..", "training", "training_data.json"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(__file__), "..", "evaluation_outputs"))
    
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
