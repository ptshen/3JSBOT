"""
Download the trained model from Modal Volume to local filesystem.

Usage:
    python download_model.py --output-dir ./models/threejs_codellama
"""

import modal
import os
import argparse
import shutil
import tarfile
import tempfile

app = modal.App("threejs-codellama-download")

# Use the same volume where the model was saved
model_volume = modal.Volume.from_name("threejs-codellama-models", create_if_missing=False)

image = (
    modal.Image.debian_slim()
    .pip_install("transformers", "torch")
)


@app.function(
    image=image,
    volumes={"/models": model_volume},
    timeout=3600,  # 1 hour timeout
)
def create_model_archive(model_path: str = "/models/threejs_codellama_lora_merged"):
    """Create a tar archive of the model files."""
    import os
    import tarfile
    import tempfile
    
    if not os.path.exists(model_path):
        return {"error": f"Model not found at {model_path}"}
    
    # Create tar archive
    archive_path = "/tmp/model.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(model_path, arcname=os.path.basename(model_path))
    
    # Read archive into memory
    with open(archive_path, "rb") as f:
        archive_data = f.read()
    
    return {
        "success": True,
        "archive_size": len(archive_data),
        "archive_data": archive_data,
    }


@app.function(
    image=image,
    volumes={"/models": model_volume},
    timeout=3600,
)
def list_model_files():
    """List files in the model directory."""
    import os
    
    model_path = "/models/threejs_codellama_lora_merged"
    if not os.path.exists(model_path):
        # Try alternative paths
        alt_paths = [
            "/models/threejs_codellama_lora",
            "/models",
        ]
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                model_path = alt_path
                break
        else:
            return {"error": "Model not found", "available_paths": []}
    
    files = []
    for root, dirs, filenames in os.walk(model_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, model_path)
            files.append({
                "path": filepath,
                "relative_path": rel_path,
                "size": os.path.getsize(filepath)
            })
    
    return {
        "model_path": model_path,
        "files": files,
        "total_size": sum(f["size"] for f in files)
    }


@app.local_entrypoint()
def main(output_dir: str = "./models/threejs_codellama"):
    """Download model from Modal Volume to local directory."""
    print("=" * 60)
    print("Downloading Three.js CodeLlama Model from Modal")
    print("=" * 60)
    
    # First, check what files exist
    print("\nChecking model files in Modal Volume...")
    result = list_model_files.remote()
    
    if "error" in result:
        print(f"Error: {result['error']}")
        if "available_paths" in result:
            print(f"Available paths: {result['available_paths']}")
        print("\nThe model may not be fully trained yet, or the path is different.")
        print("Check the Modal dashboard or wait for training to complete.")
        return
    
    print(f"\nFound {len(result['files'])} files")
    print(f"Total size: {result['total_size'] / (1024**3):.2f} GB")
    print(f"Model location: {result['model_path']}")
    
    # Create local output directory
    local_dir = os.path.abspath(output_dir)
    os.makedirs(local_dir, exist_ok=True)
    print(f"\nDownloading to: {local_dir}")
    
    # Create archive and download
    print("\nCreating archive...")
    archive_result = create_model_archive.remote(result['model_path'])
    
    if "error" in archive_result:
        print(f"Error creating archive: {archive_result['error']}")
        return
    
    print(f"Archive size: {archive_result['archive_size'] / (1024**2):.2f} MB")
    
    # Save archive locally
    archive_path = os.path.join(local_dir, "model.tar.gz")
    print(f"\nSaving archive to {archive_path}...")
    with open(archive_path, "wb") as f:
        f.write(archive_result['archive_data'])
    
    # Extract archive
    print("Extracting archive...")
    extract_dir = os.path.join(local_dir, "threejs_codellama_lora_merged")
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=local_dir)
    
    # Remove archive
    os.remove(archive_path)
    
    print(f"\n✓ Model downloaded successfully!")
    print(f"Model location: {extract_dir}")
    print(f"\nYou can now test the model with:")
    print(f"  python training/test_model.py --model-path {extract_dir} --n 20")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download trained model from Modal")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models/threejs_codellama",
        help="Local directory to save the model"
    )
    args = parser.parse_args()
    
    with app.run():
        main(args.output_dir)
