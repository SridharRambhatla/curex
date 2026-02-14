"""
Configuration management for the Agent Logging System.
"""

import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class LogConfig:
    """Configuration for the Agent Logging System."""
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: str = "backend/logs"
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    log_format: Literal["json", "text", "both"] = "json"
    sanitize_sensitive_data: bool = True
    max_log_size_mb: int = 100
    buffer_size: int = 10
    flush_interval_seconds: int = 5
    retention_days: int = 30
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        """
        Load configuration from environment variables.
        
        Returns:
            LogConfig instance with values from environment or defaults
        """
        return cls(
            log_level=os.getenv("AGENT_LOG_LEVEL", "INFO").upper(),
            log_dir=os.getenv("AGENT_LOG_DIR", "backend/logs"),
            enable_file_logging=os.getenv("AGENT_LOG_FILE_ENABLED", "true").lower() == "true",
            enable_console_logging=os.getenv("AGENT_LOG_CONSOLE_ENABLED", "true").lower() == "true",
            log_format=os.getenv("AGENT_LOG_FORMAT", "json").lower(),
            sanitize_sensitive_data=os.getenv("AGENT_LOG_SANITIZE", "true").lower() == "true",
            max_log_size_mb=int(os.getenv("AGENT_LOG_MAX_SIZE_MB", "100")),
            buffer_size=int(os.getenv("AGENT_LOG_BUFFER_SIZE", "10")),
            flush_interval_seconds=int(os.getenv("AGENT_LOG_FLUSH_INTERVAL", "5")),
            retention_days=int(os.getenv("AGENT_LOG_RETENTION_DAYS", "30")),
        )
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"log_level must be one of {valid_log_levels}, got {self.log_level}")
        
        valid_formats = ["json", "text", "both"]
        if self.log_format not in valid_formats:
            raise ValueError(f"log_format must be one of {valid_formats}, got {self.log_format}")
        
        if self.max_log_size_mb <= 0:
            raise ValueError(f"max_log_size_mb must be positive, got {self.max_log_size_mb}")
        
        if self.buffer_size <= 0:
            raise ValueError(f"buffer_size must be positive, got {self.buffer_size}")
        
        if self.flush_interval_seconds <= 0:
            raise ValueError(f"flush_interval_seconds must be positive, got {self.flush_interval_seconds}")
        
        if self.retention_days <= 0:
            raise ValueError(f"retention_days must be positive, got {self.retention_days}")
