"""Langfuse callback handler for observability."""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_langfuse_handler() -> Optional[Any]:
    """
    Initialize Langfuse callback handler if credentials are available.

    The handler traces all agent actions, tool calls, and LLM interactions
    to the Langfuse dashboard for observability and debugging.

    Environment Variables:
        LANGFUSE_PUBLIC_KEY: Public key from Langfuse dashboard (required)
        LANGFUSE_SECRET_KEY: Secret key from Langfuse dashboard (required)
        LANGFUSE_HOST: Langfuse instance URL (default: https://cloud.langfuse.com)
        LANGFUSE_ENV: Environment name (development/staging/production)
        LANGFUSE_SAMPLE_RATE: Sampling rate 0.0-1.0 (default: 1.0)

    Returns:
        CallbackHandler instance if credentials present, None otherwise.

    Example:
        >>> handler = get_langfuse_handler()
        >>> if handler:
        ...     agent = create_react_agent(..., callbacks=[handler])
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        logger.debug("Langfuse credentials not configured, observability disabled")
        return None

    try:
        from langfuse.langchain import CallbackHandler

        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        env = os.getenv("LANGFUSE_ENV", "development")
        sample_rate = float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0"))

        # Validate sample rate
        sample_rate = max(0.0, min(1.0, sample_rate))

        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        logger.info("Langfuse callback handler initialized")
        logger.info(f"  Host: {host}")
        logger.info(f"  Environment: {env}")
        logger.info(f"  Sample Rate: {sample_rate * 100:.1f}%")

        return handler

    except ImportError:
        logger.warning("langfuse package not installed. Install with: pip install langfuse")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse handler: {e}", exc_info=True)
        return None


def is_langfuse_enabled() -> bool:
    """
    Check if Langfuse observability is enabled.

    Returns:
        True if both public and secret keys are configured, False otherwise.
    """
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def get_langfuse_client() -> Optional[Any]:
    """
    Get a direct Langfuse client for manual tracing.

    Useful for creating custom spans outside of LangChain callbacks.

    Returns:
        Langfuse client instance if credentials available, None otherwise.

    Example:
        >>> client = get_langfuse_client()
        >>> if client:
        ...     trace = client.trace(name="custom-trace")
        ...     span = trace.span(name="custom-span")
        ...     span.end()
        ...     client.flush()
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse import Langfuse

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        return client

    except ImportError:
        logger.warning("langfuse package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to create Langfuse client: {e}", exc_info=True)
        return None
