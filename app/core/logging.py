"""
Logging configuration for the IoT Management Platform
"""
import logging
import sys
from typing import Any, Dict, Optional

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create a logger for the application
logger = logging.getLogger("iot_platform")

# Set the logger level
logger.setLevel(logging.INFO)

class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter to add context to log messages"""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add context to log messages"""
        context = kwargs.pop("context", {})
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            msg = f"{msg} [{context_str}]"
        return msg, kwargs

# Create a logger adapter for adding context
def get_logger_with_context(context: Optional[Dict[str, Any]] = None) -> LoggerAdapter:
    """Get a logger with added context"""
    return LoggerAdapter(logger, {"context": context or {}})

# Export the logger
__all__ = ["logger", "get_logger_with_context"]
