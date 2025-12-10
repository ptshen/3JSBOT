"""This file loads three.js code in a browser environment using Playwright and renders the animation.
Based on the Codecademy guide: https://www.codecademy.com/article/build-a-3d-environment-with-three-js
"""

import asyncio
from playwright.async_api import async_playwright
import os
import tempfile
import re
import http.server
import socketserver
import threading
import socket
from pathlib import Path


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


def process_js_code(js_code: str) -> str:
    """
    Process JavaScript code to work with local Three.js files via import map.
    Converts ES6 imports to dynamic imports that work with the import map.

    Args:
        js_code: The JavaScript code containing three.js animation logic
    
    Returns:
        Processed JavaScript code compatible with local Three.js via import map
    """
    # Extract all import statements to determine what needs to be loaded
    # Pattern: import { A, B } from 'path' or import * as X from 'path' or import X from 'path'
    import_pattern = r"import\s+(?:(?:\{([^}]+)\}|\*\s+as\s+(\w+)|(\w+))\s+from\s+)?['\"]([^'\"]+)['\"];?"
    import_matches = re.finditer(import_pattern, js_code, re.MULTILINE)
    
    # Track imports by module path with their exports
    imports_by_module = {}
    
    for match in import_matches:
        named_imports = match.group(1)  # { A, B, C }
        namespace_import = match.group(2)  # * as X
        default_import = match.group(3)  # X
        module_path = match.group(4)  # 'three' or 'three/addons/...'
        
        if module_path:
            if module_path not in imports_by_module:
                imports_by_module[module_path] = []
            
            if named_imports:
                # Named imports: { A, B, C }
                exports = [e.strip() for e in named_imports.split(',')]
                imports_by_module[module_path].extend(exports)
            elif namespace_import:
                # Namespace import: * as X
                imports_by_module[module_path].append(f"* as {namespace_import}")
            elif default_import:
                # Default import: X
                imports_by_module[module_path].append(default_import)
    
    # Remove all ES6 import statements
    processed_code = re.sub(r"import\s+.*?from\s+['\"][^'\"]+['\"];?\s*\n?", "", js_code, flags=re.MULTILINE)
    processed_code = re.sub(r"import\s+.*?from\s+['\"][^'\"]+['\"];?\s*$", "", processed_code, flags=re.MULTILINE)
    
    # Build dynamic import code for all modules
    addons_code = ""
    
    for module_path, exports in imports_by_module.items():
        if module_path == 'three':
            # THREE is already loaded globally in the HTML, skip
            continue
        
        # Convert module path to use import map format
        import_path = module_path
        
        # Extract module name for variable naming
        module_name = os.path.basename(module_path).replace('.js', '').replace('.module', '').replace('.min', '')
        # Clean up module name (remove special chars)
        module_name = re.sub(r'[^a-zA-Z0-9_]', '', module_name)
        if not module_name:
            module_name = "Module"
        
        # Separate namespace imports from named/default imports
        namespace_imports = [e for e in exports if e.startswith('* as ')]
        regular_exports = [e for e in exports if not e.startswith('* as ')]
        
        if namespace_imports:
            # Handle namespace import: * as X
            for ns_import in namespace_imports:
                var_name = ns_import.replace('* as ', '').strip()
                addons_code += f"""
// Load {module_path} as namespace {var_name}
const {var_name} = await import('{import_path}');
window.{var_name} = {var_name};

"""
        
        if regular_exports:
            # Handle named/default imports
            unique_exports = list(set(regular_exports))
            exports_str = ', '.join(unique_exports)
            
            addons_code += f"""
// Load {module_path}
const {module_name}Module = await import('{import_path}');
const {{ {exports_str} }} = {module_name}Module;
// Make exports available globally
{chr(10).join([f'window.{exp} = {exp};' for exp in unique_exports])}

"""
    
    # Also check for common addons that might be used without explicit imports
    if re.search(r'\b(new\s+)?OrbitControls\b', processed_code, re.IGNORECASE) and 'OrbitControls' not in addons_code:
        addons_code += """
// Load OrbitControls (detected usage without import)
const OrbitControlsModule = await import('three/addons/controls/OrbitControls.js');
const OrbitControls = OrbitControlsModule.OrbitControls;
window.OrbitControls = OrbitControls;

"""
    
    if re.search(r'\b(new\s+)?Stats\b', processed_code, re.IGNORECASE) and 'Stats' not in addons_code:
        addons_code += """
// Load Stats.js (detected usage without import)
try {
    const StatsModule = await import('three/addons/libs/stats.module.js');
    const Stats = StatsModule.default || StatsModule.Stats || StatsModule;
    window.Stats = Stats;
} catch (e) {
    console.warn('Failed to load Stats.js:', e);
    window.Stats = class Stats {
        constructor() {
            this.dom = document.createElement('div');
        }
        showPanel() {}
        begin() {}
        end() {}
    };
}

"""
    
    # Replace THREE.OrbitControls references (if OrbitControls is loaded)
    if 'OrbitControls' in addons_code:
        processed_code = re.sub(r'\bTHREE\.OrbitControls\b', 'OrbitControls', processed_code)
    
    # Handle variable declarations that might conflict with auto-setup
    # The model often generates: "let camera, scene, renderer;" which conflicts with auto-injection
    # Remove empty declarations (declarations without assignments) for these variables
    # Pattern: "let camera, scene, renderer;" or "let camera, scene, renderer, labelRenderer;"
    
    # Remove multi-variable declarations that include camera/scene/renderer without assignments
    # Match any declaration that contains camera, scene, or renderer (even with other variables)
    lines = processed_code.split('\n')
    cleaned_lines = []
    for line in lines:
        # Check if line is an empty declaration that includes camera/scene/renderer
        # Pattern matches: "let camera, scene, renderer;" or "let camera, scene, renderer, labelRenderer;"
        # We check if the line contains any of our target variables
        if re.match(r'^\s*(let|const|var)\s+[^=;]+;\s*$', line, re.IGNORECASE):
            # Check if this declaration contains camera, scene, or renderer
            if re.search(r'\b(camera|scene|renderer)\b', line, re.IGNORECASE):
                # Check if it's an empty declaration (no assignment)
                if '=' not in line:
                    # Skip empty declarations - they'll be handled by auto-injection or actual assignments
                    # But we need to preserve other variables in the declaration
                    # Extract variables that are NOT camera/scene/renderer
                    var_match = re.match(r'^\s*(let|const|var)\s+([^=;]+);\s*$', line, re.IGNORECASE)
                    if var_match:
                        var_list = var_match.group(2)
                        # Split by comma and filter out camera/scene/renderer
                        vars_to_keep = []
                        for var in var_list.split(','):
                            var = var.strip()
                            if var and not re.match(r'^(camera|scene|renderer)$', var, re.IGNORECASE):
                                vars_to_keep.append(var)
                        
                        # If there are other variables to keep, add a declaration for them
                        if vars_to_keep:
                            decl_type = var_match.group(1)
                            cleaned_lines.append(f"{decl_type} {', '.join(vars_to_keep)};")
                    # Skip the original line (camera/scene/renderer will be auto-injected)
                    continue
        cleaned_lines.append(line)
    processed_code = '\n'.join(cleaned_lines)
    
    # After removing empty declarations, check if camera/scene/renderer are still declared elsewhere
    # If they are declared with let/const/var later in the code, we shouldn't auto-inject
    # Check for any remaining declarations (not just assignments)
    has_renderer_decl = re.search(r'\b(let|const|var)\s+renderer\b', processed_code, re.IGNORECASE)
    has_camera_decl = re.search(r'\b(let|const|var)\s+camera\b', processed_code, re.IGNORECASE)
    has_scene_decl = re.search(r'\b(let|const|var)\s+scene\b', processed_code, re.IGNORECASE)
    
    # Check if camera has lookAt call (to center on scene)
    has_camera_lookat = re.search(r'\bcamera\.lookAt\s*\(', processed_code, re.IGNORECASE)
    
    # Check what's actually referenced (after removing empty declarations)
    has_renderer_ref = 'renderer' in processed_code.lower()
    has_camera_ref = 'camera' in processed_code.lower()
    has_scene_ref = 'scene' in processed_code.lower()
    
    setup_code = ""
    # Only auto-inject if the variable is referenced but not declared anywhere
    if has_renderer_ref and not has_renderer_decl:
        setup_code += """
// Auto-create renderer if missing (Codecademy guide pattern)
var renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

"""
    if has_camera_ref and not has_camera_decl:
        setup_code += """
// Auto-create camera if missing (Codecademy guide pattern)
var camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 5;
camera.lookAt(0, 0, 0);

"""
    if has_scene_ref and not has_scene_decl:
        setup_code += """
// Auto-create scene if missing
var scene = new THREE.Scene();

"""
    
    # Add camera lookAt at the end if needed (after user code runs)
    end_code = ""
    if has_camera_ref and has_camera_decl and not has_camera_lookat:
        # Add lookAt call after a short delay to ensure camera is positioned
        end_code = """
// Ensure camera looks at center after initialization
setTimeout(() => {
    if (typeof camera !== 'undefined' && camera.lookAt) {
        camera.lookAt(0, 0, 0);
    }
}, 100);
"""
    
    # Wrap in async IIFE to allow await for addons
    wrapped_code = f"""
(async function() {{
{addons_code}
{setup_code}
{processed_code}
{end_code}
}})();
"""
    
    return wrapped_code


def create_html_file(js_code: str, output_dir: str, pipeline_dir: str = None) -> str:
    """
    Create an HTML file using local Three.js files from the pipeline directory.
    Uses import map to reference local build and jsm directories.
    
    Args:
        js_code: The processed JavaScript code
        output_dir: Directory where HTML file will be created
        pipeline_dir: Directory containing build/ and jsm/ folders (default: None, uses script's parent)
    
    Returns:
        Path to the created HTML file
    """
    import shutil
    
    # Determine pipeline directory (where build/ and jsm/ live)
    if pipeline_dir is None:
        # Get the directory containing this script (pipeline/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pipeline_dir = script_dir
    else:
        pipeline_dir = os.path.abspath(pipeline_dir)
    
    # Copy build and jsm directories to output_dir if they don't exist
    build_src = os.path.join(pipeline_dir, "build")
    jsm_src = os.path.join(pipeline_dir, "jsm")
    build_dst = os.path.join(output_dir, "build")
    jsm_dst = os.path.join(output_dir, "jsm")
    
    if os.path.exists(build_src) and not os.path.exists(build_dst):
        print(f"Copying build directory from {build_src} to {build_dst}...")
        shutil.copytree(build_src, build_dst)
    
    if os.path.exists(jsm_src) and not os.path.exists(jsm_dst):
        print(f"Copying jsm directory from {jsm_src} to {jsm_dst}...")
        shutil.copytree(jsm_src, jsm_dst)
    
    # Copy asset directories that might be referenced in the code (textures, models, sounds, etc.)
    asset_dirs = ["textures", "models", "sounds", "fonts", "files", "luts", "ies", "materialx", "screenshots"]
    for asset_dir in asset_dirs:
        asset_src = os.path.join(pipeline_dir, asset_dir)
        asset_dst = os.path.join(output_dir, asset_dir)
        if os.path.exists(asset_src) and not os.path.exists(asset_dst):
            print(f"Copying {asset_dir} directory from {asset_src} to {asset_dst}...")
            shutil.copytree(asset_src, asset_dst)
    
    # Process the JavaScript code
    processed_js = process_js_code(js_code)
    
    # Create HTML using local Three.js files with import map
    # Import map uses relative paths: "./build/three.module.js" and "./jsm/"
    # Use json.dumps to ensure valid JSON in the import map
    import json
    import_map = {
        "imports": {
            "three": "./build/three.module.js",
            "three/addons/": "./jsm/"
        }
    }
    import_map_json = json.dumps(import_map, indent=4)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Three.js Animation</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: #000;
        }}
        #container {{
            width: 100vw;
            height: 100vh;
            position: relative;
            margin: 0;
            padding: 0;
        }}
        canvas {{
            display: block;
            width: 100vw;
            height: 100vh;
            position: absolute;
            top: 0;
            left: 0;
        }}
    </style>
    <!-- Import map to resolve 'three' module specifier using local files -->
    <script type="importmap">
{import_map_json}
    </script>
    <!-- Load Three.js as ES module from local build directory -->
    <script type="module">
        // Import Three.js as ES module and make it globally available
        import * as THREE from 'three';
        
        // Make THREE available globally
        window.THREE = THREE;
        
        // User's code will run here
        {processed_js}
    </script>
</head>
<body>
    <!-- Container div for Three.js renderer (if code references it) -->
    <div id="container"></div>
</body>
</html>"""

    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, "w") as f:
        f.write(html_content)

    return html_path


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files with proper CORS headers."""
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()


def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.
    
    Args:
        start_port: Starting port number
        max_attempts: Maximum number of ports to try
    
    Returns:
        Available port number
    """
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")


def start_http_server(directory: str, port: int = None) -> tuple:
    """
    Start a simple HTTP server to serve the HTML file.
    
    Args:
        directory: Directory to serve files from
        port: Port number (default: None, will find available port)
    
    Returns:
        Tuple of (server object, server URL)
    """
    # Find available port if not specified
    if port is None:
        port = find_available_port()
    
    os.chdir(directory)
    handler = SimpleHTTPRequestHandler
    
    # Try to bind to the port, find another if it's in use
    for attempt in range(10):
        try:
            httpd = socketserver.TCPServer(("", port), handler)
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                port = find_available_port(port + 1)
                continue
            raise
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    server_url = f"http://localhost:{port}"
    return httpd, server_url


async def load_and_render_threejs(
    js_code: str, 
    output_path: str = "screenshot.jpg", 
    wait_time: float = 2.0,
    keep_server_running: bool = False,
    project_dir: str = None,
    pipeline_dir: str = None
):
    """
    Load three.js JavaScript code in a browser environment using Playwright,
    render the animation, and take a screenshot.
    Uses local Three.js files from the pipeline directory.

    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "screenshot.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the HTTP server running (default: False)
        project_dir: Directory where files will be created (default: None, uses temp dir)
        pipeline_dir: Directory containing build/ and jsm/ folders (default: None, uses script's parent)
    """
    # Create output directory
    if project_dir:
        if os.path.exists(project_dir):
            import shutil
            shutil.rmtree(project_dir)
        os.makedirs(project_dir)
        temp_dir = project_dir
        cleanup_dir = False
    else:
        temp_dir = tempfile.mkdtemp(prefix="threejs_")
        cleanup_dir = True

    httpd = None
    
    try:
        print(f"Creating HTML file in {temp_dir}...")
        
        # Determine pipeline directory if not provided
        if pipeline_dir is None:
            pipeline_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create HTML file with embedded JavaScript and copy build/jsm directories
        html_path = create_html_file(js_code, temp_dir, pipeline_dir=pipeline_dir)
        print(f"HTML file created: {html_path}")
        
        # Start HTTP server
        print("Starting HTTP server...")
        httpd, server_url = start_http_server(temp_dir)
        print(f"HTTP server ready at {server_url}")
        
        # Give server a moment to initialize
        await asyncio.sleep(1)

        # Launch browser with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set viewport size
            await page.set_viewport_size({'width': 1920, 'height': 1080})

            # Set up console logging (filter out WebGL context warnings)
            def log_console(msg):
                # Filter out the WebGL context warning since it's not critical
                if "WebGL context" not in msg.text and "existing context" not in msg.text:
                    print(f"Browser console: {msg.text}")
            page.on('console', log_console)
            page.on('pageerror', lambda err: print(f"Page error: {err}"))
            
            # Load the page
            html_url = f"{server_url}/index.html"
            print(f"Loading page: {html_url}")
            try:
                await page.goto(html_url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f"Error loading page: {e}")
                raise

            # Wait for Three.js to load and scene to be created
            await page.wait_for_function(
                '() => typeof THREE !== "undefined" && typeof THREE.Scene !== "undefined"',
                timeout=15000
            )
            print("Three.js loaded")
            
            # Wait for canvas element to exist (don't check WebGL context to avoid multiple context creation)
            await page.wait_for_function('''
                () => {
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {
                        if (canvas.width > 0 && canvas.height > 0) {
                            return true;
                        }
                    }
                    return false;
                }
            ''', timeout=15000)
            print("Canvas ready")

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

            # Verify canvas is visible before screenshot (no fallback rendering)
            canvas_ready = await page.evaluate('''
                () => {
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {
                        if (canvas.width > 0 && canvas.height > 0) {
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
            ''')
            
            if not canvas_ready:
                print("Warning: Canvas not ready, capturing blank screen")
            
            # Take screenshot of the actual page (no fallback - will capture blank if nothing rendered)
            print(f"Taking screenshot...")
            # Screenshot the canvas element directly if it exists, otherwise screenshot the page
            canvas_exists = await page.evaluate('document.querySelector("canvas") !== null')
            if canvas_exists:
                # Screenshot just the canvas element
                canvas_element = await page.query_selector('canvas')
                if canvas_element:
                    await canvas_element.screenshot(path=output_path, type='jpeg', quality=90)
                else:
                    # Fallback to full page if canvas selector fails
                    await page.screenshot(path=output_path, type='jpeg', quality=90, full_page=True)
            else:
                # No canvas found, screenshot blank page
                await page.screenshot(path=output_path, type='jpeg', quality=90, full_page=True)
            print(f"Screenshot saved to {output_path}")

            # Close browser
            await browser.close()

        if keep_server_running:
            print(f"\n{'='*60}")
            print(f"Screenshot saved to {output_path}")
            print(f"HTTP server is running at {server_url}")
            print(f"Project directory: {temp_dir}")
            print(f"\nYou can view the animation at: {html_url}")
            print(f"Press Ctrl+C to stop the server when you're done.")
            print(f"{'='*60}\n")

            # Keep the server running - wait for user interrupt
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down server...")

    finally:
        # Stop HTTP server
        if httpd:
            print("Stopping HTTP server...")
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception as e:
                print(f"Error shutting down server: {e}")

        # Clean up temporary directory only if not keeping it
        if cleanup_dir and os.path.exists(temp_dir):
            print(f"Cleaning up temporary directory {temp_dir}...")
            import shutil
            shutil.rmtree(temp_dir)


def render_threejs(
    js_code: str, 
    output_path: str = None, 
    wait_time: float = 2.0,
    keep_server_running: bool = False,
    project_dir: str = None,
    pipeline_dir: str = None
):
    """
    Synchronous wrapper for load_and_render_threejs.

    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: None, saves in script directory)
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the HTTP server running (default: False)
        project_dir: Directory where files will be created (default: None, uses temp dir)
        pipeline_dir: Directory containing build/ and jsm/ folders (default: None, uses script's parent)
    """
    # If output_path is not specified, save in the same directory as this script
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "screenshot.jpg")
    
    asyncio.run(load_and_render_threejs(js_code, output_path, wait_time, keep_server_running, project_dir, pipeline_dir))


if __name__ == "__main__":
    # Read JavaScript code from gen_code.js
    js_code = read_js_from_file("gen_code.js")

    # Render and save screenshot
    # Set keep_server_running=True to view in browser, False for automated screenshot only
    render_threejs(js_code, keep_server_running=True)
