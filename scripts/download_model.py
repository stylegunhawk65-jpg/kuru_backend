"""Download utility for Qwen2.5-3B-Instruct to a persistent local cache outside Git."""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from huggingface_hub import snapshot_download

# Default local storage path outside OneDrive sync if possible, or in models/
DEFAULT_MODEL_DIR = os.environ.get(
    "LOCAL_MODEL_PATH",
    os.path.join(os.path.expanduser("~"), ".cache", "kuru_models", "Qwen2.5-3B-Instruct"),
)


def verify_disk_space(target_path: str, required_gb: float = 8.0) -> None:
    """Ensure sufficient disk storage before initiating multi-gigabyte download."""
    # Get root/drive of target path
    drive = os.path.splitdrive(os.path.abspath(target_path))[0] or "/"
    total, used, free = shutil.disk_usage(drive)
    free_gb = free / (1024 ** 3)
    print(f"[*] Target storage drive: {drive} | Available disk space: {free_gb:.2f} GB")

    if free_gb < required_gb:
        raise OSError(
            f"Insufficient disk space on {drive}: {free_gb:.2f} GB free, but {required_gb:.1f} GB required."
        )


def download_qwen_model(
    repo_id: str = "Qwen/Qwen2.5-3B-Instruct",
    output_dir: str = DEFAULT_MODEL_DIR,
) -> str:
    """Download Qwen2.5-3B-Instruct model snapshot with progress tracking and validation."""
    print("=" * 70)
    print("  KURU BACKEND — LOCAL MODEL DOWNLOAD UTILITY")
    print(f"  Repository ID:    {repo_id}")
    print(f"  Target Directory: {output_dir}")
    print("=" * 70)

    verify_disk_space(output_dir, required_gb=8.0)
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.perf_counter()
    print("\n[*] Starting snapshot download from Hugging Face official repository...")

    downloaded_path = snapshot_download(
        repo_id=repo_id,
        local_dir=output_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
    )

    elapsed = time.perf_counter() - start_time

    # Validate essential files
    required_files = ["config.json", "tokenizer_config.json"]
    for req in required_files:
        check_file = os.path.join(downloaded_path, req)
        if not os.path.isfile(check_file):
            raise FileNotFoundError(f"Missing required model artifact: {check_file}")

    # Calculate total size on disk
    total_bytes = 0
    file_count = 0
    for root, _, files in os.walk(downloaded_path):
        for f in files:
            fp = os.path.join(root, f)
            total_bytes += os.path.getsize(fp)
            file_count += 1

    size_gb = total_bytes / (1024 ** 3)

    print("\n" + "=" * 70)
    print("  DOWNLOAD COMPLETED SUCCESSFULLY")
    print(f"  Model Path:       {downloaded_path}")
    print(f"  Total Files:      {file_count}")
    print(f"  Size on Disk:     {size_gb:.2f} GB")
    print(f"  Download Time:    {elapsed:.1f} seconds")
    print("=" * 70)
    print(f"\nTo configure Kuru Backend to use this local path, set in .env:")
    print(f"LOCAL_MODEL_PATH=\"{downloaded_path}\"")
    print(f"LLM_PROVIDER=\"local\"\n")

    return downloaded_path


def main():
    parser = argparse.ArgumentParser(description="Download Qwen2.5-3B-Instruct weights")
    parser.add_argument("--repo-id", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    download_qwen_model(repo_id=args.repo_id, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
