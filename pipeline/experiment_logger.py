#!/usr/bin/env python3
"""
CSV logging utility for experiment results.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Always write to the project root so runs don’t scatter CSVs inside workspaces
CSV_PATH = str(Path(__file__).resolve().parent.parent / "experiment_results.csv")
CSV_HEADERS = [
    "timestamp", "experiment_condition", "example_idx", "prompt",
    "execution_score", "execution_status", "visual_score", "final_score",
    "output_path", "error_msg", "iterations"
]


def ensure_csv_headers(csv_path: str) -> None:
    """Ensure CSV file exists with headers."""
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def log_experiment_result(
    experiment_condition: str,
    example_idx: int,
    prompt: str,
    execution_score: float,
    execution_status: str,
    visual_score: float,
    final_score: float,
    output_path: str,
    error_msg: str = "",
    iterations: int = 1,
    csv_path: str = CSV_PATH
) -> None:
    """
    Log a single experiment result to CSV.

    Args:
        experiment_condition: String identifier for the experiment (e.g., 'baseline', 'fewshot')
        example_idx: Which test case this is (0, 1, 2, etc.)
        prompt: The input description text
        execution_score: Float (1.0 clean, 0.5 runtime errors, 0.25 critical errors, 0.0 crashed)
        execution_status: String ("clean", "runtime_errors", "critical_errors", "crashed")
        visual_score: Float from VLM evaluation
        final_score: Weighted composite score
        output_path: Path to the output directory containing results
        error_msg: Error message if failed (empty string if success)
        iterations: Number of self-refinement iterations
        csv_path: Path to CSV file (default: experiment_results.csv)
    """
    # Ensure CSV exists with headers
    ensure_csv_headers(csv_path)

    # Create row data
    timestamp = datetime.now().isoformat()
    row = [
        timestamp,
        experiment_condition,
        str(example_idx),
        prompt,
        str(execution_score),
        execution_status,
        str(visual_score),
        str(final_score),
        output_path,
        error_msg,
        str(iterations)
    ]

    # Append row immediately with flush
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.flush()  # Ensure data is written immediately


def get_relative_path(full_path: str, base_dir: str = None) -> str:
    """Convert full path to relative path from base directory."""
    if base_dir is None:
        # Default to project root
        base_dir = Path(__file__).parent.parent

    try:
        return str(Path(full_path).relative_to(base_dir))
    except ValueError:
        # If can't make relative, return as-is
        return full_path


if __name__ == "__main__":
    # Test the logging function
    log_experiment_result(
        experiment_condition="test_baseline",
        example_idx=0,
        prompt="A red cube",
        execution_score=1.0,
        execution_status="clean",
        visual_score=0.8,
        final_score=0.94,
        output_path="evaluation_outputs/test_001",
        error_msg="",
        iterations=1
    )
    print(f"Test result logged to {CSV_FILE}")
