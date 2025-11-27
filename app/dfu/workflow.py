"""
DFU workflow orchestration
State machine for firmware update process
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

from app.smp import SMPClient
from app.util import format_speed, get_logger

from .image import ImageMetadata, chunk_image
from .resume import ResumeManager, calculate_resume_offset

logger = get_logger(__name__)


class DFUState(Enum):
    """DFU workflow states."""

    IDLE = auto()
    CONNECTING = auto()
    QUERYING_SLOTS = auto()
    PREPARING = auto()
    UPLOADING = auto()
    TESTING = auto()
    RESETTING = auto()
    RECONNECTING = auto()
    VERIFYING = auto()
    CONFIRMING = auto()
    COMPLETE = auto()
    ERROR = auto()
    CANCELLED = auto()


@dataclass
class DFUProgress:
    """
    DFU progress information.
    """

    state: DFUState
    message: str
    bytes_uploaded: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    eta_seconds: float = 0.0

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_uploaded / self.total_bytes) * 100.0

    @property
    def speed_formatted(self) -> str:
        """Get formatted transfer speed."""
        return format_speed(self.speed_bps)

    @property
    def eta_formatted(self) -> str:
        """Get formatted ETA."""
        if self.eta_seconds <= 0:
            return "calculating..."

        if self.eta_seconds < 60:
            return f"{int(self.eta_seconds)}s"
        elif self.eta_seconds < 3600:
            minutes = int(self.eta_seconds / 60)
            seconds = int(self.eta_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.eta_seconds / 3600)
            minutes = int((self.eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class DFUWorkflow:
    """
    DFU workflow orchestrator.
    Manages the complete firmware update process.
    """

    def __init__(
        self,
        smp_client: SMPClient,
        device_identifier: str,
        chunk_size: Optional[int] = None,
        auto_confirm: bool = False,
        enable_resume: bool = True,
    ):
        """
        Initialize DFU workflow.
        
        Args:
            smp_client: SMP client instance
            device_identifier: Device address or serial port
            chunk_size: Upload chunk size (auto-calculated if None)
            auto_confirm: Automatically confirm image after successful test
            enable_resume: Enable resume support
        """
        self.smp_client = smp_client
        self.device_identifier = device_identifier
        self.chunk_size = chunk_size
        self.auto_confirm = auto_confirm
        self.enable_resume = enable_resume

        self.state = DFUState.IDLE
        self.resume_manager = ResumeManager() if enable_resume else None

        self._cancel_flag = False
        self._progress_callback: Optional[Callable[[DFUProgress], None]] = None

        logger.info(
            "dfu_workflow_init",
            device=device_identifier,
            chunk_size=chunk_size,
            auto_confirm=auto_confirm,
            enable_resume=enable_resume,
        )

    def set_progress_callback(self, callback: Callable[[DFUProgress], None]) -> None:
        """
        Set progress callback.
        
        Args:
            callback: Function to call with progress updates
        """
        self._progress_callback = callback

    def _update_progress(self, progress: DFUProgress) -> None:
        """Update progress and call callback if set."""
        self.state = progress.state

        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.error("progress_callback_error", error=str(e))

    async def execute(self, image: ImageMetadata) -> bool:
        """
        Execute complete DFU workflow.
        
        Args:
            image: Firmware image metadata
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("dfu_execute_start", image=repr(image))
        self._cancel_flag = False

        try:
            # Connect (if not already connected)
            if not self.smp_client.is_connected:
                await self._connect()

            if self._cancel_flag:
                return False

            # Query current image slots
            slots = await self._query_slots()

            if self._cancel_flag:
                return False

            # Prepare for upload
            await self._prepare(image, slots)

            if self._cancel_flag:
                return False

            # Upload image
            success = await self._upload(image)

            if not success or self._cancel_flag:
                return False

            # Mark for test
            await self._test_image(image)

            if self._cancel_flag:
                return False

            # Reset device
            await self._reset_device()

            if self._cancel_flag:
                return False

            # Reconnect
            await self._reconnect()

            if self._cancel_flag:
                return False

            # Verify new image
            await self._verify_image(image)

            if self._cancel_flag:
                return False

            # Optionally confirm
            if self.auto_confirm:
                await self._confirm_image()

            # Complete
            self._update_progress(
                DFUProgress(
                    state=DFUState.COMPLETE,
                    message="DFU complete successfully",
                    bytes_uploaded=image.size,
                    total_bytes=image.size,
                )
            )

            # Clear resume state
            if self.resume_manager:
                self.resume_manager.clear_state(
                    self.device_identifier, image.sha256_hex
                )

            logger.info("dfu_execute_complete")
            return True

        except Exception as e:
            logger.error("dfu_execute_error", error=str(e))
            self._update_progress(
                DFUProgress(
                    state=DFUState.ERROR,
                    message=f"DFU failed: {e}",
                )
            )
            return False

    async def _connect(self) -> None:
        """Connect to device."""
        logger.info("dfu_connect_start")
        self._update_progress(
            DFUProgress(state=DFUState.CONNECTING, message="Connecting to device...")
        )

        await self.smp_client.connect()

    async def _query_slots(self) -> list:
        """
        Query image slots.
        
        Returns:
            List of ImageSlot objects
        """
        logger.info("dfu_query_slots_start")
        self._update_progress(
            DFUProgress(
                state=DFUState.QUERYING_SLOTS, message="Querying image slots..."
            )
        )

        slots = await self.smp_client.img_list()
        logger.info("dfu_slots_queried", slot_count=len(slots))

        for slot in slots:
            logger.info("slot_info", slot=repr(slot))
        
        return slots

    async def _prepare(self, image: ImageMetadata, slots: list) -> None:
        """
        Prepare for upload.
        
        Args:
            image: Image to upload
            slots: List of current image slots
        """
        logger.info("dfu_prepare_start")
        self._update_progress(
            DFUProgress(state=DFUState.PREPARING, message="Preparing for upload...")
        )

        # Check if slot 1 (secondary) exists
        slot1_exists = any(slot.slot == 1 for slot in slots)
        
        if slot1_exists:
            # Erase slot 1 for clean upload - prevents corrupted/partial image issues
            logger.info("dfu_erase_slot1_start", reason="clean_upload")
            self._update_progress(
                DFUProgress(state=DFUState.PREPARING, message="Erasing secondary slot...")
            )
            
            try:
                await self.smp_client.img_erase(slot=1)
                logger.info("dfu_erase_slot1_complete")
                
                # Clear resume state since we're starting fresh
                if self.resume_manager:
                    self.resume_manager.clear_state(
                        self.device_identifier, image.sha256_hex
                    )
                    logger.info("resume_state_cleared", reason="slot_erased")
                    
            except Exception as e:
                logger.warning("dfu_erase_slot1_failed", error=str(e), note="continuing_anyway")
        else:
            # No slot 1 exists - clear any stale resume state
            # Resume state is only valid if slot 1 still exists on the device
            if self.resume_manager:
                resume_state = self.resume_manager.load_state(
                    self.device_identifier, image.sha256_hex
                )
                if resume_state:
                    logger.info("resume_state_invalid", reason="slot1_not_found", 
                               offset=resume_state.last_offset)
                    self.resume_manager.clear_state(
                        self.device_identifier, image.sha256_hex
                    )
                    logger.info("resume_state_cleared", reason="no_slot1")

        # Auto-calculate chunk size if not set
        if self.chunk_size is None:
            mtu = await self.smp_client.get_mtu()
            # MTU - ATT overhead (8) - SMP header (8) - CBOR overhead (~20-30)
            self.chunk_size = max(32, mtu - 50)

        logger.info(
            "dfu_chunk_size",
            chunk_size=self.chunk_size,
            mtu=await self.smp_client.get_mtu(),
        )

    async def _upload(self, image: ImageMetadata) -> bool:
        """
        Upload image with resume support.
        
        Args:
            image: Image to upload
            
        Returns:
            True if successful
        """
        logger.info("dfu_upload_start", size=image.size)

        # Check for resume state
        start_offset = 0
        if self.resume_manager:
            resume_state = self.resume_manager.load_state(
                self.device_identifier, image.sha256_hex
            )
            if resume_state:
                resume_offset = calculate_resume_offset(
                    image.size, resume_state.last_offset, resume_state.image_size
                )
                if resume_offset is not None:
                    start_offset = resume_offset
                    logger.info("dfu_resume_from_offset", offset=start_offset)

        # Chunk the image
        chunks = chunk_image(image.data, self.chunk_size)
        total_chunks = len(chunks)

        # Calculate start chunk
        start_chunk = start_offset // self.chunk_size if start_offset > 0 else 0

        # Upload metrics
        start_time = time.time()
        bytes_uploaded = start_offset

        # Upload chunks
        for chunk_idx in range(start_chunk, total_chunks):
            if self._cancel_flag:
                logger.info("dfu_upload_cancelled", offset=bytes_uploaded)
                return False

            chunk_offset = chunk_idx * self.chunk_size
            chunk_data = chunks[chunk_idx]

            # Progress update
            elapsed = time.time() - start_time
            if elapsed > 0 and bytes_uploaded > start_offset:
                speed_bps = (bytes_uploaded - start_offset) / elapsed
                remaining_bytes = image.size - bytes_uploaded
                eta = remaining_bytes / speed_bps if speed_bps > 0 else 0
            else:
                speed_bps = 0.0
                eta = 0.0

            self._update_progress(
                DFUProgress(
                    state=DFUState.UPLOADING,
                    message=f"Uploading chunk {chunk_idx + 1}/{total_chunks}...",
                    bytes_uploaded=bytes_uploaded,
                    total_bytes=image.size,
                    speed_bps=speed_bps,
                    eta_seconds=eta,
                )
            )

            # Upload chunk
            try:
                next_offset = await self.smp_client.img_upload(
                    offset=chunk_offset,
                    data=chunk_data,
                    total_size=image.size if chunk_idx == 0 else None,
                    sha=image.sha256 if chunk_idx == 0 else None,
                    timeout=15.0,  # Longer timeout for uploads
                )

                bytes_uploaded = next_offset

                # Save resume state periodically
                if self.resume_manager and chunk_idx % 10 == 0:
                    self.resume_manager.save_state(
                        self.device_identifier,
                        image.sha256_hex,
                        image.size,
                        bytes_uploaded,
                        self.chunk_size,
                    )

            except Exception as e:
                logger.error(
                    "dfu_upload_chunk_failed",
                    chunk=chunk_idx,
                    offset=chunk_offset,
                    error=str(e),
                )

                # Save resume state before giving up
                if self.resume_manager:
                    self.resume_manager.save_state(
                        self.device_identifier,
                        image.sha256_hex,
                        image.size,
                        bytes_uploaded,
                        self.chunk_size,
                    )

                raise

        # Final progress
        elapsed = time.time() - start_time
        avg_speed = (bytes_uploaded - start_offset) / elapsed if elapsed > 0 else 0.0

        logger.info(
            "dfu_upload_complete",
            bytes=bytes_uploaded,
            elapsed=elapsed,
            avg_speed=format_speed(avg_speed),
        )

        return True

    async def _test_image(self, image: ImageMetadata) -> None:
        """Mark image for testing."""
        logger.info("dfu_test_image_start")
        self._update_progress(
            DFUProgress(state=DFUState.TESTING, message="Marking image for test...")
        )

        # Query slots to get the hash of the uploaded image in slot 1
        slots = await self.smp_client.img_list()
        logger.info("dfu_test_query_slots", slot_count=len(slots))
        
        # Find slot 1 (secondary/uploaded image)
        slot1 = next((s for s in slots if s.slot == 1), None)
        
        if not slot1:
            raise RuntimeError("Uploaded image not found in slot 1")
        
        logger.info("dfu_test_using_hash", hash=slot1.hash.hex()[:16] + "...")
        
        # Test using the MCUboot image hash from slot 1
        await self.smp_client.img_test(hash_bytes=slot1.hash)
        logger.info("dfu_test_image_complete")

    async def _reset_device(self) -> None:
        """Reset the device."""
        logger.info("dfu_reset_device_start")
        self._update_progress(
            DFUProgress(state=DFUState.RESETTING, message="Rebooting device...")
        )

        await self.smp_client.os_reset()

        # Wait a moment for reset
        await asyncio.sleep(2.0)

        logger.info("dfu_reset_device_complete")

    async def _reconnect(self) -> None:
        """Reconnect to device after reset."""
        logger.info("dfu_reconnect_start")
        self._update_progress(
            DFUProgress(
                state=DFUState.RECONNECTING, message="Reconnecting to device..."
            )
        )

        # Disconnect first
        await self.smp_client.disconnect()

        # Wait for device to boot
        await asyncio.sleep(3.0)

        # Retry connection with backoff
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self.smp_client.connect()
                logger.info("dfu_reconnect_success", attempt=attempt + 1)
                return
            except Exception as e:
                logger.warning(
                    "dfu_reconnect_attempt_failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def _verify_image(self, image: ImageMetadata) -> None:
        """Verify new image is active."""
        logger.info("dfu_verify_image_start")
        self._update_progress(
            DFUProgress(state=DFUState.VERIFYING, message="Verifying new image...")
        )

        slots = await self.smp_client.img_list()

        # Find active slot
        active_slot = next((s for s in slots if s.active), None)

        if active_slot:
            logger.info("active_image", slot=repr(active_slot))

            # Check if hash matches (first 32 bytes should match)
            if active_slot.hash[:32] == image.sha256[:32]:
                logger.info("dfu_verify_success", hash_match=True)
            else:
                logger.warning(
                    "dfu_verify_hash_mismatch",
                    expected=image.sha256_hex[:16],
                    actual=active_slot.hash.hex()[:16],
                )
        else:
            logger.warning("dfu_verify_no_active_slot")

    async def _confirm_image(self) -> None:
        """Confirm the image (make permanent)."""
        logger.info("dfu_confirm_image_start")
        self._update_progress(
            DFUProgress(state=DFUState.CONFIRMING, message="Confirming image...")
        )

        await self.smp_client.img_confirm()
        logger.info("dfu_confirm_image_complete")

    def cancel(self) -> None:
        """Cancel the DFU operation."""
        logger.info("dfu_cancel_requested")
        self._cancel_flag = True
        self._update_progress(
            DFUProgress(state=DFUState.CANCELLED, message="DFU cancelled by user")
        )
