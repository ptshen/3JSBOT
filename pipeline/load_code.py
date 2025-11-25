"""This file loads three.js code in a browser environment using Playwright and renders the animation."""

import asyncio
from playwright.async_api import async_playwright
import os
import json
import subprocess
import shutil
import tempfile
import time
import signal
import re


def read_js_from_file(file_path: str = "gen_code.js") -> str:
    """
    Read JavaScript code from a file.
    
    Args:
        file_path: Path to the JavaScript file (default: "gen_code.js")
    
    Returns:
        The JavaScript code as a string
    """
    with open(file_path, "r") as f:
        return f.read()


def process_user_code(js_code: str) -> str:
    """
    Process user code to make it compatible with our environment.
    
    Args:
        js_code: The raw JavaScript code from the user
        
    Returns:
        Processed JavaScript code with imports removed
    """
    lines = js_code.split('\n')
    processed_lines = []
    
    for line in lines:
        # Skip import lines that import from 'three' (exact match)
        if re.match(r'^\s*import\s+.*\s+from\s+[\'"]three[\'"]', line.strip()):
            continue
        # Also skip import maps that reference three.js addons we've already imported
        if re.match(r'^\s*import\s+.*\s+from\s+[\'"]three/examples/', line.strip()):
            continue
        processed_lines.append(line)
    
    processed_code = '\n'.join(processed_lines)
    
    # Replace THREE references to use window.THREE (which has addons)
    # This ensures code using THREE.TeapotGeometry etc. will work
    processed_code = re.sub(r'\bTHREE\.', 'window.THREE.', processed_code)
    
    return processed_code


def extract_vite_url(line: str) -> str:
    """
    Extract Vite server URL from output line.
    
    Args:
        line: A line of output from Vite
        
    Returns:
        URL string if found, None otherwise
    """
    # Look for various Vite output patterns
    patterns = [
        r'Local:\s+(https?://[^\s]+)',
        r'Network:\s+(https?://[^\s]+)',
        r'(https?://localhost:\d+)',
        r'(https?://127\.0\.0\.1:\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def setup_vite_project(js_code: str, project_dir: str):
    """
    Set up a vite project with three.js and the user's code.

    Args:
        js_code: The JavaScript code containing three.js animation logic
        project_dir: Directory where the vite project will be created
    """
    # Create package.json
    package_json = {
        "name": "threejs-vite-temp",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "devDependencies": {
            "vite": "^5.0.0"
        },
        "dependencies": {
            "three": "^0.160.0"
        }
    }

    with open(os.path.join(project_dir, "package.json"), "w") as f:
        json.dump(package_json, f, indent=2)

    # Create index.html
    # Check if the code references 'myCanvas' to decide whether to include it
    needs_canvas_element = 'myCanvas' in js_code or "getElementById('myCanvas')" in js_code or 'getElementById("myCanvas")' in js_code

    canvas_element = '<canvas id="myCanvas"></canvas>' if needs_canvas_element else ''

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Three.js Animation</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background-color: #000;
        }}
        canvas {{
            display: block;
            width: 100vw;
            height: 100vh;
        }}
    </style>
</head>
<body>
    {canvas_element}
    <script type="module" src="/main.js"></script>
</body>
</html>"""

    with open(os.path.join(project_dir, "index.html"), "w") as f:
        f.write(html_content)

    # Create main.js with user's code
    # Prepend common three.js imports and addons
    common_imports = """import * as THREE from 'three';

// Import common three.js addons - controls
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TrackballControls } from 'three/examples/jsm/controls/TrackballControls.js';
import { FlyControls } from 'three/examples/jsm/controls/FlyControls.js';

// Import common three.js addons - geometries
import { TeapotGeometry } from 'three/examples/jsm/geometries/TeapotGeometry.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry.js';

// Import common three.js addons - loaders
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js';
import { FontLoader } from 'three/examples/jsm/loaders/FontLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { HDRLoader } from 'three/examples/jsm/loaders/HDRLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';

// Import common three.js addons - post-processing
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';

// Import common three.js addons - animation
import { AnimationMixer } from 'three/examples/jsm/animation/AnimationMixer.js';

// Import common three.js addons - environments
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

// Make THREE globally available
window.THREE = THREE;

// Attach addons to THREE namespace (preserving original THREE object)
THREE.OrbitControls = OrbitControls;
THREE.TrackballControls = TrackballControls;
THREE.FlyControls = FlyControls;
THREE.TeapotGeometry = TeapotGeometry;
THREE.TeapotBufferGeometry = TeapotGeometry; // Alias for older code
THREE.RoundedBoxGeometry = RoundedBoxGeometry;
THREE.TextGeometry = TextGeometry;
THREE.GLTFLoader = GLTFLoader;
THREE.OBJLoader = OBJLoader;
THREE.FBXLoader = FBXLoader;
THREE.FontLoader = FontLoader;
THREE.DRACOLoader = DRACOLoader;
THREE.HDRLoader = HDRLoader;
THREE.RGBELoader = RGBELoader;
THREE.EffectComposer = EffectComposer;
THREE.RenderPass = RenderPass;
THREE.UnrealBloomPass = UnrealBloomPass;
THREE.ShaderPass = ShaderPass;
THREE.AnimationMixer = AnimationMixer;
THREE.RoomEnvironment = RoomEnvironment;

// Also make commonly used addons available globally for code that expects them
window.OrbitControls = OrbitControls;
window.GLTFLoader = GLTFLoader;
window.EffectComposer = EffectComposer;
window.RenderPass = RenderPass;
window.AnimationMixer = AnimationMixer;

"""

    # Process user's code using the improved function
    user_code = process_user_code(js_code)

    main_js = common_imports + user_code

    with open(os.path.join(project_dir, "main.js"), "w") as f:
        f.write(main_js)


async def load_and_render_threejs(js_code: str, output_path: str = "test.jpg", wait_time: float = 2.0, keep_server_running: bool = False, project_dir: str = "threejs_vite_project"):
    """
    Load three.js JavaScript code in a browser environment using Vite and Playwright,
    render the animation, and take a screenshot.

    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the vite server running after screenshot for manual viewing (default: False)
        project_dir: Directory where the vite project will be created (default: "threejs_vite_project")
    """
    # Use persistent directory if keeping server running, otherwise use temp directory
    if keep_server_running:
        # Create persistent directory in current working directory
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        os.makedirs(project_dir)
        temp_dir = project_dir
        cleanup_dir = False
    else:
        temp_dir = tempfile.mkdtemp(prefix="threejs_vite_")
        cleanup_dir = True

    vite_process = None

    try:
        print(f"Setting up vite project in {temp_dir}...")

        # Set up vite project structure
        setup_vite_project(js_code, temp_dir)

        # Install dependencies
        print("Installing npm dependencies...")
        install_process = subprocess.run(
            ["npm", "install"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=120
        )

        if install_process.returncode != 0:
            print(f"npm install error: {install_process.stderr}")
            raise RuntimeError(f"Failed to install dependencies: {install_process.stderr}")

        print("Dependencies installed successfully.")

        # Start vite dev server
        print("Starting vite dev server...")
        vite_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for server to be ready and extract URL
        server_url = None
        max_wait = 30  # Maximum wait time in seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if vite_process.poll() is not None:
                # Process has terminated
                stdout, stderr = vite_process.communicate()
                raise RuntimeError(f"Vite server failed to start:\nstdout: {stdout}\nstderr: {stderr}")

            # Check if we can read from stdout without blocking
            line = vite_process.stdout.readline()
            if line:
                print(line.strip())
                # Use improved URL extraction
                extracted_url = extract_vite_url(line)
                if extracted_url:
                    server_url = extracted_url
                    break

            await asyncio.sleep(0.5)

        if not server_url:
            # Default to standard vite port
            server_url = "http://localhost:5173"

        print(f"Vite server ready at {server_url}")

        # Give server a moment to fully initialize
        await asyncio.sleep(2)

        # Launch browser with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set viewport size
            await page.set_viewport_size({'width': 1920, 'height': 1080})

            # Load the page from vite server
            try:
                await page.goto(server_url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f"Error loading page: {e}")
                # Try to get console messages for debugging
                page.on('console', lambda msg: print(f"Browser console: {msg.text}"))
                raise

            # Wait for canvas element and WebGL context to be created
            await page.wait_for_function('''
                () => {
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {
                        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                        if (gl !== null && canvas.width > 0 && canvas.height > 0) {
                            return true;
                        }
                    }
                    return false;
                }
            ''', timeout=15000)

            # Wait for multiple animation frames to ensure rendering has occurred
            await page.evaluate('''
                () => new Promise((resolve) => {
                    let frames = 0;
                    const targetFrames = 10;
                    function checkFrame() {
                        requestAnimationFrame(() => {
                            frames++;
                            if (frames >= targetFrames) {
                                resolve();
                            } else {
                                checkFrame();
                            }
                        });
                    }
                    checkFrame();
                })
            ''')

            # Additional wait to ensure animation has fully rendered
            await asyncio.sleep(wait_time)

            # Verify canvas is visible before screenshot
            await page.wait_for_function('''
                () => {
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {
                        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                        if (gl !== null && canvas.width > 0 && canvas.height > 0) {
                            const rect = canvas.getBoundingClientRect();
                            const style = window.getComputedStyle(canvas);
                            if (rect.width > 0 && rect.height > 0 &&
                                style.display !== 'none' &&
                                style.visibility !== 'hidden' &&
                                style.opacity !== '0') {
                                return true;
                            }
                        }
                    }
                    return false;
                }
            ''', timeout=5000)

            # Take screenshot
            await page.screenshot(path=output_path, type='jpeg', quality=90, full_page=True)

            print(f"Screenshot saved to {output_path}")

            # Close browser
            await browser.close()

        if keep_server_running:
            print(f"\n{'='*60}")
            print(f"Screenshot saved to {output_path}")
            print(f"Vite server is running at {server_url}")
            print(f"Project directory: {temp_dir}")
            print(f"\nYou can now view the animation in your browser!")
            print(f"Press Ctrl+C to stop the server when you're done.")
            print(f"{'='*60}\n")

            # Keep the server running - wait for user interrupt
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down server...")

    finally:
        # Stop vite server
        if vite_process and not keep_server_running:
            print("Stopping vite server...")
            vite_process.terminate()
            try:
                vite_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vite_process.kill()
        elif vite_process and keep_server_running:
            # User interrupted, stop the server
            print("Stopping vite server...")
            vite_process.terminate()
            try:
                vite_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vite_process.kill()

        # Clean up temporary directory only if not keeping it
        if cleanup_dir and os.path.exists(temp_dir):
            print(f"Cleaning up temporary directory {temp_dir}...")
            shutil.rmtree(temp_dir)


def render_threejs(js_code: str, output_path: str = "test.jpg", wait_time: float = 2.0, keep_server_running: bool = False, project_dir: str = "threejs_vite_project"):
    """
    Synchronous wrapper for load_and_render_threejs.

    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the vite server running after screenshot for manual viewing (default: False)
        project_dir: Directory where the vite project will be created (default: "threejs_vite_project")
    """
    asyncio.run(load_and_render_threejs(js_code, output_path, wait_time, keep_server_running, project_dir))


if __name__ == "__main__":
    # Read JavaScript code from gen_code.js
    js_code = read_js_from_file("gen_code.js")

    # Render and save screenshot
    # Set keep_server_running=True to view in browser, False for automated screenshot only
    render_threejs(js_code, keep_server_running=True)