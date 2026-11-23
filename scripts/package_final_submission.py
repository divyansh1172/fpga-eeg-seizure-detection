"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Team: 15
Author: Member 1 (Report & Packaging Lead)
Purpose: Packages clean submission archive `final-15.zip` adhering strictly to Course Rule 9
         (zero .edf or .npz raw data). Includes final-15.pdf, synthesizable RTL, testbenches,
         Python pipelines, verification scripts, results, and endsem documentation.
AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Member 1)
"""

import os
import zipfile
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJ_ROOT / "final-15.zip"

EXCLUDE_EXTS = {
    ".edf", ".npz", ".tmp", ".log", ".pyc", ".xdv", ".aux", 
    ".bbl", ".blg", ".fls", ".fdb_latexmk", ".bak", ".out"
}

EXCLUDE_DIRS = {
    "data/raw", "data/processed", "bin", "__pycache__", 
    ".git", ".vscode", ".idea", ".venv", "report/results"
}

EXCLUDE_EXACT_FILES = {
    "report/mtr-15.tex.bak_audit2",
    "report/mtr-15.tex.bak_audit3",
    "report/midterm.tex",
    "report/preliminary_main.tex",
    "report/mtr-15.out",
    "scripts/apply_audit3_clean.py",
    "scripts/apply_audit4_clean.py"
}

def should_include(rel_path: str) -> bool:
    norm_path = rel_path.replace("\\", "/")
    
    if Path(norm_path).name == ".DS_Store" or norm_path.endswith(".DS_Store"):
        return False

    # Check excluded directories
    for ex_dir in EXCLUDE_DIRS:
        if norm_path == ex_dir or norm_path.startswith(ex_dir + "/"):
            return False
            
    # Check exact excluded files
    if norm_path in EXCLUDE_EXACT_FILES or Path(norm_path).name.startswith("mtr-15.tex.bak"):
        return False
        
    # Explicit whitelist for required results telemetry log
    if norm_path == "results/uart_demo_playback.log":
        return True

    # Check excluded extensions
    suffix = Path(norm_path).suffix.lower()
    if suffix in EXCLUDE_EXTS:
        return False
        
    if norm_path.endswith("tectonic.exe") or norm_path.endswith(".bit"):
        return False
        
    return True

def package():
    print(f"Creating clean final submission archive: {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add root core deliverables
        root_files = ["final-15.pdf", "README.md", "process.md", "AGENT_PROMPT.md"]
        # Also check report/final-15.pdf
        report_pdf = PROJ_ROOT / "report" / "final-15.pdf"
        root_pdf = PROJ_ROOT / "final-15.pdf"
        if not root_pdf.exists() and report_pdf.exists():
            import shutil
            shutil.copy(report_pdf, root_pdf)

        for rf in root_files:
            fpath = PROJ_ROOT / rf
            if fpath.exists():
                zf.write(fpath, arcname=rf)
                print(f"  + [ROOT] {rf}")

        # Add directories
        dirs_to_add = [
            "src", "rtl", "scripts", "report", "results", 
            "vectors", "golden", "data", "endsem report", 
            "mid term report", "preliminary report"
        ]
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
    print(f"\n[DONE] Clean final submission package created: {ZIP_PATH} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    package()
