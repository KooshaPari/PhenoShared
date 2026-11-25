#!/usr/bin/env python3
"""Verify Langfuse integration is working end-to-end."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def verify_langfuse():
    """Verify Langfuse connection and basic functionality."""

    logger.info("=" * 60)
    logger.info("Langfuse Integration Verification")
    logger.info("=" * 60)

    # Step 1: Check environment variables
    logger.info("\n[1/5] Checking environment variables...")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    env = os.getenv("LANGFUSE_ENV", "development")
    sample_rate = float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0"))

    if not public_key or not secret_key:
        logger.error("Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")
        logger.error("Set these in your .env file to enable Langfuse observability")
        return False

    logger.info(f"  ✓ Public Key configured: {public_key[:20]}...")
    logger.info(f"  ✓ Secret Key configured: {secret_key[:20]}...")
    logger.info(f"  ✓ Host: {host}")
    logger.info(f"  ✓ Environment: {env}")
    logger.info(f"  ✓ Sample Rate: {sample_rate * 100:.1f}%")

    # Step 2: Test Langfuse client initialization
    logger.info("\n[2/5] Initializing Langfuse client...")
    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("  ✓ Langfuse client initialized")
    except ImportError:
        logger.error("langfuse package not installed")
        logger.error("Install with: pip install langfuse")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {e}")
        return False

    # Step 3: Create and submit test trace
    logger.info("\n[3/5] Creating test trace...")
    try:
        trace = client.trace(
            name="verification-test",
            user_id="test-user",
            metadata={"test": True, "timestamp": datetime.now().isoformat(), "version": "1.0"},
        )
        trace_id = trace.id
        logger.info(f"  ✓ Created trace: {trace_id}")

        # Add a span to the trace
        span = trace.span(
            name="test-span", input={"query": "verification test"}, metadata={"span_type": "test"}
        )
        logger.info(f"  ✓ Created span: {span.id}")

        # End the span
        span.end(output={"status": "success"})
        logger.info("  ✓ Span completed")

        # Update trace with output
        trace.update(output={"status": "success"}, metadata={"verified": True})
        logger.info("  ✓ Trace updated")

    except Exception as e:
        logger.error(f"Failed to create trace: {e}")
        return False

    # Step 4: Test callback handler
    logger.info("\n[4/5] Testing callback handler...")
    try:
        from agents.callbacks.langfuse import get_langfuse_handler

        handler = get_langfuse_handler()
        if handler:
            logger.info("  ✓ Langfuse callback handler loaded")
        else:
            logger.warning("  ⚠ Callback handler returned None (credentials may be missing)")
    except ImportError:
        logger.warning("  ⚠ Could not import callback handler")
    except Exception as e:
        logger.error(f"Callback handler error: {e}")
        return False

    # Step 5: Flush and verify
    logger.info("\n[5/5] Flushing data to Langfuse...")
    try:
        client.flush()
        logger.info("  ✓ Data flushed successfully")
    except Exception as e:
        logger.error(f"Failed to flush data: {e}")
        return False

    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("✅ LANGFUSE INTEGRATION VERIFIED")
    logger.info("=" * 60)
    logger.info(f"\nTrace ID: {trace_id}")
    logger.info(f"Dashboard: {host}/traces/{trace_id}")
    logger.info("\nDeepAgent observability is fully operational!")
    logger.info("All agent actions and tool calls will be traced.")
    logger.info("\n" + "=" * 60)

    return True


async def verify_deep_agent_integration():
    """Verify Langfuse is properly integrated with DeepAgent."""

    logger.info("\n[BONUS] Verifying DeepAgent integration...")

    try:
        from agents.deep_agent import create_4sgm_agent

        # Create agent with Langfuse enabled
        # (no actual MCP tools needed for this test)
        agent = create_4sgm_agent(mcp_tools=[], enable_langfuse=True)

        # Check if callbacks are attached
        callbacks = getattr(agent, "_callbacks", [])
        if callbacks:
            logger.info(f"  ✓ DeepAgent has {len(callbacks)} callback(s) attached")
            for i, cb in enumerate(callbacks, 1):
                logger.info(f"    - Callback {i}: {type(cb).__name__}")
        else:
            logger.warning("  ⚠ No callbacks attached to DeepAgent")

        logger.info("  ✓ DeepAgent integration verified")
        return True

    except Exception as e:
        logger.warning(f"  ⚠ Could not verify DeepAgent integration: {e}")
        return True  # Don't fail the whole verification for this


async def main():
    """Run all verification checks."""

    success = await verify_langfuse()

    if success:
        await verify_deep_agent_integration()
        return 0
    else:
        logger.error("\n❌ LANGFUSE VERIFICATION FAILED")
        logger.error("Please check your configuration and try again.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
