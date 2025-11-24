"""This file loads three.js code in a browser environment using Playwright and renders the animation."""

import asyncio
from playwright.async_api import async_playwright
import os
import json


def read_js_from_file(file_path: str = "input_gen_code.js") -> str:
    """
    Read JavaScript code from a file.
    
    Args:
        file_path: Path to the JavaScript file (default: "input_gen_code.js")
    
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
        }}
        #myCanvas {{
            width: 100%;
            height: 100%;
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
                // Signal that rendering has started
                window.threeJsRendered = true;
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
            
            # Wait for canvas element and WebGL context to be created
            await page.wait_for_function('''
                () => {{
                    const canvas = document.getElementById('myCanvas');
                    if (!canvas) return false;
                    const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                    return gl !== null;
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
            
            # Take screenshot
            await page.screenshot(path=output_path, type='jpeg', quality=90)
            
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
    # Read JavaScript code from input_gen_code.js
    js_code = read_js_from_file("input_gen_code.js")
    
    # Render and save screenshot
    render_threejs(js_code)

