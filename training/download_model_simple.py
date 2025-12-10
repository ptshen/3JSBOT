"""
Simple script to download model from Modal using Modal shell commands.

This script provides instructions and a helper function to download the model.
"""

import os
import subprocess
import argparse


def download_via_modal_shell(output_dir: str = "./models/threejs_codellama"):
    """
    Download model using Modal shell.
    
    Instructions:
    1. Run: modal shell train_threejs_modal.py
    2. In the shell, run:
       cd /models
       tar -czf /tmp/model.tar.gz threejs_codellama_lora_merged
    3. Exit shell
    4. Download from Modal dashboard or use modal volume snapshot
    """
    print("=" * 60)
    print("Download Model from Modal")
    print("=" * 60)
    print("\nOption 1: Use Modal Shell (Recommended)")
    print("-" * 60)
    print("1. Run: modal shell train_threejs_modal.py")
    print("2. In the Modal shell, run:")
    print("   cd /models")
    print("   ls -la  # Check what's available")
    print("   tar -czf /tmp/model.tar.gz threejs_codellama_lora_merged")
    print("3. The archive will be in /tmp/model.tar.gz")
    print("4. You can download it via Modal dashboard or use volume snapshot")
    print("\nOption 2: Check Modal Dashboard")
    print("-" * 60)
    print("1. Visit: https://modal.com/apps")
    print("2. Find your app: threejs-codellama-training")
    print("3. Navigate to volumes and download files")
    print("\nOption 3: Use Modal Volume Snapshot")
    print("-" * 60)
    print("Run: modal volume snapshot threejs-codellama-models")
    print("This will create a snapshot you can download")
    print("\n" + "=" * 60)


def check_training_status():
    """Check if training has completed by looking at Modal app status."""
    print("Checking training status...")
    print("Run: modal app list")
    print("Look for 'threejs-codellama-training' app")
    print("\nIf training is still running, wait for it to complete.")
    print("The model will be saved to /models/threejs_codellama_lora_merged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download model from Modal")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models/threejs_codellama",
        help="Local directory to save the model (for reference)"
    )
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Check training status"
    )
    
    args = parser.parse_args()
    
    if args.check_status:
        check_training_status()
    else:
        download_via_modal_shell(args.output_dir)

