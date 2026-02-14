"""
Global logger instance for the agent logging system.
Provides a singleton LogWriter that can be shared across all agents.
"""

from typing import Optional
from .log_writer import LogWriter
from .log_config import LogConfig

# Global LogWriter instance
_global_log_writer: Optional[LogWriter] = None
_global_log_config: Optional[LogConfig] = None


def get_log_writer() -> LogWriter:
    """
    Get the global LogWriter instance.
    Creates one if it doesn't exist.
    
    Returns:
        LogWriter instance
    """
    global _global_log_writer, _global_log_config
    
    if _global_log_writer is None:
        _global_log_config = LogConfig.from_env()
        _global_log_writer = LogWriter(_global_log_config)
    
    return _global_log_writer


def get_log_config() -> LogConfig:
    """
    Get the global LogConfig instance.
    
    Returns:
        LogConfig instance
    """
    global _global_log_config
    
    if _global_log_config is None:
        _global_log_config = LogConfig.from_env()
    
    return _global_log_config


async def start_global_logger():
    """Start the global LogWriter."""
    log_writer = get_log_writer()
    await log_writer.start()


async def stop_global_logger():
    """Stop the global LogWriter."""
    global _global_log_writer
    
    if _global_log_writer is not None:
        await _global_log_writer.stop()
        _global_log_writer = None
