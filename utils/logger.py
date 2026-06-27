"""
utils/logger.py
---------------
Lightweight structured logger used across all modules.

Uses Python's built-in logging so there are zero extra dependencies.
Format includes timestamp, level, and module name for easy debugging.
"""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return (or create) a named logger with a consistent format.

    All loggers write to stderr so they don't interfere with the
    streamed output that goes to stdout.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False   # avoid duplicate messages from root logger
    return logger
