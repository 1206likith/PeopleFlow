"""
Utilities for hardening report generation in containerized environments.
Handles permission issues, read-only filesystems, and graceful fallbacks.
"""

import os
import sys
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


class FileSystemConfig:
    """Configuration for filesystem access in containerized environments."""
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_artifact_base() -> Path:
        """Get the base directory for artifacts with fallback chain."""
        # Priority order: explicit env var > Vercel temp > /tmp > local reports
        candidates = [
            os.getenv("ARTIFACT_BASE_PATH"),      # Highest priority: explicit config
            os.getenv("REPORTS_DIR"),              # Legacy: reports directory
            "/mnt/artifacts" if os.getenv("VERCEL") else None,  # Vercel mount
            "/tmp/peopleflow" if os.getenv("DOCKER") else None,  # Docker temp
            "/tmp",                                 # Fallback: standard temp
            "reports" if not os.getenv("CONTAINER") else None,   # Local (non-container)
        ]
        
        for candidate in candidates:
            if not candidate:
                continue
            
            try:
                path = Path(candidate)
                # Verify path is writable
                if FileSystemConfig._verify_writable(path):
                    logger.info(f"Using artifact base: {path}")
                    return path
            except Exception as e:
                logger.debug(f"Artifact base candidate {candidate} failed: {e}")
                continue
        
        # Final fallback: create in temp
        fallback = Path(tempfile.gettempdir()) / "peopleflow-artifacts"
        logger.warning(f"All artifact base candidates failed, using fallback: {fallback}")
        return fallback
    
    @staticmethod
    def _verify_writable(path: Path) -> bool:
        """Verify that a path is writable."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Test write: create and delete a temp file
            test_file = path / ".test_write"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return True
        except (OSError, IOError, PermissionError) as e:
            logger.debug(f"Path {path} not writable: {e}")
            return False
    
    @staticmethod
    def get_reports_dir() -> Path:
        """Get reports directory with automatic fallback."""
        base = FileSystemConfig.get_artifact_base()
        reports_dir = base / "reports"
        return reports_dir
    
    @staticmethod
    def get_cache_dir() -> Path:
        """Get cache directory with automatic fallback."""
        base = FileSystemConfig.get_artifact_base()
        cache_dir = base / "cache"
        return cache_dir
    
    @staticmethod
    def get_logs_dir() -> Path:
        """Get logs directory with automatic fallback."""
        base = FileSystemConfig.get_artifact_base()
        logs_dir = base / "logs"
        return logs_dir


def ensure_writable_directory(path: Optional[Path] = None) -> Path:
    """
    Ensure a directory is writable, with automatic fallback to temp.
    Returns the writable path.
    """
    if path is None:
        return FileSystemConfig.get_artifact_base()
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Verify writable
        test_file = path / ".verify_write"
        test_file.write_text("verify", encoding="utf-8")
        test_file.unlink()
        logger.info(f"Directory confirmed writable: {path}")
        return path
    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Directory {path} not writable, using fallback: {e}")
        # Fall back to temp
        fallback = Path(tempfile.gettempdir()) / "peopleflow"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_safe_artifact_path(artifact_name: str, subdir: str = "reports") -> Path:
    """
    Get a safe path for an artifact with automatic handling of read-only filesystems.
    
    Args:
        artifact_name: Name of the artifact (e.g., 'simulation_report_123.pdf')
        subdir: Subdirectory within artifact base (e.g., 'reports', 'cache')
    
    Returns:
        Path object pointing to writable location
    """
    base = FileSystemConfig.get_artifact_base()
    artifact_dir = base / subdir
    
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir / artifact_name
    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Cannot create {subdir} in {base}, using temp: {e}")
        fallback_dir = Path(tempfile.gettempdir()) / "peopleflow" / subdir
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / artifact_name


def startup_filesystem_check() -> Tuple[bool, str]:
    """
    Perform startup checks on filesystem accessibility.
    Should be called during app initialization.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    checks = []
    
    # Check artifact base accessibility
    try:
        artifact_base = FileSystemConfig.get_artifact_base()
        checks.append(f"✓ Artifact base accessible: {artifact_base}")
    except Exception as e:
        checks.append(f"✗ Artifact base not accessible: {e}")
        return False, "\n".join(checks)
    
    # Check reports directory
    try:
        reports_dir = FileSystemConfig.get_reports_dir()
        reports_dir.mkdir(parents=True, exist_ok=True)
        checks.append(f"✓ Reports directory writable: {reports_dir}")
    except Exception as e:
        checks.append(f"⚠ Reports directory not writable, will use temp: {e}")
    
    # Check temp directory as fallback
    try:
        temp_dir = Path(tempfile.gettempdir())
        if temp_dir.exists():
            checks.append(f"✓ Temp directory available: {temp_dir}")
        else:
            checks.append(f"✗ Temp directory not available: {temp_dir}")
            return False, "\n".join(checks)
    except Exception as e:
        checks.append(f"✗ Cannot access temp directory: {e}")
        return False, "\n".join(checks)
    
    return True, "\n".join(checks)


def write_artifact_safely(
    content: bytes,
    artifact_name: str,
    subdir: str = "reports"
) -> Tuple[bool, Path, str]:
    """
    Write an artifact safely with automatic handling of filesystem issues.
    
    Args:
        content: Binary content to write
        artifact_name: Name of the artifact
        subdir: Subdirectory within artifact base
    
    Returns:
        Tuple of (success: bool, path: Path, error_message: str)
    """
    artifact_path = get_safe_artifact_path(artifact_name, subdir)
    
    try:
        artifact_path.write_bytes(content)
        logger.info(f"Artifact written successfully: {artifact_path}")
        return True, artifact_path, ""
    except (OSError, IOError, PermissionError) as e:
        error_msg = f"Failed to write artifact {artifact_name}: {e}"
        logger.error(error_msg)
        return False, artifact_path, error_msg


def cleanup_old_artifacts(max_age_hours: int = 24) -> int:
    """
    Clean up old artifacts to prevent disk space issues.
    
    Args:
        max_age_hours: Maximum age of artifacts to keep
    
    Returns:
        Number of artifacts cleaned
    """
    import time
    
    base = FileSystemConfig.get_artifact_base()
    if not base.exists():
        return 0
    
    cleaned = 0
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    try:
        for artifact in base.rglob("*"):
            if artifact.is_file():
                # Check modification time
                if os.path.getmtime(artifact) < cutoff_time:
                    try:
                        artifact.unlink()
                        cleaned += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {artifact}: {e}")
    except Exception as e:
        logger.warning(f"Error during artifact cleanup: {e}")
    
    return cleaned
