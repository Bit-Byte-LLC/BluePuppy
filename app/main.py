"""
Main application entry point
Integrates PySide6 with asyncio using qasync
"""

import sys
from pathlib import Path

import qasync
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.util import APP_NAME, APP_ORGANIZATION, APP_VERSION, get_logger, setup_logging


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code
    """
    # Setup logging
    setup_logging(log_level="INFO", log_to_console=True)
    logger = get_logger(__name__)

    logger.info(
        "app_starting",
        name=APP_NAME,
        version=str(APP_VERSION),
        organization=APP_ORGANIZATION,
    )

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationVersion(str(APP_VERSION))

    # Setup qasync event loop
    loop = qasync.QEventLoop(app)
    import asyncio

    asyncio.set_event_loop(loop)

    # Create main window
    window = MainWindow()
    window.show()

    logger.info("app_started", window_visible=True)

    # Run event loop
    with loop:
        exit_code = loop.run_forever()

    logger.info("app_exiting", exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
