"""PeopleFlow Backend Application."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
MODULES_DIR = ROOT_DIR / "modules"
for path in (ROOT_DIR, MODULES_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

