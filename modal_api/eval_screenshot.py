#!/usr/bin/env python3
import base64
import requests
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python3 annotate_image.py <image_path> [prompt]")
    sys.exit(1)

image_path = sys.argv[1]
prompt = sys.argv[2] if len(sys.argv) > 2 else "Describe this image in detail"

# Read and encode image
with open(image_path, "rb") as f:
    base64_image = base64.b64encode(f.read()).decode('utf-8')

# Send request
response = requests.post(
    "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate",
    json={
        "image": {"image_base64": base64_image},
        "prompt": prompt
    }
)

# Print annotation
result = response.json()
if "annotation" in result:
    print(result["annotation"])
else:
    print(json.dumps(result, indent=2))
