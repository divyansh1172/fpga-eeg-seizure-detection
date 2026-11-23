"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Packages mtr-15.zip adhering to Course Rule 9 (no .edf, no .npz).
         Includes mtr-15.pdf, src/, rtl/, scripts/, vectors/, results/, data/,
         report/ (active TeX + bib), README.md, process.md.
         Prunes intermediate patch scripts, old draft backups, and transient files.
AI-assisted: yes
"""

import os
import zipfile
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJ_ROOT / "mtr-15.zip"

EXCLUDE_EXTS = {
    ".edf", ".npz", ".tmp", ".log", ".pyc", ".xdv", ".aux", 
    ".bbl", ".blg", ".fls", ".fdb_latexmk", ".bak", ".out"
}

EXCLUDE_DIRS = {
    "data/raw", "data/processed", "bin", "__pycache__", 
    ".git", ".vscode", ".idea", "report/results"
}

# Specific redundant files to exclude from package
EXCLUDE_EXACT_FILES = {
    "report/mtr-15.tex.bak_audit2",
    "report/mtr-15.tex.bak_audit3",
    "report/midterm.tex",
    "report/preliminary_main.tex",
    "report/references.bib",
    "report/mtr-15.out",
    "scripts/apply_audit3_clean.py",
    "scripts/apply_audit4_clean.py",
    "scripts/run_s1.py",
    "scripts/overnight_pipeline.py",
    "scripts/download_data.py"
}

def should_include(rel_path: str) -> bool:
    norm_path = rel_path.replace("\\", "/")
    
    # Check excluded directories
    for ex_dir in EXCLUDE_DIRS:
        if norm_path == ex_dir or norm_path.startswith(ex_dir + "/"):
            return False
            
    # Check exact excluded files
    if norm_path in EXCLUDE_EXACT_FILES or Path(norm_path).name.startswith("mtr-15.tex.bak"):
        return False
        
    # Check excluded extensions
    suffix = Path(norm_path).suffix.lower()
    if suffix in EXCLUDE_EXTS:
        return False
        
    if norm_path.endswith("tectonic.exe"):
        return False
        
    return True

def package():
    print(f"Creating clean submission zip: {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add root core deliverables
        root_files = ["mtr-15.pdf", "README.md", "process.md"]
        for rf in root_files:
            fpath = PROJ_ROOT / rf
            if fpath.exists():
                zf.write(fpath, arcname=rf)
                print(f"  + {rf}")

        # Add directories
        dirs_to_add = ["src", "rtl", "scripts", "report", "results", "vectors", "data"]
        for d in dirs_to_add:
            dp = PROJ_ROOT / d
            if not dp.exists():
                continue
            for root, _, files in os.walk(dp):
                for f in sorted(files):
                    fp = Path(root) / f
                    rel_path = str(fp.relative_to(PROJ_ROOT))
                    if should_include(rel_path):
                        zf.write(fp, arcname=rel_path)
                        print(f"  + {rel_path}")

    size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"\n[DONE] Clean package created successfully: {ZIP_PATH} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    package()
