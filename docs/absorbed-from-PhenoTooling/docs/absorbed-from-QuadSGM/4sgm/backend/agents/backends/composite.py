"""Composite backend configuration for hybrid state storage."""

import logging
import os

logger = logging.getLogger(__name__)


def get_composite_backend() -> dict:
    """
    Configure composite backend for hybrid storage.

    Uses StateBackend for default in-memory state management,
    and StoreBackend for persistent memory stores if needed.

    Returns:
        Dictionary with backend configuration.
    """
    backend_config = {
        "type": "composite",
        "default_backend": "state",
        "routes": {},
    }

    # Configure memory store backend if database URL is available
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        backend_config["routes"]["/memories/"] = {
            "type": "store",
            "url": db_url,
        }
        logger.info("Configured persistent memory store backend")
    else:
        logger.debug("DATABASE_URL not set, using in-memory state only")

    return backend_config
