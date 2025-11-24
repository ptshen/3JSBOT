"""This file is for generating the code for the three.js animation."""

import requests
import re
import json
import sys


def extract_code_from_markdown(content: str) -> str:
    """
    Extract JavaScript code from markdown code blocks.
    
    Args:
        content: The content string that may contain markdown code blocks
        
    Returns:
        The extracted code without markdown formatting
    """
    # Pattern to match code blocks: ```javascript ... ``` or ```js ... ``` or ``` ... ```
    pattern = r'```(?:javascript|js)?\s*\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no code block found, return the content as-is (might already be code)
    return content.strip()


def generate_threejs_code(prompt: str, output_file: str = "gen_code.js", api_url: str = None) -> str:
    """
    Generate three.js code by querying the API and save it to a file.
    
    Args:
        prompt: The prompt to send to the API
        output_file: Path to the output file (default: "gen_code.js")
        api_url: The API endpoint URL (default: uses the provided endpoint)
    
    Returns:
        The generated JavaScript code
    """
    if api_url is None:
        api_url = "https://patbshen--ollama-ollama-serve.modal.run/v1/chat/completions"
    
    # Prepare the request payload
    payload = {
        "model": "codellama:7b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Make the API request
        print(f"Querying API with prompt: {prompt}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Extract the code from the response
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            code = extract_code_from_markdown(content)
            
            # Write the code to the output file
            with open(output_file, "w") as f:
                f.write(code)
            
            print(f"Generated code saved to {output_file}")
            return code
        else:
            raise ValueError("No choices found in API response")
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        raise
    except (KeyError, ValueError) as e:
        print(f"Error parsing API response: {e}")
        print(f"Response: {json.dumps(data, indent=2)}")
        raise


if __name__ == "__main__":
    # Get prompt from command-line argument
    if len(sys.argv) < 2:
        print("Usage: python3 generate_code.py <prompt>")
        print("Example: python3 generate_code.py 'generate three.js code for a rotating sphere'")
        sys.exit(1)
    
    # Join all arguments after the script name to allow prompts with spaces
    prompt = " ".join(sys.argv[1:])
    generate_threejs_code(prompt)
