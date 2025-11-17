"""Error handling utilities for the MCP server."""

import logging
import traceback
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def handle_exception(e: Exception, context: Optional[Dict[str, Any]] = None):
    """Handle exceptions with logging and context.

    Args:
        e: The exception to handle
        context: Additional context information
    """
    context = context or {}
    error_info = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc(),
        **context
    }

    logger.error(f"Exception occurred: {error_info}")

    # Log to stderr for debugging
    import sys
    print(f"ERROR: {error_info}", file=sys.stderr)
