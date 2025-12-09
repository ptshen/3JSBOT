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
    Process JavaScript code to work with CDN-based Three.js.
    Converts ES6 imports to use global THREE object (Codecademy guide pattern).
    
    Args:
        js_code: The JavaScript code containing three.js animation logic
    
    Returns:
        Processed JavaScript code compatible with CDN Three.js
    """
    # Check if OrbitControls is imported
    needs_orbit_controls = 'OrbitControls' in js_code and 'import' in js_code
    
    # Remove all ES6 import statements (more comprehensive regex)
    # Match import statements with various formats
    processed_code = re.sub(r"import\s+.*?from\s+['\"]three['\"];?\s*\n?", "", js_code, flags=re.MULTILINE)
    processed_code = re.sub(r"import\s+.*?from\s+['\"]three/examples.*?['\"];?\s*\n?", "", processed_code, flags=re.MULTILINE)
    processed_code = re.sub(r"import\s+.*?from\s+['\"]three['\"];?\s*$", "", processed_code, flags=re.MULTILINE)
    processed_code = re.sub(r"import\s+.*?from\s+['\"]three/examples.*?['\"];?\s*$", "", processed_code, flags=re.MULTILINE)
    
    # Load OrbitControls if needed (using dynamic import)
    addons_code = ""
    if needs_orbit_controls:
        addons_code = """
// Load OrbitControls addon from CDN
const OrbitControlsModule = await import('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js');
const OrbitControls = OrbitControlsModule.OrbitControls;
// Make OrbitControls available globally (not on THREE object since it's not extensible)
window.OrbitControls = OrbitControls;

"""
    
    # Replace OrbitControls references to use window.OrbitControls
    # This handles cases where code uses `new OrbitControls(...)` or `new THREE.OrbitControls(...)`
    if needs_orbit_controls:
        # Replace THREE.OrbitControls with OrbitControls (which will be available from window)
        processed_code = re.sub(r'\bTHREE\.OrbitControls\b', 'OrbitControls', processed_code)
    
    # Add automatic renderer and camera setup if they're missing (Codecademy guide pattern)
    # Check if renderer or camera are referenced but not defined
    has_renderer_ref = 'renderer' in processed_code.lower()
    has_camera_ref = 'camera' in processed_code.lower()
    has_renderer_def = re.search(r'\b(const|let|var)\s+renderer\s*=', processed_code)
    has_camera_def = re.search(r'\b(const|let|var)\s+camera\s*=', processed_code)
    
    setup_code = ""
    if has_renderer_ref and not has_renderer_def:
        setup_code += """
// Auto-create renderer if missing (Codecademy guide pattern)
var renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

"""
    if has_camera_ref and not has_camera_def:
        setup_code += """
// Auto-create camera if missing (Codecademy guide pattern)
var camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 5;
camera.lookAt(0, 0, 0);

"""
    
    # Wrap in async IIFE to allow await for addons
    wrapped_code = f"""
(async function() {{
{addons_code}
{setup_code}
{processed_code}
}})();
"""
    
    return wrapped_code


def create_html_file(js_code: str, output_dir: str) -> str:
    """
    Create an HTML file following the Codecademy guide pattern.
    Uses Three.js CDN and embeds the JavaScript code.
    
    Args:
        js_code: The processed JavaScript code
        output_dir: Directory where HTML file will be created
    
    Returns:
        Path to the created HTML file
    """
    # Process the JavaScript code
    processed_js = process_js_code(js_code)
    
    # Create HTML following Codecademy guide structure
    # Using ES module version of Three.js from CDN with import map
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
        }}
        body {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #000;
            overflow: hidden;
        }}
        canvas {{
            display: block;
            width: 100vw;
            height: 100vh;
        }}
    </style>
    <!-- Import map to resolve 'three' module specifier -->
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/examples/jsm/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>
    <!-- Load Three.js as ES module from CDN (following Codecademy guide approach) -->
    <script type="module">
        // Import Three.js as ES module and make it globally available
        import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
        
        // Make THREE available globally (Codecademy guide pattern)
        window.THREE = THREE;
        
        // User's code will run here
        {processed_js}
    </script>
</head>
<body></body>
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
    output_path: str = "test.jpg", 
    wait_time: float = 2.0,
    keep_server_running: bool = False,
    project_dir: str = None
):
    """
    Load three.js JavaScript code in a browser environment using Playwright,
    render the animation, and take a screenshot.
    Follows the Codecademy guide approach using CDN-based Three.js.
    
    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the HTTP server running (default: False)
        project_dir: Directory where files will be created (default: None, uses temp dir)
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
        
        # Create HTML file with embedded JavaScript
        html_path = create_html_file(js_code, temp_dir)
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
    output_path: str = "test.jpg", 
    wait_time: float = 2.0,
    keep_server_running: bool = False,
    project_dir: str = None
):
    """
    Synchronous wrapper for load_and_render_threejs.
    
    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
        keep_server_running: If True, keep the HTTP server running (default: False)
        project_dir: Directory where files will be created (default: None, uses temp dir)
    """
    asyncio.run(load_and_render_threejs(js_code, output_path, wait_time, keep_server_running, project_dir))


if __name__ == "__main__":
    # Read JavaScript code from gen_code.js
    js_code = read_js_from_file("gen_code.js")
    
    # Render and save screenshot
    # Set keep_server_running=True to view in browser, False for automated screenshot only
    render_threejs(js_code, keep_server_running=True)
