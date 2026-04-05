"""Experiments package."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
EXPERIMENTS_DIR = ROOT_DIR / "research" / "experiments"
OUTPUT_DIR = EXPERIMENTS_DIR / "output"
ARTIFACTS_EXPERIMENT_DIR = ROOT_DIR / "artifacts" / "experiments" / "output"
EXPERIMENT_INDEX_PATH = ARTIFACTS_EXPERIMENT_DIR / "index.json"
