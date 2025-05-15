import logging
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    formatter: Optional[logging.Formatter] = None,
    propagate: bool = True,
) -> logging.Logger:
    """
    Set up and return a logger with consistent configuration.

    Args:
        name: Name of the logger
        level: Logging level (default: logging.INFO)
        formatter: Custom formatter (default: uses standard format)
        propagate: Whether to propagate to parent logger (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Use default formatter if none provided
    if formatter is None:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler if no handlers exist
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Set propagation
    logger.propagate = propagate

    return logger
