"""
services/logging_service.py
============================
Configures application-wide logging.

WHY LOGGING INSTEAD OF PRINT()?
    print() is fine for quick debugging but has serious problems
    in production:
    - No timestamps
    - No severity levels (is this info or a critical error?)
    - No way to filter by module
    - Cannot write to files or databases
    - Cannot be turned off without removing code

    Python's logging module solves all of this.
    We configure it once here and every other module
    simply does: logger = logging.getLogger(__name__)
"""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging() -> None:
    """
    Sets up the logging system for the entire application.
    Call this once in main.py before anything else.

    LOGGING LEVELS (from least to most severe):
        DEBUG    - Detailed info for debugging (SQL queries, etc.)
        INFO     - General events (app started, stock fetched)
        WARNING  - Something unexpected but recoverable
        ERROR    - Something failed but app continues
        CRITICAL - App cannot continue
    """

    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Root logger — all loggers in the app inherit from this
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # ── Formatter ─────────────────────────────────────────────
    # Defines what each log line looks like
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ── Console Handler ───────────────────────────────────────
    # Prints logs to the terminal while developing
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # ── File Handler ──────────────────────────────────────────
    # Writes logs to a rotating file — when it hits 5MB,
    # it starts a new file and keeps the last 3 files.
    # This prevents logs from filling your hard drive.
    log_filename = os.path.join(
        'logs',
        f"stock_analyzer_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_filename,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Attach both handlers to the root logger
    # Clear any existing handlers first to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    logging.info("Logging system initialised.")
    logging.info(f"Log level : {log_level_str}")
    logging.info(f"Log file  : {log_filename}")
