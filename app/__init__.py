"""
BluePuppy - Production Windows DFU Application
mcumgr/SMP over BLE for Nordic/Zephyr devices
"""

import tomllib
from pathlib import Path

__author__ = "Bit Byte LLC - Open Source Projects Team"
__license__ = "MIT"


def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception:
        return "0.0.0"  # Fallback version


__version__ = _get_version()
