#!/usr/bin/env python3
"""
Run temp=0 baselines.
Default: Gemini only (GEMINI_API_KEY).
Add --all to also run Tinker models (TOGETHER_API_KEY).

Uses baseline prompt (no system prompt) and logs row-by-row to experiment_results.csv.
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
from typing import List, Tuple

import requests
from playwright.async_api import async_playwright

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from load_code import process_js_code
from experiment_logger import log_experiment_result

# API endpoints
EVAL_API = "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate"
TOGETHER_API = os.environ.get("TOGETHER_API_URL", "https://api.together.xyz/v1/chat/completions")

# Baseline prompt (no system prompt)
BASELINE_USER = """Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting

Return only the JavaScript code without any explanations."""


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def extract_code_from_markdown(content: str) -> str:
    # Try to capture inside fenced code blocks first
    fence_regex = r'```(?:javascript|js)?\\s*\\n([\\s\\S]*?)```'
    m = re.search(fence_regex, content, re.MULTILINE)
    if m:
        code = m.group(1)
    else:
        code = content
    # Split and drop first/last lines if they look like fences
    lines = code.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


FORBIDDEN_PATTERNS = ["OrbitControls", "RoomEnvironment", "PMREMGenerator"]
INSECURE_TEXTURE_REGEX = r"TextureLoader\\(\\)\\.load\\([\"']https?:\\/\\/.*?[\"']\\)"


def sanitize_code_for_runner(js_code: str) -> str:
    """Remove common addon-only / external texture lines to avoid runtime failures."""
    lines = js_code.splitlines()
    # Drop lines using addons we don't import
    filtered = [ln for ln in lines if not any(pat in ln for pat in FORBIDDEN_PATTERNS)]
    # Drop external texture loads (network forbidden / CORS)
    safe = []
    for ln in filtered:
        if re.search(INSECURE_TEXTURE_REGEX, ln):
            continue
        safe.append(ln)
    return "\n".join(safe)


def calculate_execution_score(js_errors: List[str], render_success: bool) -> Tuple[float, str]:
    if not render_success:
        return 0.0, "crashed"
    if not js_errors:
        return 1.0, "clean"
    has_critical = any("SyntaxError" in e or "Unexpected token" in e for e in js_errors)
    return (0.25, "critical_errors") if has_critical else (0.5, "runtime_errors")


# ---------------------------------------------------------------------
# Code generation (Tinker / Together)
# ---------------------------------------------------------------------
def generate_code_tinker(description: str, model: str) -> Tuple[str, bool, str]:
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        return "", False, "TOGETHER_API_KEY not set"

    user_prompt = BASELINE_USER.format(description=description)
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
        "stream": False
    }
    # Tinker/Together: send multiple common headers (Bearer, X-Api-Key, X-Tinker-Api-Key)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Api-Key": api_key,
        "X-Tinker-Api-Key": api_key,
    }

    try:
        resp = requests.post(TOGETHER_API, json=payload, headers=headers, timeout=180)
        if resp.status_code != 200:
            # Return full response text for debugging
            return "", False, f"{resp.status_code}: {resp.text}"
        data = resp.json()
        if "choices" in data and data["choices"]:
            content = data["choices"][0]["message"]["content"]
            return extract_code_from_markdown(content), True, content
        return "", False, f"No choices in response: {data}"
    except Exception as e:
        return "", False, f"request failed: {e}"


# ---------------------------------------------------------------------
# Code generation (Gemini)
# ---------------------------------------------------------------------
def generate_code_gemini(description: str) -> Tuple[str, bool, str]:
    if not GEMINI_AVAILABLE:
        return "", False, "google-genai not installed; pip install google-genai"

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "", False, "GEMINI_API_KEY not set"

    client = genai.Client(api_key=api_key)
    user_prompt = BASELINE_USER.format(description=description)
    # Try current supported models, highest quality first
    models_to_try = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    last_err = None
    for model in models_to_try:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config={"temperature": 0.0},
            )
            if resp and hasattr(resp, "text") and resp.text:
                return extract_code_from_markdown(resp.text), True, resp.text
            last_err = f"{model} empty response"
        except Exception as e:
            last_err = f"{model}: {e}"
            continue
    return "", False, last_err or "Gemini failed"


# ---------------------------------------------------------------------
# Visual evaluation
# ---------------------------------------------------------------------
def evaluate_visual(screenshot_path: str, description: str) -> Tuple[float, str]:
    try:
        with open(screenshot_path, "rb") as f:
            b64img = base64.b64encode(f.read()).decode("utf-8")
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
        resp = requests.post(
            EVAL_API,
            json={"image": {"image_base64": b64img}, "prompt": prompt},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if "annotation" in data:
            m = re.search(r"([0-9]*\\.?[0-9]+)", data["annotation"])
            if m:
                val = float(m.group(1))
                return max(0.0, min(1.0, val)), data["annotation"]
        return 0.0, "Could not parse"
    except Exception as e:
        return 0.0, str(e)


# ---------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------
async def render_code(js_code: str, output_path: str, project_dir: str, browser, server_url: str) -> Tuple[bool, List[str]]:
    js_errors: List[str] = []
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
        Path(project_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(project_dir, "index.html"), "w") as f:
            f.write(html)

        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        try:
            await page.goto(f"{server_url}/project/index.html", wait_until="networkidle", timeout=30000)
            await page.wait_for_function('() => typeof THREE !== "undefined"', timeout=10000)
            await asyncio.sleep(2.0)
            canvas = await page.query_selector("canvas")
            if canvas:
                await canvas.screenshot(path=output_path, type="jpeg", quality=90)
            else:
                await page.screenshot(path=output_path, type="jpeg", quality=90)
            await page.close()
            return True, js_errors
        except Exception as e:
            await page.close()
            return False, js_errors + [str(e)]
    except Exception as e:
        return False, [str(e)]


# ---------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------
async def run_condition(
    condition: str,
    model: str,
    is_gemini: bool,
    data: List[dict],
    n: int,
    output_dir: str,
    project_dir: str,
    browser,
    server_url: str,
):
    print(f"\n{'='*60}")
    print(f"CONDITION: {condition} | MODEL: {model}")
    print(f"{'='*60}")
    cond_dir = os.path.join(output_dir, condition)
    os.makedirs(cond_dir, exist_ok=True)

    results = []
    for i, example in enumerate(data[:n]):
        description = example.get("description", "")
        if not description:
            continue
        print(f"\n[{i+1}/{n}] ", end="", flush=True)

        # Generate
        if is_gemini:
            code, gen_ok, gen_err = generate_code_gemini(description)
        else:
            code, gen_ok, gen_err = generate_code_tinker(description, model)
        if not gen_ok:
            print("✗ Gen failed")
            log_experiment_result(
                experiment_condition=condition,
                example_idx=i,
                prompt=description,
                execution_score=0.0,
                execution_status="gen_failed",
                visual_score=0.0,
                final_score=0.0,
                output_path=cond_dir,
                error_msg=str(gen_err),
                iterations=1,
            )
            continue

        # Sanitize code to avoid addon/CORS crashes
        code = sanitize_code_for_runner(code)

        code_path = os.path.join(cond_dir, f"{i:03d}_code.js")
        with open(code_path, "w") as f:
            f.write(code)

        screenshot_path = os.path.join(cond_dir, f"{i:03d}_screenshot.jpg")
        render_ok, js_errors = await render_code(code, screenshot_path, project_dir, browser, server_url)
        exec_score, exec_status = calculate_execution_score(js_errors, render_ok)

        if not render_ok:
            final_score = 0.7 * exec_score
            log_experiment_result(
                experiment_condition=condition,
                example_idx=i,
                prompt=description,
                execution_score=exec_score,
                execution_status=exec_status,
                visual_score=0.0,
                final_score=final_score,
                output_path=cond_dir,
                error_msg="; ".join(js_errors),
                iterations=1,
            )
            print("✗ Render failed")
            continue

        visual_score, _ = evaluate_visual(screenshot_path, description)
        final_score = 0.7 * exec_score + 0.3 * visual_score

        log_experiment_result(
            experiment_condition=condition,
            example_idx=i,
            prompt=description,
            execution_score=exec_score,
            execution_status=exec_status,
            visual_score=visual_score,
            final_score=final_score,
            output_path=cond_dir,
            error_msg="; ".join(js_errors),
            iterations=1,
        )
        status_icon = {"clean": "✓", "runtime_errors": "⚠", "critical_errors": "⚠", "crashed": "✗"}
        print(f"{status_icon.get(exec_status, '?')} exec={exec_score:.1f} vis={visual_score:.2f} final={final_score:.3f}")
        results.append(final_score)


async def main_async(args):
    # Load data (use last 20% as eval like run_experiments)
    with open(args.data, "r") as f:
        all_data = json.load(f)
    split_idx = int(len(all_data) * 0.8)
    eval_data = all_data[split_idx:]
    print(f"Loaded {len(eval_data)} validation examples")

    # Prepare output dirs
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(args.output_dir, f"temp0_baselines_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    project_dir = os.path.join(output_dir, "workspace", "project")
    build_parent = os.path.join(output_dir, "workspace")
    os.makedirs(project_dir, exist_ok=True)

    # Copy assets
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
                s.bind(("", port))
                break
        except OSError:
            continue
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    server_url = f"http://localhost:{port}"
    print(f"Server: {server_url}")

    # Start browser
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)

    # Default: only Gemini
    conditions = [
        ("gemini_temp0", "gemini-2.5-flash", True),
    ]
    # If --all, also run Tinker models
    if args.all:
        conditions.extend([
            ("llama33_70b_temp0", "meta-llama/Llama-3.3-70B-Instruct", False),
            ("gpt_oss_120b_temp0", "openai/gpt-oss-120b", False),
        ])

    for cond_name, model, is_gemini in conditions:
        await run_condition(
            condition=cond_name,
            model=model,
            is_gemini=is_gemini,
            data=eval_data,
            n=args.n,
            output_dir=output_dir,
            project_dir=project_dir,
            browser=browser,
            server_url=server_url,
        )

    await browser.close()
    await playwright.stop()
    httpd.shutdown()
    print(f"\n✓ Results saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run temp=0 baselines (default: Gemini only, use --all for Tinker too)")
    parser.add_argument("--n", type=int, default=10, help="Examples to run per condition")
    parser.add_argument("--data", type=str, default=os.path.join(os.path.dirname(__file__), "..", "training", "training_data.json"))
    parser.add_argument("--output-dir", type=str, default=os.path.join(os.path.dirname(__file__), "..", "evaluation_outputs"))
    parser.add_argument("--all", action="store_true", help="Include Tinker models in addition to Gemini")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

