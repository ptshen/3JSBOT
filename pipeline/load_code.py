"""This file loads three.js code in a browser environment using Playwright and renders the animation."""

import asyncio
from playwright.async_api import async_playwright
import os
import json


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


async def load_and_render_threejs(js_code: str, output_path: str = "test.jpg", wait_time: float = 2.0):
    """
    Load three.js JavaScript code in a browser environment using Playwright,
    render the animation, and take a screenshot.
    
    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
    """
    # Escape JavaScript code for embedding in HTML (using JSON encoding for safety)
    js_code_escaped = json.dumps(js_code)
    
    # Create HTML page with three.js library and user's code
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
        #canvas-container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}
        #myCanvas {{
            width: 100%;
            height: 100%;
        }}
        canvas {{
            display: block;
        }}
        body > canvas {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw !important;
            height: 100vh !important;
        }}
    </style>
</head>
<body>
    <div id="canvas-container">
        <canvas id="myCanvas"></canvas>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // Convert ES6 import to global THREE usage
        // Replace import statements and use global THREE
        (function() {{
            let userCode = {js_code_escaped};
            // Remove ES6 import statements and use global THREE
            userCode = userCode.replace(/import\\s+.*?from\\s+['"]three['"];?/g, '');
            // Execute the user's code
            try {{
                eval(userCode);
                
                // Post-process: If renderer created its own canvas and appended to body,
                // ensure it's properly styled and visible
                // Use requestAnimationFrame to ensure DOM is updated
                requestAnimationFrame(() => {{
                    requestAnimationFrame(() => {{
                        const myCanvas = document.getElementById('myCanvas');
                        const allCanvases = document.querySelectorAll('canvas');
                        const container = document.getElementById('canvas-container');
                        
                        // Find canvas that's not myCanvas (created by renderer)
                        let rendererCanvas = null;
                        for (let canvas of allCanvases) {{
                            if (canvas.id !== 'myCanvas') {{
                                // Check if this canvas has WebGL context (created by renderer)
                                const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                                if (gl !== null) {{
                                    rendererCanvas = canvas;
                                    break;
                                }}
                            }}
                        }}
                        
                        if (rendererCanvas) {{
                            // Hide the unused myCanvas
                            if (myCanvas) {{
                                myCanvas.style.display = 'none';
                            }}
                            
                            // Move renderer canvas to container if not already there
                            if (container && !container.contains(rendererCanvas)) {{
                                container.appendChild(rendererCanvas);
                            }}
                            
                            // Ensure canvas takes full size and is visible
                            rendererCanvas.style.width = '100%';
                            rendererCanvas.style.height = '100%';
                            rendererCanvas.style.display = 'block';
                            rendererCanvas.style.position = 'absolute';
                            rendererCanvas.style.top = '0';
                            rendererCanvas.style.left = '0';
                            
                            // Ensure container is positioned correctly
                            container.style.position = 'relative';
                            
                            // Resize renderer to match viewport if needed
                            if (window.renderer && typeof window.renderer.setSize === 'function') {{
                                window.renderer.setSize(window.innerWidth, window.innerHeight);
                            }}
                        }}
                        
                        // Signal that rendering has started (after post-processing)
                        window.threeJsRendered = true;
                    }});
                }});
            }} catch (e) {{
                console.error('Error executing three.js code:', e);
                window.threeJsRendered = true; // Still signal to continue
            }}
        }})();
    </script>
</body>
</html>"""
    
    # Write HTML to temporary file
    temp_html = "temp_threejs.html"
    with open(temp_html, "w") as f:
        f.write(html_content)
    
    try:
        # Launch browser with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set viewport size
            await page.set_viewport_size({'width': 1920, 'height': 1080})
            
            # Load the HTML file
            file_path = os.path.abspath(temp_html)
            await page.goto(f'file://{file_path}', wait_until='networkidle')
            
            # Wait for three.js library to load
            await page.wait_for_function('typeof THREE !== "undefined"', timeout=10000)
            
            # Wait for the user's code to execute and rendering to start
            await page.wait_for_function('window.threeJsRendered === true', timeout=10000)
            
            # Additional small wait to ensure post-processing completes
            await asyncio.sleep(0.2)
            
            # Wait for canvas element and WebGL context to be created
            # Handle both cases: code using existing myCanvas or code creating its own canvas
            await page.wait_for_function('''
                () => {{
                    // First check if myCanvas has WebGL context (for code that uses existing canvas)
                    const myCanvas = document.getElementById('myCanvas');
                    if (myCanvas) {{
                        const gl = myCanvas.getContext('webgl') || myCanvas.getContext('webgl2');
                        if (gl !== null) return true;
                    }}
                    
                    // If myCanvas doesn't have WebGL, check for any canvas with WebGL context
                    // (for code that creates its own canvas via renderer.domElement)
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {{
                        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                        if (gl !== null) {{
                            // Ensure the canvas is visible and properly sized
                            if (canvas.width > 0 && canvas.height > 0) {{
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
            ''', timeout=10000)
            
            # Wait for multiple animation frames to ensure rendering has occurred
            # This ensures the animation loop has had time to render at least a few frames
            await page.evaluate('''
                () => new Promise((resolve) => {{
                    let frames = 0;
                    const targetFrames = 10; // Wait for 10 animation frames
                    function checkFrame() {{
                        requestAnimationFrame(() => {{
                            frames++;
                            if (frames >= targetFrames) {{
                                resolve();
                            }} else {{
                                checkFrame();
                            }}
                        }});
                    }}
                    checkFrame();
                }})
            ''')
            
            # Additional wait to ensure animation has fully rendered
            await asyncio.sleep(wait_time)
            
            # Verify canvas is visible before screenshot
            await page.wait_for_function('''
                () => {{
                    const allCanvases = document.querySelectorAll('canvas');
                    for (let canvas of allCanvases) {{
                        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                        if (gl !== null && canvas.width > 0 && canvas.height > 0) {{
                            const rect = canvas.getBoundingClientRect();
                            const style = window.getComputedStyle(canvas);
                            // Check if canvas is visible
                            if (rect.width > 0 && rect.height > 0 && 
                                style.display !== 'none' && 
                                style.visibility !== 'hidden' &&
                                style.opacity !== '0') {{
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
            ''', timeout=5000)
            
            # Take screenshot
            await page.screenshot(path=output_path, type='jpeg', quality=90, full_page=True)
            
            print(f"Screenshot saved to {output_path}")
            
            # Close browser
            await browser.close()
        
    finally:
        # Clean up temporary HTML file
        if os.path.exists(temp_html):
            os.remove(temp_html)


def render_threejs(js_code: str, output_path: str = "test.jpg", wait_time: float = 2.0):
    """
    Synchronous wrapper for load_and_render_threejs.
    
    Args:
        js_code: The JavaScript code containing three.js animation logic
        output_path: Path where the screenshot will be saved (default: "test.jpg")
        wait_time: Time in seconds to wait for animation to render (default: 2.0)
    """
    asyncio.run(load_and_render_threejs(js_code, output_path, wait_time))


if __name__ == "__main__":
    # Read JavaScript code from gen_code.js
    js_code = read_js_from_file("gen_code.js")
    
    # Render and save screenshot
    render_threejs(js_code)
