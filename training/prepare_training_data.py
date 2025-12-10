"""
Prepare training data by pairing descriptions (.md files) with Three.js code (.js files).

This script:
1. Loads all .md descriptions from image_to_prompt/screenshots
2. Matches them with corresponding .js files from training/extracted_scripts
3. Creates training pairs (description, code) for fine-tuning CodeLlama
4. Saves training_data.json for use in training
"""

import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict


def prepare_training_data(
    screenshots_dir: str,
    scripts_dir: str,
    output_file: str = "training_data.json"
):
    """
    Create training dataset by pairing descriptions with code files.
    
    Args:
        screenshots_dir: Directory containing .md description files
        scripts_dir: Directory containing .js code files (with _module.js suffix)
        output_file: Path to save training data JSON
    """
    print("=" * 60)
    print("Preparing Training Data for CodeLlama")
    print("=" * 60)
    
    # Load all .md files
    md_files = glob.glob(os.path.join(screenshots_dir, "*.md"))
    print(f"\nFound {len(md_files)} description files")
    
    # Create mapping: base_name -> (md_path, js_path)
    pairs = {}
    
    for md_file in md_files:
        base_name = Path(md_file).stem  # e.g., "webgl_animation_skinning_ik"
        js_file = os.path.join(scripts_dir, f"{base_name}_module.js")
        
        if os.path.exists(js_file):
            pairs[base_name] = (md_file, js_file)
        else:
            print(f"  ⚠ Warning: No matching JS file for {base_name}")
    
    print(f"Found {len(pairs)} matching pairs")
    
    # Load descriptions and code
    training_data = []
    
    for i, (base_name, (md_path, js_path)) in enumerate(sorted(pairs.items()), 1):
        print(f"[{i}/{len(pairs)}] Processing {base_name}...")
        
        try:
            # Load description
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Skip the first line if it's just the filename
                lines = content.split('\n')
                if len(lines) > 1 and lines[0].startswith('#'):
                    description = '\n'.join(lines[1:]).strip()
                else:
                    description = content
            
            # Load code
            with open(js_path, 'r', encoding='utf-8') as f:
                code = f.read().strip()
            
            # Create training pair
            training_data.append({
                'description': description,
                'code': code,
                'filename': base_name,
                'md_file': os.path.basename(md_path),
                'js_file': os.path.basename(js_path)
            })
            
            print(f"  ✓ Loaded {len(description)} chars description, {len(code)} chars code")
            
        except Exception as e:
            print(f"  ✗ Error processing {base_name}: {e}")
            continue
    
    # Save training data
    print(f"\n\nSaving training data to {output_file}...")
    print(f"Total examples: {len(training_data)}")
    
    # Handle output path: if absolute, use as-is; if relative, join with script directory
    if os.path.isabs(output_file):
        output_path = output_file
    else:
        # If output_file starts with "training/", remove that prefix since we're already in training/
        if output_file.startswith("training/"):
            output_file = output_file[len("training/"):]
        output_path = os.path.join(os.path.dirname(__file__), output_file)
    
    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Training data saved to {output_path}")
    
    # Print statistics
    avg_desc_len = sum(len(d['description']) for d in training_data) / len(training_data) if training_data else 0
    avg_code_len = sum(len(d['code']) for d in training_data) / len(training_data) if training_data else 0
    print(f"\nStatistics:")
    print(f"  Average description length: {avg_desc_len:.0f} characters")
    print(f"  Average code length: {avg_code_len:.0f} characters")
    
    return training_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data for CodeLlama fine-tuning")
    parser.add_argument("--screenshots-dir", type=str, 
                       default=os.path.join(os.path.dirname(__file__), '..', 'image_to_prompt', 'screenshots'),
                       help="Directory containing .md files")
    parser.add_argument("--scripts-dir", type=str,
                       default=os.path.join(os.path.dirname(__file__), 'extracted_scripts'),
                       help="Directory containing .js files")
    parser.add_argument("--output", type=str, default="training_data.json",
                       help="Output JSON file for training data")
    
    args = parser.parse_args()
    
    prepare_training_data(
        args.screenshots_dir,
        args.scripts_dir,
        args.output
    )
