#!/usr/bin/env python3
"""
Generate a "Taxonomy of Failure" table from experiment_results.csv.

Flow:
1) Read experiment_results.csv
2) Add code_full_path and image_full_path from output_path + example_idx
   - prefer .html if it exists, else .js
3) Assign failure_type:
   - System Error (API/Network): error_msg contains any of ["401", "Unauthorized", "Connection", "Timeout", "Rate limit"]
   - Syntax Error (Model Failed to Code): execution_score == 0 and NOT System Error
   - Visual/Spatial Failure: execution_score == 1 and visual_score < 0.5
     -> further classified by analyze_failure(code_path, prompt) into:
        ["Spatial Hallucination", "Conceptual Failure", "Faithfulness Error"]
   - Else: "None"
4) Save failure_analysis_tagged.csv
5) Print a summary markdown table

Note: analyze_failure currently returns "Unknown" as a placeholder; to enable LLM
analysis, implement the call to your model of choice (e.g., GPT-4o, Claude) and
replace the stub.
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "experiment_results.csv"
EVAL_ROOT = ROOT / "evaluation_outputs"
OUTPUT_CSV = ROOT / "failure_analysis_tagged.csv"

SYSTEM_ERROR_PATTERNS = [
    "401", "unauthorized", "connection", "timeout", "rate limit"
]


def file_exists(p: Path) -> bool:
    try:
        return p.exists()
    except OSError:
        return False


def build_code_path(base: str, idx: str) -> str:
    """
    Prefer .html if exists, else .js; if neither, return empty string.
    """
    base_path = Path(base).expanduser()
    html_path = base_path / f"{int(idx):03d}_code.html"
    js_path = base_path / f"{int(idx):03d}_code.js"
    if file_exists(html_path):
        return str(html_path)
    if file_exists(js_path):
        return str(js_path)
    return ""


def build_image_path(base: str, idx: str) -> str:
    """
    Build .png path; return empty string if not found.
    """
    base_path = Path(base).expanduser()
    png_path = base_path / f"{int(idx):03d}_screenshot.png"
    jpg_path = base_path / f"{int(idx):03d}_screenshot.jpg"
    if file_exists(png_path):
        return str(png_path)
    if file_exists(jpg_path):
        return str(jpg_path)
    return ""


def is_system_error(err: str) -> bool:
    err_lower = str(err or "").lower()
    return any(pat in err_lower for pat in SYSTEM_ERROR_PATTERNS)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")


def safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def derive_condition(data: Dict, run_dir: Path) -> str:
    """
    Try to build a stable experiment_condition from the run metadata.
    Priority:
      1) explicit experiment_condition
      2) experiment name
      3) model name
      4) folder stem before timestamp
    """
    meta = data.get("metadata", {}) if isinstance(data, dict) else {}
    candidates = [
        data.get("experiment_condition"),
        meta.get("experiment_condition"),
        data.get("experiment"),
        meta.get("experiment"),
    ]
    cond = next((c for c in candidates if c), None)

    model = data.get("model") or meta.get("model")
    if model:
        model_slug = slugify(model)
        if cond:
            cond = f"{model_slug}_{slugify(cond)}"
        else:
            cond = model_slug
    elif cond:
        cond = slugify(cond)

    if not cond:
        name = run_dir.name
        cond = name.split("_2025")[0] or name

    return cond


def load_results_from_eval_root(eval_root: Path, include_archived: bool) -> pd.DataFrame:
    rows: List[Dict] = []
    search_roots = [eval_root]
    if include_archived:
        search_roots.append(eval_root / "archived")

    for root in search_roots:
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            if "results.json" not in filenames:
                continue

            run_dir = Path(dirpath)
            try:
                with open(run_dir / "results.json", "r") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            condition = derive_condition(data, run_dir)
            results = data.get("results", [])
            for r in results:
                error_list = r.get("js_errors") or r.get("errors") or []
                if isinstance(error_list, list):
                    error_msg = "; ".join(map(str, error_list))
                else:
                    error_msg = str(error_list or r.get("error") or "")

                rows.append(
                    {
                        "timestamp": data.get("timestamp")
                        or data.get("metadata", {}).get("timestamp"),
                        "experiment_condition": condition,
                        "example_idx": r.get("idx"),
                        "prompt": r.get("description", ""),
                        "execution_score": safe_float(r.get("execution_score")),
                        "execution_status": r.get("execution_status", ""),
                        "visual_score": safe_float(
                            r.get("visual_score", r.get("visual_accuracy"))
                        ),
                        "final_score": safe_float(r.get("final_score")),
                        "output_path": str(run_dir),
                        "error_msg": error_msg,
                        "iterations": r.get("iterations", ""),
                    }
                )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def analyze_failure(code_path: str, prompt: str) -> str:
    """
    Placeholder for LLM-based analysis.
    Intended behavior: read code file, send code + prompt to an LLM with:
      "The user asked for: '{prompt}'. The code compiles, but the visual score is low.
       Look at the Three.js code. Is this a Spatial Hallucination (objects floating/detached),
       a Conceptual Failure (wrong object entirely), or a Faithfulness Error (ignored constraints)?
       Return ONLY the category name."
    Returns: "Spatial Hallucination" | "Conceptual Failure" | "Faithfulness Error" | "Unknown"
    """
    # Stub: no remote call in this offline script
    return "Unknown"


def assign_failure_type(row) -> str:
    err = row.get("error_msg", "") or ""
    exec_score = safe_float(row.get("execution_score", 0))
    visual_score = safe_float(row.get("visual_score", 0))

    if is_system_error(err):
        return "System Error"
    if exec_score == 0:
        return "Syntax Error"
    if exec_score == 1 and visual_score < 0.5:
        return "Visual/Spatial Failure"
    return "None"


def main(args):
    frames = []
    if args.csv and Path(args.csv).exists():
        frames.append(pd.read_csv(args.csv))

    eval_df = load_results_from_eval_root(args.eval_root, args.include_archived)
    if not eval_df.empty:
        frames.append(eval_df)

    if not frames:
        raise SystemExit("No data found in CSV or evaluation_outputs.")

    df = pd.concat(frames, ignore_index=True)

    # Build paths
    df["code_full_path"] = df.apply(
        lambda r: build_code_path(str(r["output_path"]), str(r["example_idx"])), axis=1
    )
    df["image_full_path"] = df.apply(
        lambda r: build_image_path(str(r["output_path"]), str(r["example_idx"])), axis=1
    )

    # Tag failure_type
    df["failure_type"] = df.apply(assign_failure_type, axis=1)

    # For visual/spatial failures, call analyzer (stubbed)
    df["failure_subtype"] = ""
    mask_visual = df["failure_type"] == "Visual/Spatial Failure"
    for i, r in df[mask_visual].iterrows():
        code_path = r["code_full_path"]
        prompt = r.get("prompt", "")
        if code_path and file_exists(Path(code_path)):
            subtype = analyze_failure(code_path, prompt)
        else:
            subtype = "File Missing"
        df.at[i, "failure_subtype"] = subtype

    # Save
    df.to_csv(args.output, index=False)

    # Summary table
    summary = []
    for cond, group in df.groupby("experiment_condition"):
        sys_err = (group["failure_type"] == "System Error").sum()
        syn_err = (group["failure_type"] == "Syntax Error").sum()
        visual_any = (group["failure_type"] == "Visual/Spatial Failure").sum()
        spatial = (
            (group["failure_type"] == "Visual/Spatial Failure")
            & (group["failure_subtype"] == "Spatial Hallucination")
        ).sum()
        conceptual = (
            (group["failure_type"] == "Visual/Spatial Failure")
            & (group["failure_subtype"] == "Conceptual Failure")
        ).sum()
        faithfulness = (
            (group["failure_type"] == "Visual/Spatial Failure")
            & (group["failure_subtype"] == "Faithfulness Error")
        ).sum()
        other_visual = max(visual_any - spatial - conceptual - faithfulness, 0)
        summary.append(
            (
                cond,
                sys_err,
                syn_err,
                visual_any,
                spatial,
                conceptual,
                faithfulness,
                other_visual,
            )
        )

    # Print markdown table
    print(
        "| Experiment Condition | System Errors | Syntax Errors | Visual/Spatial (any) | Spatial Hallucinations | Conceptual Failures | Faithfulness Errors | Other/Unknown Visual |"
    )
    print(
        "|----------------------|---------------|---------------|----------------------|------------------------|---------------------|---------------------|----------------------|"
    )
    for (
        cond,
        sys_err,
        syn_err,
        visual_any,
        spatial,
        conceptual,
        faithfulness,
        other_visual,
    ) in summary:
        print(
            f"| {cond} | {sys_err} | {syn_err} | {visual_any} | {spatial} | {conceptual} | {faithfulness} | {other_visual} |"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Taxonomy of Failure analysis.")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="Optional path to a precomputed experiment_results.csv")
    parser.add_argument(
        "--eval-root",
        type=Path,
        default=EVAL_ROOT,
        help="Root folder containing evaluation runs (each with results.json)",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Also read evaluation_outputs/archived runs",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Where to save failure_analysis_tagged.csv")
    args = parser.parse_args()
    main(args)

