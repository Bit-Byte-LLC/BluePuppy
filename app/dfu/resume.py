"""
DFU resume logic
Handles interrupted uploads and resume from last known offset
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.util import get_logger

logger = get_logger(__name__)


@dataclass
class ResumeState:
    """
    State for resuming an interrupted DFU operation.
    """

    device_address: str
    image_sha256: str
    image_size: int
    last_offset: int
    chunk_size: int
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResumeState":
        """Create from dictionary."""
        return cls(**data)


class ResumeManager:
    """
    Manages DFU resume state persistence.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize resume manager.
        
        Args:
            state_dir: Directory for state files (defaults to AppData/Local)
        """
        if state_dir is None:
            state_dir = Path.home() / "AppData" / "Local" / "BluePuppy" / "resume"

        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("resume_manager_init", state_dir=str(self.state_dir))

    def _get_state_file(self, device_address: str, image_sha256: str) -> Path:
        """
        Get state file path for a device and image.
        
        Args:
            device_address: Device BLE address or serial port
            image_sha256: Image SHA-256 hash
            
        Returns:
            Path to state file
        """
        # Sanitize device address for filename
        safe_address = device_address.replace(":", "_").replace("\\", "_").replace("/", "_")
        filename = f"resume_{safe_address}_{image_sha256[:16]}.json"
        return self.state_dir / filename

    def save_state(
        self,
        device_address: str,
        image_sha256: str,
        image_size: int,
        last_offset: int,
        chunk_size: int,
    ) -> None:
        """
        Save resume state.
        
        Args:
            device_address: Device identifier
            image_sha256: Image SHA-256 hash
            image_size: Total image size
            last_offset: Last successfully uploaded offset
            chunk_size: Chunk size used for upload
        """
        state = ResumeState(
            device_address=device_address,
            image_sha256=image_sha256,
            image_size=image_size,
            last_offset=last_offset,
            chunk_size=chunk_size,
            timestamp=datetime.now().isoformat(),
        )

        state_file = self._get_state_file(device_address, image_sha256)

        try:
            state_file.write_text(json.dumps(state.to_dict(), indent=2))
            logger.debug(
                "resume_state_saved",
                device=device_address,
                offset=last_offset,
                file=str(state_file),
            )
        except Exception as e:
            logger.error("resume_state_save_failed", error=str(e))

    def load_state(
        self, device_address: str, image_sha256: str
    ) -> Optional[ResumeState]:
        """
        Load resume state.
        
        Args:
            device_address: Device identifier
            image_sha256: Image SHA-256 hash
            
        Returns:
            ResumeState if found, None otherwise
        """
        state_file = self._get_state_file(device_address, image_sha256)

        if not state_file.exists():
            logger.debug("resume_state_not_found", file=str(state_file))
            return None

        try:
            data = json.loads(state_file.read_text())
            state = ResumeState.from_dict(data)

            logger.info(
                "resume_state_loaded",
                device=device_address,
                offset=state.last_offset,
                timestamp=state.timestamp,
            )

            return state

        except Exception as e:
            logger.error("resume_state_load_failed", error=str(e))
            return None

    def clear_state(self, device_address: str, image_sha256: str) -> None:
        """
        Clear resume state (after successful completion).
        
        Args:
            device_address: Device identifier
            image_sha256: Image SHA-256 hash
        """
        state_file = self._get_state_file(device_address, image_sha256)

        if state_file.exists():
            try:
                state_file.unlink()
                logger.info("resume_state_cleared", file=str(state_file))
            except Exception as e:
                logger.error("resume_state_clear_failed", error=str(e))

    def clear_all_states(self) -> None:
        """Clear all resume states."""
        try:
            for state_file in self.state_dir.glob("resume_*.json"):
                state_file.unlink()
            logger.info("all_resume_states_cleared")
        except Exception as e:
            logger.error("clear_all_states_failed", error=str(e))

    def list_states(self) -> list[ResumeState]:
        """
        List all saved resume states.
        
        Returns:
            List of ResumeState objects
        """
        states = []

        for state_file in self.state_dir.glob("resume_*.json"):
            try:
                data = json.loads(state_file.read_text())
                state = ResumeState.from_dict(data)
                states.append(state)
            except Exception as e:
                logger.warning("failed_to_load_state", file=str(state_file), error=str(e))

        logger.debug("list_resume_states", count=len(states))
        return states


def calculate_resume_offset(
    current_image_size: int,
    saved_offset: int,
    saved_image_size: int,
) -> Optional[int]:
    """
    Calculate safe resume offset.
    
    Validates that the resume state is compatible with current image.
    
    Args:
        current_image_size: Current image size
        saved_offset: Last uploaded offset from saved state
        saved_image_size: Image size from saved state
        
    Returns:
        Safe resume offset, or None if resume not possible
    """
    # Image size must match
    if current_image_size != saved_image_size:
        logger.warning(
            "resume_size_mismatch",
            current=current_image_size,
            saved=saved_image_size,
        )
        return None

    # Offset must be valid
    if saved_offset < 0 or saved_offset >= current_image_size:
        logger.warning(
            "resume_invalid_offset",
            offset=saved_offset,
            size=current_image_size,
        )
        return None

    logger.info("resume_offset_valid", offset=saved_offset)
    return saved_offset
