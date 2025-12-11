#!/usr/bin/env python3
"""
Re-run Qwen evaluation on an existing evaluation run's screenshots.
"""

import argparse
import base64
import json
import os
import re
import requests
from pathlib import Path

DEFAULT_EVAL_API = "https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate"


def get_direct_rating(screenshot_path: str, reference: str, api_url: str) -> tuple[float, str]:
    """Get direct rating from Qwen-VL with lenient partial-credit scoring."""
    try:
        with open(screenshot_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = f"""Rate how well this 3D rendered image captures elements from the description.

DESCRIPTION:
{reference[:500]}

SCORING GUIDE (give partial credit):
- 0.0: Completely black/empty, or no recognizable 3D content
- 0.2: Has some 3D shapes but wrong type/color
- 0.4: Has correct basic shapes (spheres, cubes, etc.) but wrong arrangement
- 0.6: Correct shapes AND colors, but missing environment/lighting details
- 0.8: Good match - main objects correct with some lighting/composition
- 1.0: Excellent match - objects, colors, arrangement, and lighting all match

Focus on: Are the RIGHT TYPES of shapes present? Are colors approximately correct?
Ignore: Complex environments, exact positioning, advanced lighting effects.

Respond with ONLY a number between 0.0 and 1.0."""

        response = requests.post(
            api_url,
            json={"image": {"image_base64": base64_image}, "prompt": prompt},
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if "annotation" in result:
            text = result["annotation"]
            match = re.search(r'([0-9]*\.?[0-9]+)', text)
            if match:
                rating = float(match.group(1))
                return max(0.0, min(1.0, rating)), text
        return 0.0, "Could not extract rating"
    except Exception as e:
        return 0.0, f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Re-run Qwen eval on existing screenshots")
    parser.add_argument("run_dir", help="Path to existing run directory")
    parser.add_argument("--eval-api", default=DEFAULT_EVAL_API)
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    examples_dir = run_dir / "examples"
    
    if not examples_dir.exists():
        print(f"Error: {examples_dir} not found")
        return
    
    print(f"Re-evaluating screenshots in: {run_dir}")
    print(f"API: {args.eval_api}\n")
    
    results = []
    
    for example_dir in sorted(examples_dir.iterdir()):
        if not example_dir.is_dir():
            continue
        
        screenshot = example_dir / "screenshot.jpg"
        description_file = example_dir / "description.txt"
        eval_file = example_dir / "evaluation.json"
        
        if not screenshot.exists():
            print(f"[{example_dir.name}] No screenshot, skipping")
            continue
        
        # Load description
        description = ""
        if description_file.exists():
            description = description_file.read_text()
        
        # Load existing eval
        old_eval = {}
        if eval_file.exists():
            old_eval = json.loads(eval_file.read_text())
        
        print(f"[{example_dir.name}] Evaluating...", end=" ", flush=True)
        
        rating, response = get_direct_rating(str(screenshot), description, args.eval_api)
        
        # Update eval
        exec_score = old_eval.get("execution_score", 0.5)
        new_final = 0.7 * exec_score + 0.3 * rating
        
        print(f"Qwen: {rating:.3f} | Final: {new_final:.3f} (was {old_eval.get('final_score', 'N/A')})")
        
        # Save updated eval
        old_eval["visual_accuracy_qwen"] = rating
        old_eval["final_score_qwen"] = new_final
        old_eval["qwen_response"] = response
        
        with open(eval_file, "w") as f:
            json.dump(old_eval, f, indent=2)
        
        results.append({
            "idx": example_dir.name,
            "exec": exec_score,
            "visual_qwen": rating,
            "final_qwen": new_final,
        })
    
    # Summary
    if results:
        avg_visual = sum(r["visual_qwen"] for r in results) / len(results)
        avg_final = sum(r["final_qwen"] for r in results) / len(results)
        
        print(f"\n{'='*50}")
        print(f"SUMMARY ({len(results)} examples)")
        print(f"{'='*50}")
        print(f"Avg Visual (Qwen): {avg_visual:.3f}")
        print(f"Avg Final Score:   {avg_final:.3f}")


if __name__ == "__main__":
    main()
