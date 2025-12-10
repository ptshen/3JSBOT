"""
View training metrics from a previous training run.

Usage:
    python view_metrics.py --metrics-file /path/to/training_metrics.json
    # Or if metrics are in Modal volume:
    python view_metrics.py --from-modal
"""

import json
import argparse
import os


def view_metrics(metrics_file: str):
    """Display training metrics from a JSON file."""
    if not os.path.exists(metrics_file):
        print(f"Error: Metrics file not found at {metrics_file}")
        return
    
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    print("=" * 60)
    print("Training Metrics Summary")
    print("=" * 60)
    
    # Training metrics
    if "train" in metrics:
        train = metrics["train"]
        print("\n📊 Training Set Metrics:")
        print(f"  Loss: {train.get('train_loss', 'N/A'):.4f}")
        if 'train_perplexity' in train:
            print(f"  Perplexity: {train['train_perplexity']:.4f}")
        print(f"  Runtime: {train.get('train_runtime', 'N/A'):.2f}s")
        print(f"  Samples/sec: {train.get('train_samples_per_second', 'N/A'):.2f}")
        print(f"  Total Steps: {train.get('train_steps', 'N/A')}")
    
    # Validation metrics
    if "validation" in metrics:
        val = metrics["validation"]
        print("\n📊 Validation Set Metrics:")
        print(f"  Loss: {val.get('eval_loss', 'N/A'):.4f}")
        if 'eval_perplexity' in val:
            print(f"  Perplexity: {val['eval_perplexity']:.4f}")
        print(f"  Runtime: {val.get('eval_runtime', 'N/A'):.2f}s")
    
    # Training sample metrics
    if "train_sample" in metrics:
        train_sample = metrics["train_sample"]
        sample_size = train_sample.get('sample_size', 'N/A')
        print(f"\n📊 Training Set Sample Metrics (n={sample_size}):")
        print(f"  Loss: {train_sample.get('eval_loss', 'N/A'):.4f}")
        if 'eval_perplexity' in train_sample:
            print(f"  Perplexity: {train_sample['eval_perplexity']:.4f}")
    
    # Comparison
    if "train" in metrics and "validation" in metrics:
        train_loss = metrics["train"].get('train_loss', 0)
        val_loss = metrics["validation"].get('eval_loss', 0)
        if train_loss and val_loss:
            diff = val_loss - train_loss
            print("\n" + "=" * 60)
            print("📈 Overfitting Analysis:")
            print("=" * 60)
            print(f"  Train Loss: {train_loss:.4f}")
            print(f"  Val Loss: {val_loss:.4f}")
            print(f"  Difference: {diff:+.4f}")
            if diff > 0.1:
                print("  ⚠️  Warning: Large gap suggests possible overfitting")
            elif diff < -0.1:
                print("  ℹ️  Note: Validation loss lower than training (unusual)")
            else:
                print("  ✓ Gap is reasonable")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="View training metrics")
    parser.add_argument(
        "--metrics-file",
        type=str,
        default=None,
        help="Path to training_metrics.json file"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help="Path to model directory (will look for training_metrics.json inside)"
    )
    
    args = parser.parse_args()
    
    # Determine metrics file path
    if args.metrics_file:
        metrics_file = args.metrics_file
    elif args.model_dir:
        metrics_file = os.path.join(args.model_dir, "training_metrics.json")
    else:
        # Try default locations
        default_paths = [
            "./models/threejs_codellama/threejs_codellama_lora/training_metrics.json",
            "./threejs_codellama_lora/training_metrics.json",
            "/models/threejs_codellama_lora/training_metrics.json",
        ]
        metrics_file = None
        for path in default_paths:
            if os.path.exists(path):
                metrics_file = path
                break
        
        if not metrics_file:
            print("Error: Could not find training_metrics.json")
            print("Please specify --metrics-file or --model-dir")
            return
    
    view_metrics(metrics_file)


if __name__ == "__main__":
    main()

