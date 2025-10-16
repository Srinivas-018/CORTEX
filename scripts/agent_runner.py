#!/usr/bin/env python3
"""
Lightweight agent runner for CI: runs a quick smoke check, optional formatting,
and stages any repository changes so the workflow can commit them.

This script is intentionally conservative: it won't make network calls or
exfiltrate secrets. It runs locally inside the workflow using the
GITHUB_TOKEN (via the checkout action) to allow committing results.
"""
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_command(cmd, cwd=ROOT, check=True, capture=False):
    print(f"> {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=capture)
    if check and res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise SystemExit(res.returncode)
    return res


def format_code():
    # Try to run black if installed; otherwise skip
    try:
        run_command("black --version", check=False)
        print("Running black formatting...")
        run_command("black .", check=False)
    except Exception:
        print("black not available or formatting failed; skipping")


def smoke_check():
    # Run a quick import check of the app to catch obvious errors.
    app_path = ROOT / "AIModelPerfector" / "app.py"
    if not app_path.exists():
        print("app.py not found; skipping smoke check")
        return

    print("Running smoke check: import AIModelPerfector.app")
    run_command(f"python -c \"import importlib.util, sys; sys.path.insert(0, 'AIModelPerfector'); import app\"", check=False)


def stage_changes():
    # Stage any changes for commit
    run_command("git add -A", check=False)
    # Check if there is anything to commit
    status = run_command("git status --porcelain", check=False, capture=True)
    output = status.stdout.strip() if status.stdout else ""
    if output:
        print("Changes detected, creating commit...")
        run_command("git commit -m \"Auto: agent run updates\" || true", check=False)
    else:
        print("No changes to commit")


def main():
    print("Agent runner starting...")
    format_code()
    smoke_check()
    stage_changes()
    print("Agent runner finished")


if __name__ == "__main__":
    main()
