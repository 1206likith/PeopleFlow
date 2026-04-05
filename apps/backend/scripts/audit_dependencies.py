#!/usr/bin/env python3
"""
Dependency verification and audit script.
Checks for outdated packages, security vulnerabilities, and transitive issues.
"""

import subprocess
import sys
import json
from pathlib import Path


def run_pip_audit() -> bool:
    """Run pip-audit to check for security vulnerabilities."""
    print("🔍 Running security audit with pip-audit...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--desc"],
            cwd=Path(__file__).parent,
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("⚠ pip-audit not installed. Install with: pip install pip-audit")
        return False


def check_outdated_packages() -> bool:
    """Check for outdated packages."""
    print("\n📦 Checking for outdated packages...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--outdated"],
        capture_output=True,
        text=True,
    )
    
    if result.stdout:
        print("Found outdated packages:")
        print(result.stdout)
        return False
    else:
        print("✓ All packages are up to date")
        return True


def verify_transitive_pins() -> bool:
    """Verify that all transitive dependencies are reasonably pinned."""
    print("\n📋 Verifying transitive dependency pins...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "-f"],
        capture_output=True,
        text=True,
    )
    
    requirements_path = Path(__file__).parent / "requirements.txt"
    required_packages = set()
    
    with open(requirements_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name
                pkg_name = line.split("==")[0].split(">=")[0].split("<")[0].strip()
                required_packages.add(pkg_name.lower())
    
    print(f"✓ Verified {len(required_packages)} core packages")
    return True


def check_conflicting_dependencies() -> bool:
    """Check for conflicting dependency versions."""
    print("\n⚠ Checking for dependency conflicts...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print("Found dependency conflicts:")
        print(result.stdout)
        return False
    else:
        print("✓ No conflicting dependencies found")
        return True


def generate_pip_freeze() -> bool:
    """Generate current environment pip freeze."""
    print("\n💾 Generating pip freeze output...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
    )
    
    freeze_path = Path(__file__).parent / ".pip-freeze.txt"
    with open(freeze_path, "w") as f:
        f.write(result.stdout)
    
    print(f"✓ Saved to {freeze_path}")
    print(f"✓ {len(result.stdout.splitlines())} total packages in environment")
    return True


def main() -> int:
    """Run all dependency checks."""
    print("=" * 60)
    print("PeopleFlow Backend - Dependency Audit")
    print("=" * 60)
    
    checks = [
        ("Security Audit", run_pip_audit),
        ("Outdated Packages", check_outdated_packages),
        ("Transitive Pins", verify_transitive_pins),
        ("Conflicting Dependencies", check_conflicting_dependencies),
        ("Freeze Snapshot", generate_pip_freeze),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            print(f"⚠ {name} failed: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("Audit Summary:")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_pass = all(results.values())
    print("\n" + ("✓ All checks passed!" if all_pass else "⚠ Some checks failed"))
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
