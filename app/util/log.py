"""
Logging configuration and utilities
Provides structured logging with rotating file handlers
"""

import contextlib
import logging
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    log_to_console: bool = True,
) -> None:
    """
    Configure structured logging with file rotation and console output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to user's AppData/Local)
        log_to_console: Whether to also output to console
    """
    # Determine log directory
    if log_dir is None:
        log_dir = Path.home() / "AppData" / "Local" / "BluePuppy" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "dfu_app.log"

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[],
    )

    # File handler with rotation (10 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file

    handlers = [file_handler]

    # Console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        handlers.append(console_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Apply handlers to root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LogCapture:
    """
    Capture log messages for display in UI.
    Thread-safe log handler that stores recent messages.
    """

    def __init__(self, max_messages: int = 1000):
        """
        Initialize log capture.

        Args:
            max_messages: Maximum number of messages to store
        """
        self.max_messages = max_messages
        self.messages: list[str] = []
        self.callbacks: list[Callable] = []

    def add_message(self, message: str) -> None:
        """Add a log message and notify callbacks."""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        # Notify all registered callbacks
        for callback in self.callbacks:
            with contextlib.suppress(Exception):
                callback(message)  # Don't let callback errors break logging

    def register_callback(self, callback: Callable) -> None:
        """Register a callback to be notified of new messages."""
        self.callbacks.append(callback)

    def clear(self) -> None:
        """Clear all captured messages."""
        self.messages.clear()

    def get_messages(self) -> list[str]:
        """Get all captured messages."""
        return self.messages.copy()


# Global log capture instance
_log_capture: LogCapture | None = None


def get_log_capture() -> LogCapture:
    """Get the global log capture instance."""
    global _log_capture
    if _log_capture is None:
        _log_capture = LogCapture()
    return _log_capture


class UILogHandler(logging.Handler):
    """Custom log handler that feeds messages to the UI."""

    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the capture."""
        try:
            msg = self.format(record)
            self.log_capture.add_message(msg)
        except Exception:
            self.handleError(record)


def add_ui_handler() -> None:
    """Add UI log handler to root logger."""
    log_capture = get_log_capture()
    ui_handler = UILogHandler(log_capture)
    ui_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.getLogger().addHandler(ui_handler)
