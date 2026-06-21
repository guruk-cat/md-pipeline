#!/usr/bin/env python3
"""
Copy the pipeline (src/) into a research repo as `.tools/`.

Usage: python setup-tools.py /path/to/research-repo
Overwrites any existing `.tools/` so re-running pushes the latest pipeline.
"""

import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"


def main(target):
    target = Path(target).resolve()
    if not target.is_dir():
        sys.exit(f"target is not a directory: {target}")

    dest = target / ".tools"
    shutil.copytree(
        SRC, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__")
    )
    print(f"copied {SRC} -> {dest}")

    # Ensure the build output is never committed. 
    # Create .gitignore if absent, append the rule if it isn't already listed.
    gitignore = target / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    if ".public/" not in lines:
        with gitignore.open("a", encoding="utf-8") as f:
            if lines and lines[-1].strip():
                f.write("\n")
            f.write(".public/\n")
        print(f"added .public/ to {gitignore}")
    print("next: set Cloudflare build command to")
    print("  pip install -r .tools/requirements.txt && python .tools/build.py")
    print("and output directory to .public")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python setup-tools.py /path/to/research-repo")
    main(sys.argv[1])
