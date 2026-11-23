"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Robust downloader for CHB-MIT EDF records specified in data/manifest.csv.
         Prioritizes seizure files first, followed by seizure-free control files.
AI-assisted: yes
"""

import sys
import os
import time
import urllib.request
import urllib.parse
from pathlib import Path
import pandas as pd

PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJ_ROOT))

from src.config import MANIFEST_PATH, RAW_DATA_DIR

BASE_URLS = [
    "https://physionet-open.s3.amazonaws.com/chbmit/1.0.0/",
    "https://physionet.org/files/chbmit/1.0.0/"
]

def safe_replace(src: Path, dst: Path, retries: int = 5, delay: float = 0.5):
    """Safely replace/rename file on Windows handling transient AV scanner locks."""
    for attempt in range(retries):
        try:
            if dst.exists():
                dst.unlink()
            src.rename(dst)
            return True
        except PermissionError:
            time.sleep(delay)
    # Final attempt with os.replace
    os.replace(src, dst)
    return True

def download_file(sub: str, fname: str, dest_path: Path, max_retries: int = 5) -> bool:
    """Download a file with high-speed S3 mirror fallback and validation."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_name(f"{dest_path.name}.tmp.{os.getpid()}")

    # If already downloaded and valid size (> 1 MB), skip
    if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
        print(f"[EXISTS] {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB)", flush=True)
        return True

    for attempt in range(1, max_retries + 1):
        for base_url in BASE_URLS:
            quoted_fname = urllib.parse.quote(fname)
            url = f"{base_url}{sub}/{quoted_fname}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as response:
                    total_size = int(response.info().get("Content-Length", 0))
                    with open(temp_path, "wb") as out_file:
                        downloaded = 0
                        block_size = 512 * 1024
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            downloaded += len(buffer)
                            out_file.write(buffer)

                # Check downloaded size
                if total_size > 0 and temp_path.stat().st_size != total_size:
                    raise IOError(f"Incomplete download: {temp_path.stat().st_size} / {total_size} bytes")

                if temp_path.exists():
                    safe_replace(temp_path, dest_path)

                print(f"[DOWNLOADED] {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB) via {base_url}", flush=True)
                return True

            except Exception as e:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                time.sleep(1)

        print(f"[RETRY {attempt}/{max_retries}] {dest_path.name}", flush=True)
        time.sleep(2 * attempt)

    print(f"[FAILED] Could not download {dest_path.name} after {max_retries} attempts.", flush=True)
    return False


def main():
    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    df = pd.read_csv(MANIFEST_PATH)
    print(f"Loaded manifest with {len(df)} files.")

    # Sort so all seizure files are downloaded first, then seizure-free files
    df_seizure = df[df["is_seizure_file"] == 1].copy()
    df_free = df[df["is_seizure_file"] == 0].copy()

    print(f"Priority 1: {len(df_seizure)} Seizure-containing files (approx. {len(df_seizure)*42} MB)")
    print(f"Priority 2: {len(df_free)} Seizure-free background files (approx. {len(df_free)*42} MB)")

    success_count = 0
    fail_count = 0

    print("\n--- Downloading Priority 1: Seizure Files ---", flush=True)
    for _, row in df_seizure.iterrows():
        sub = row["subject"]
        fname = row["filename"]
        dest = RAW_DATA_DIR / sub / fname
        if download_file(sub, fname, dest):
            success_count += 1
        else:
            fail_count += 1

    print("\n--- Downloading Priority 2: Seizure-Free Background Files ---", flush=True)
    for _, row in df_free.iterrows():
        sub = row["subject"]
        fname = row["filename"]
        dest = RAW_DATA_DIR / sub / fname
        if download_file(sub, fname, dest):
            success_count += 1
        else:
            fail_count += 1

    print(f"\nDownload summary: {success_count} succeeded, {fail_count} failed.")

if __name__ == "__main__":
    main()
