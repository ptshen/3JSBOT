#!/usr/bin/env python3
"""
Send a screenshot to Anthropic's Claude to generate a prompt that could create the three.js output.
"""

import os
import base64
import sys
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def encode_image(image_path: str) -> tuple[str, str]:
    """
    Encode an image to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Tuple of (base64_encoded_data, media_type)
    """
    with open(image_path, "rb") as image_file:
        image_data = base64.standard_b64encode(image_file.read()).decode("utf-8")

    # Determine media type from file extension
    ext = Path(image_path).suffix.lower()
    media_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    media_type = media_type_map.get(ext, 'image/jpeg')

    return image_data, media_type


def get_prompt_from_screenshot(screenshot_path: str, api_key: str = None) -> str:
    """
    Send a screenshot to Claude and ask it to generate a prompt.

    Args:
        screenshot_path: Path to the screenshot file
        api_key: Anthropic API key (optional, will use ANTHROPIC_API_KEY env var if not provided)

    Returns:
        The generated prompt suggestion from Claude
    """
    # Initialize the Anthropic client
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    # Encode the image
    image_data, media_type = encode_image(screenshot_path)

    # Create the message
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "You are a world class 3D artist. Given this screenshot of three.js generated output, write a detailed description of the scene."
                    }
                ],
            }
        ],
    )

    # Extract the text response
    return message.content[0].text


def main():
    """Main function to process all screenshots in the directory."""
    screenshots_dir = Path(__file__).parent / "screenshots"

    if not screenshots_dir.exists():
        print(f"Error: Screenshots directory not found at {screenshots_dir}")
        sys.exit(1)

    # Get all .jpg files in the screenshots directory
    screenshot_files = sorted(screenshots_dir.glob("*.jpg"))

    if not screenshot_files:
        print("No .jpg files found in the screenshots directory.")
        sys.exit(1)

    print(f"Found {len(screenshot_files)} screenshots to process.")
    print("="*80)

    successful = 0
    failed = 0
    skipped = 0

    for i, screenshot_path in enumerate(screenshot_files, 1):
        screenshot_filename = screenshot_path.name
        output_filename = screenshot_path.stem + ".md"
        output_path = screenshots_dir / output_filename

        # Skip if .md file already exists
        if output_path.exists():
            print(f"[{i}/{len(screenshot_files)}] Skipping {screenshot_filename} (already processed)")
            skipped += 1
            continue

        print(f"[{i}/{len(screenshot_files)}] Processing {screenshot_filename}...")

        try:
            prompt = get_prompt_from_screenshot(str(screenshot_path))

            # Save to markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {screenshot_filename}\n\n")
                f.write(prompt)
                f.write("\n")

            print(f"  ✓ Saved to {output_filename}")
            successful += 1

        except Exception as e:
            print(f"  ✗ Error processing {screenshot_filename}: {e}")
            failed += 1

    print("="*80)
    print(f"Processing complete!")
    print(f"  Successful: {successful}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(screenshot_files)}")


if __name__ == "__main__":
    main()
