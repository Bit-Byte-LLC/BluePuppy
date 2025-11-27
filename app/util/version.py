"""
Version information and utilities
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


def _get_version_from_pyproject() -> "Version":
    """
    Read version from pyproject.toml using tomllib.

    Returns:
        Version instance from pyproject.toml

    Raises:
        RuntimeError: If version cannot be read
    """
    try:
        # Get path to pyproject.toml (relative to this file)
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

        # Read and parse pyproject.toml with tomllib
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        version_str = data["project"]["version"]
        return Version.from_string(version_str)

    except Exception as e:
        # Fallback to hardcoded version if pyproject.toml can't be read
        # This ensures the app works even when bundled
        import warnings
        warnings.warn(f"Could not read version from pyproject.toml: {e}. Using fallback.", stacklevel=2)
        return Version(2, 0, 0)


@dataclass
class Version:
    """Semantic version representation."""

    major: int
    minor: int
    patch: int
    build: int | None = None

    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        """
        Parse version string.

        Args:
            version_str: Version string (e.g., "1.2.3" or "1.2.3+4")

        Returns:
            Version instance

        Raises:
            ValueError: If version string is invalid
        """
        # Match semantic version with optional build number
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?$"
        match = re.match(pattern, version_str)

        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        major, minor, patch, build = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            build=int(build) if build else None,
        )

    def __str__(self) -> str:
        """String representation."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.build is not None:
            return f"{base}+{self.build}"
        return base

    def __lt__(self, other: "Version") -> bool:
        """Less than comparison."""
        if not isinstance(other, Version):
            return NotImplemented

        return (self.major, self.minor, self.patch, self.build or 0) < (
            other.major,
            other.minor,
            other.patch,
            other.build or 0,
        )

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Version):
            return NotImplemented

        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.build == other.build
        )

    def __le__(self, other: "Version") -> bool:
        """Less than or equal comparison."""
        return self < other or self == other

    def __gt__(self, other: "Version") -> bool:
        """Greater than comparison."""
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        """Greater than or equal comparison."""
        return not self < other


# Application version - read from pyproject.toml
APP_VERSION = _get_version_from_pyproject()
APP_NAME = "BluePuppy"
APP_ORGANIZATION = "Bit Byte LLC"
