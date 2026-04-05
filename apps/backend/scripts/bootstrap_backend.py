"""Bootstrap the backend development environment.

Usage:
  python apps/backend/scripts/bootstrap_backend.py

This script:
- creates `.venv` under `apps/backend` if missing
- upgrades pip/setuptools/wheel
- installs `apps/backend/requirements.txt`
- creates root `.env` from `infra/deployment/environment.example.env` if missing
- prints exact activation and run commands
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"[bootstrap] $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the PeopleFlow backend environment.")
    parser.add_argument(
        "--with-ml",
        action="store_true",
        help="Install optional ML extras from requirements-ml.txt after the core backend requirements.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    backend_dir = script_path.parents[1]
    repo_root = script_path.parents[3]

    venv_dir = backend_dir / ".venv"
    requirements_path = backend_dir / "requirements.txt"
    requirements_ml_path = backend_dir / "requirements-ml.txt"
    env_example = repo_root / "infra" / "deployment" / "environment.example.env"
    env_file = repo_root / ".env"

    if not requirements_path.exists():
        print(f"[bootstrap] Missing requirements file: {requirements_path}")
        return 1

    if not venv_dir.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print(f"[bootstrap] Reusing existing virtual environment: {venv_dir}")

    if os.name == "nt":
        py = venv_dir / "Scripts" / "python.exe"
    else:
        py = venv_dir / "bin" / "python"

    if not py.exists():
        print(f"[bootstrap] Virtual environment python not found: {py}")
        return 1

    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(py), "-m", "pip", "install", "-r", str(requirements_path)])
    if args.with_ml:
        if requirements_ml_path.exists():
            run([str(py), "-m", "pip", "install", "-r", str(requirements_ml_path)])
        else:
            print(f"[bootstrap] Skipped ML extras; requirements file not found: {requirements_ml_path}")

    if not env_file.exists():
        if env_example.exists():
            shutil.copy2(env_example, env_file)
            print(f"[bootstrap] Created {env_file} from template.")
        else:
            print(f"[bootstrap] Skipped .env creation; template not found: {env_example}")
    else:
        print(f"[bootstrap] Reusing existing env file: {env_file}")

    print("\n[bootstrap] Backend setup complete.\n")
    if os.name == "nt":
        print("Activate venv:")
        print(r"  apps\\backend\\.venv\\Scripts\\activate")
    else:
        print("Activate venv:")
        print("  source apps/backend/.venv/bin/activate")

    print("Run backend:")
    print("  cd apps/backend")
    print("  python -m uvicorn app.main:app --reload --port 8000")
    if args.with_ml:
        print("")
        print("[bootstrap] Optional ML extras installed.")
        print("Detectron2 remains best-effort and may still require Linux/WSL or a pinned wheel/toolchain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
