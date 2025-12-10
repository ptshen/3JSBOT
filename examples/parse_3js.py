#!/usr/bin/env python3
"""
Script to extract JavaScript code from <script> tags in HTML files.
Specifically designed to extract three.js JavaScript code from example files.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


def extract_script_content(html_file_path: str) -> Dict[str, List[str]]:
    """
    Extract JavaScript code from <script type="module"> tags in an HTML file.
    Skips importmap and other non-module scripts.
    
    Args:
        html_file_path: Path to the HTML file
        
    Returns:
        Dictionary with keys:
            - 'scripts': List of JavaScript code strings from module script tags
            - 'script_types': List of script types (should all be 'module')
            - 'file_name': Name of the HTML file
    """
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    # Only find <script type="module"> tags, skip importmap
    script_tags = soup.find_all('script', type='module')
    
    scripts = []
    script_types = []
    
    for script_tag in script_tags:
        # Get the script type (should be 'module')
        script_type = script_tag.get('type', None)
        script_types.append(script_type)
        
        # Get the JavaScript code content using multiple methods for robustness
        script_content = None
        
        # Method 1: Try .string (works for simple cases)
        if script_tag.string:
            script_content = script_tag.string
        else:
            # Method 2: Use .get_text() to get all text content
            script_content = script_tag.get_text()
        
        # Method 3: If still empty, try decode_contents() to get raw HTML content
        if not script_content or not script_content.strip():
            try:
                script_content = script_tag.decode_contents()
            except:
                pass
        
        # Method 4: Fallback to regex extraction from raw HTML if BeautifulSoup fails
        if not script_content or not script_content.strip():
            try:
                tag_str = str(script_tag)
                match = re.search(r'<script[^>]*type=["\']module["\'][^>]*>(.*?)</script>', tag_str, re.DOTALL)
                if match:
                    script_content = match.group(1)
            except:
                pass
        
        if script_content:
            # Clean up the content (remove leading/trailing whitespace)
            script_content = script_content.strip()
            scripts.append(script_content)
        else:
            # If no content, add empty string
            scripts.append('')
    
    return {
        'scripts': scripts,
        'script_types': script_types,
        'file_name': os.path.basename(html_file_path)
    }


def process_all_html_files(directory: str = '.', output_dir: Optional[str] = None) -> List[Dict]:
    """
    Process all HTML files in the specified directory and extract JavaScript code.
    
    Args:
        directory: Directory to search for HTML files (default: current directory)
        output_dir: Optional directory to save extracted JavaScript files
        
    Returns:
        List of dictionaries containing extracted script information for each HTML file
    """
    directory_path = Path(directory)
    html_files = list(directory_path.glob('*.html'))
    
    results = []
    
    for html_file in html_files:
        print(f"Processing: {html_file.name}")
        try:
            extracted_data = extract_script_content(str(html_file))
            results.append(extracted_data)
            
            # Optionally save to output directory
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
                
                # Create a JavaScript file for each module script tag
                base_name = html_file.stem
                for idx, (script, script_type) in enumerate(zip(extracted_data['scripts'], 
                                                               extracted_data['script_types'])):
                    # Only save non-empty module scripts (skip importmaps)
                    if script and script_type == 'module':
                        output_file = output_path / f"{base_name}_module.js"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(script)
                        print(f"  Saved module script to {output_file.name}")
                        break  # Only save the first module script (usually there's only one)
        
        except Exception as e:
            print(f"Error processing {html_file.name}: {e}")
            continue
    
    return results


def print_script_summary(results: List[Dict]):
    """
    Print a summary of extracted scripts.
    
    Args:
        results: List of dictionaries from process_all_html_files
    """
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    
    total_files = len(results)
    total_scripts = sum(len(r['scripts']) for r in results)
    non_empty_scripts = sum(sum(1 for s in r['scripts'] if s.strip()) for r in results)
    
    print(f"Total HTML files processed: {total_files}")
    print(f"Total script tags found: {total_scripts}")
    print(f"Non-empty script tags: {non_empty_scripts}")
    print("\nFiles with scripts:")
    
    for result in results:
        non_empty_count = sum(1 for s in result['scripts'] if s.strip())
        if non_empty_count > 0:
            print(f"  {result['file_name']}: {non_empty_count} script(s)")


def get_threejs_code_only(html_file_path: str) -> List[str]:
    """
    Extract only three.js JavaScript code from <script type="module"> tags.
    
    Args:
        html_file_path: Path to the HTML file
        
    Returns:
        List of JavaScript code strings from module scripts (excluding empty scripts)
    """
    extracted_data = extract_script_content(html_file_path)
    
    threejs_scripts = []
    for script, script_type in zip(extracted_data['scripts'], extracted_data['script_types']):
        # Only include non-empty module scripts
        if script_type == 'module' and script.strip():
            threejs_scripts.append(script)
    
    return threejs_scripts


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract JavaScript code from <script> tags in HTML files'
    )
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default='.',
        help='Directory containing HTML files (default: current directory)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output directory to save extracted JavaScript files (optional)'
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        default=None,
        help='Process a single HTML file instead of all files'
    )
    parser.add_argument(
        '--threejs-only',
        action='store_true',
        help='Only extract three.js code from <script type="module"> tags (default behavior, skips importmaps)'
    )
    
    args = parser.parse_args()
    
    if args.file:
        # Process single file
        if os.path.exists(args.file):
            # Default behavior: extract only module scripts (skip importmaps)
            scripts = get_threejs_code_only(args.file)
            print(f"\nExtracted {len(scripts)} module script(s) from {args.file}:")
            for idx, script in enumerate(scripts):
                print(f"\n{'='*60}")
                print(f"Script {idx + 1} (type: module):")
                print(f"{'='*60}")
                print(script[:500] + "..." if len(script) > 500 else script)
        else:
            print(f"Error: File '{args.file}' not found.")
    else:
        # Process all HTML files (only extracts module scripts, skips importmaps)
        results = process_all_html_files(args.directory, args.output)
        print_script_summary(results)

