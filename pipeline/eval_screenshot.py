#!/usr/bin/env python3
"""
Evaluate how well an image matches a reference description.
Outputs a rating from 0.0 to 1.0 based on accuracy.
"""
import base64
import requests
import json
import sys
import re

def extract_rating(text: str) -> float:
    """Extract a 0-1 rating from the model's response."""
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
    
    # Fallback: Look for patterns like "0.85", "0.9", "1.0", "0.5", etc.
    # Also handle percentages like "85%" or "90%"
    patterns = [
        r'\b1\.0\b',     # Matches 1.0 exactly
        r'\b0\.\d{1,2}\b',  # Matches 0.85, 0.9, etc.
        r'\b0?\.\d+\b',  # Matches .85, etc.
        r'\b\d+%\b',     # Matches 85%, 90%, etc.
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Get the first match
            match = matches[0]
            if '%' in match:
                # Convert percentage to decimal
                return max(0.0, min(1.0, float(match.replace('%', '')) / 100.0))
            else:
                rating = float(match)
                # Ensure it's between 0 and 1
                return max(0.0, min(1.0, rating))
    
    # If no number found, look for keywords
    text_lower = text.lower()
    if 'perfect' in text_lower or 'exact' in text_lower or 'completely matches' in text_lower:
        return 1.0
    elif 'excellent' in text_lower or 'very high' in text_lower:
        return 0.9
    elif 'good' in text_lower or 'high' in text_lower:
        return 0.7
    elif 'moderate' in text_lower or 'medium' in text_lower or 'partial' in text_lower:
        return 0.5
    elif 'poor' in text_lower or 'low' in text_lower or 'minimal' in text_lower:
        return 0.3
    elif 'no match' in text_lower or 'does not match' in text_lower or 'completely different' in text_lower:
        return 0.0
    
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

if len(sys.argv) < 3:
    print("Usage: python3 eval_screenshot.py <image_path> <reference_description>")
    print("\nExample:")
    print('  python3 eval_screenshot.py image.jpg "A red bicycle leaning against a white wall"')
    sys.exit(1)

image_path = sys.argv[1]
reference_description = sys.argv[2]

# Read and encode image
try:
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')
except FileNotFoundError:
    print(f"Error: Image file not found: {image_path}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error reading image: {e}", file=sys.stderr)
    sys.exit(1)

# Create evaluation prompt
prompt = create_evaluation_prompt(reference_description)

# Send request
try:
    response = requests.post(
        "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate",
        json={
            "image": {"image_base64": base64_image},
            "prompt": prompt
        },
        timeout=120  # 2 minute timeout for evaluation
    )
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Error making request to API: {e}", file=sys.stderr)
    sys.exit(1)

# Parse response
try:
    result = response.json()
    
    if "annotation" in result:
        annotation = result["annotation"]
        
        # Extract rating
        rating = extract_rating(annotation)
        
        if rating is not None:
            # Output JSON with rating and full analysis
            output = {
                "rating": rating,
                "analysis": annotation,
                "reference_description": reference_description,
                "image_path": image_path
            }
            print(json.dumps(output, indent=2))
        else:
            # If we can't extract a rating, output the full response
            print("Warning: Could not extract rating from response", file=sys.stderr)
            output = {
                "rating": None,
                "analysis": annotation,
                "raw_response": annotation,
                "reference_description": reference_description,
                "image_path": image_path
            }
            print(json.dumps(output, indent=2))
    else:
        # Unexpected response format
        print("Error: Unexpected response format", file=sys.stderr)
        print(json.dumps(result, indent=2))
        sys.exit(1)
        
except json.JSONDecodeError as e:
    print(f"Error parsing JSON response: {e}", file=sys.stderr)
    print(f"Response text: {response.text}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error processing response: {e}", file=sys.stderr)
    print(json.dumps(result, indent=2) if 'result' in locals() else "No result available")
    sys.exit(1)
