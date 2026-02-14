"""
AgentLogger decorator for capturing agent execution.
Wraps agent functions to capture inputs, outputs, timing, and errors.
"""

import asyncio
import functools
import traceback
import copy
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from .log_writer import LogWriter
from .log_config import LogConfig
from .utils import DataSanitizer, SanitizationConfig


# Type variable for generic function wrapping
F = TypeVar('F', bound=Callable[..., Any])


class AgentLogger:
    """
    Decorator class for logging agent execution.
    Captures input/output state, timing, and errors for agent functions.
    """
    
    def __init__(
        self,
        agent_name: str,
        log_writer: Optional[LogWriter] = None,
        config: Optional[LogConfig] = None,
        sanitization_config: Optional[SanitizationConfig] = None
    ):
        """
        Initialize AgentLogger for a specific agent.
        
        Args:
            agent_name: Name of the agent being logged
            log_writer: LogWriter instance for writing logs
            config: LogConfig instance for configuration
            sanitization_config: Optional custom sanitization configuration
        """
        self.agent_name = agent_name
        self.config = config or LogConfig.from_env()
        self.log_writer = log_writer or LogWriter(self.config)
        
        # Initialize sanitizer if sanitization is enabled
        if self.config.sanitize_sensitive_data:
            self.sanitizer = DataSanitizer(sanitization_config)
        else:
            self.sanitizer = None
        
    def log_execution(self, func: F) -> F:
        """
        Decorator that wraps agent execution to capture logs.
        Works with both sync and async functions.
        
        Args:
            func: The agent function to wrap
            
        Returns:
            Wrapped function that logs execution
        """
        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._log_async_execution(func, *args, **kwargs)
            return cast(F, async_wrapper)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._log_sync_execution(func, *args, **kwargs)
            return cast(F, sync_wrapper)
    
    async def _log_async_execution(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Log execution of an async agent function.
        
        Args:
            func: The async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result from the agent function
        """
        # Extract state from arguments (typically first argument)
        input_state = self._extract_state(args, kwargs)
        
        # Capture start time with microsecond precision
        start_time = datetime.now()
        timestamp_start = start_time.isoformat()
        
        # Initialize result variables
        output_state = None
        error_info = None
        status = "success"
        
        try:
            # Execute the agent function
            result = await func(*args, **kwargs)
            output_state = result
            
        except Exception as e:
            # Capture error details
            status = "error"
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            
            # Re-raise the exception to maintain existing error handling
            raise
            
        finally:
            # Capture end time and calculate duration
            end_time = datetime.now()
            timestamp_end = end_time.isoformat()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log the execution
            await self._log_agent_call(
                agent_name=self.agent_name,
                input_state=input_state,
                output_state=output_state,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                duration_ms=duration_ms,
                status=status,
                error=error_info
            )
        
        return output_state
    
    def _log_sync_execution(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Log execution of a sync agent function.
        
        Args:
            func: The sync function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result from the agent function
        """
        # Extract state from arguments
        input_state = self._extract_state(args, kwargs)
        
        # Capture start time with microsecond precision
        start_time = datetime.now()
        timestamp_start = start_time.isoformat()
        
        # Initialize result variables
        output_state = None
        error_info = None
        status = "success"
        
        try:
            # Execute the agent function
            result = func(*args, **kwargs)
            output_state = result
            
        except Exception as e:
            # Capture error details
            status = "error"
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            
            # Re-raise the exception to maintain existing error handling
            raise
            
        finally:
            # Capture end time and calculate duration
            end_time = datetime.now()
            timestamp_end = end_time.isoformat()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Schedule async log write
            asyncio.create_task(
                self._log_agent_call(
                    agent_name=self.agent_name,
                    input_state=input_state,
                    output_state=output_state,
                    timestamp_start=timestamp_start,
                    timestamp_end=timestamp_end,
                    duration_ms=duration_ms,
                    status=status,
                    error=error_info
                )
            )
        
        return output_state
    
    def _extract_state(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """
        Extract state dictionary from function arguments.
        
        Args:
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            State dictionary (shallow copy)
        """
        # Try to find state in arguments
        state = None
        
        # Check first positional argument
        if args and isinstance(args[0], dict):
            state = args[0]
        # Check 'state' keyword argument
        elif 'state' in kwargs:
            state = kwargs['state']
        # Check other common parameter names
        elif 'input_state' in kwargs:
            state = kwargs['input_state']
        
        # Return shallow copy to avoid capturing references
        if state is not None:
            return self._create_state_snapshot(state)
        
        return {}
    
    def _create_state_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a snapshot of the state for logging.
        Uses shallow copy for performance, with special handling for nested structures.
        
        Args:
            state: The state dictionary to snapshot
            
        Returns:
            Snapshot of the state
        """
        try:
            # For DEBUG level, create a deep copy
            if self.config.log_level == "DEBUG":
                return copy.deepcopy(state)
            else:
                # For other levels, use shallow copy for performance
                return copy.copy(state)
        except Exception as e:
            # If copying fails, return a minimal representation
            return {
                "_snapshot_error": f"Failed to create snapshot: {str(e)}",
                "_keys": list(state.keys()) if isinstance(state, dict) else []
            }
    
    async def _log_agent_call(
        self,
        agent_name: str,
        input_state: Dict[str, Any],
        output_state: Optional[Dict[str, Any]],
        timestamp_start: str,
        timestamp_end: str,
        duration_ms: float,
        status: str,
        error: Optional[Dict[str, str]] = None
    ):
        """
        Internal method to log agent execution.
        
        Args:
            agent_name: Name of the agent
            input_state: Input state snapshot
            output_state: Output state snapshot
            timestamp_start: ISO format start timestamp
            timestamp_end: ISO format end timestamp
            duration_ms: Execution duration in milliseconds
            status: Execution status ('success' or 'error')
            error: Error information if status is 'error'
        """
        try:
            # Sanitize input and output states if sanitization is enabled
            if self.sanitizer:
                input_state = self.sanitizer.sanitize(input_state)
                output_state = self.sanitizer.sanitize(output_state) if output_state else None
            
            # Extract session_id from input state
            session_id = input_state.get('session_id', 'unknown')
            
            # Build log entry
            log_entry = {
                "session_id": session_id,
                "agent_name": agent_name,
                "timestamp_start": timestamp_start,
                "timestamp_end": timestamp_end,
                "duration_ms": round(duration_ms, 3),
                "status": status,
                "metadata": {
                    "log_level": self.config.log_level,
                    "sanitized": self.sanitizer is not None
                }
            }
            
            # Add input/output state based on log level
            if self.config.log_level == "DEBUG":
                log_entry["input_state"] = input_state
                log_entry["output_state"] = output_state
            elif self.config.log_level == "INFO":
                # Include summary information only
                log_entry["input_summary"] = self._create_state_summary(input_state)
                log_entry["output_summary"] = self._create_state_summary(output_state)
            
            # Add error information if present
            if error:
                log_entry["error"] = error
            
            # Write log entry
            if self.config.enable_file_logging or self.config.enable_console_logging:
                await self.log_writer.write_log_entry(
                    session_id=session_id,
                    log_entry=log_entry,
                    format=self.config.log_format
                )
            
            # Console logging if enabled
            if self.config.enable_console_logging:
                self._log_to_console(log_entry)
                
        except Exception as e:
            # Graceful degradation: log to stderr but don't block execution
            print(f"Error in agent logging: {e}", flush=True)
            traceback.print_exc()
    
    def _create_state_summary(self, state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a summary of state for INFO level logging.
        
        Args:
            state: The state dictionary
            
        Returns:
            Summary dictionary with key counts and types
        """
        if state is None:
            return {"_empty": True}
        
        if not isinstance(state, dict):
            return {"_type": type(state).__name__}
        
        summary = {
            "_key_count": len(state),
            "_keys": list(state.keys())
        }
        
        # Add counts for common collection fields
        for key, value in state.items():
            if isinstance(value, list):
                summary[f"{key}_count"] = len(value)
            elif isinstance(value, dict):
                summary[f"{key}_keys"] = len(value)
        
        return summary
    
    def _log_to_console(self, log_entry: Dict[str, Any]):
        """
        Log entry to console for debugging.
        
        Args:
            log_entry: The log entry to print
        """
        agent_name = log_entry.get('agent_name', 'unknown')
        status = log_entry.get('status', 'unknown')
        duration = log_entry.get('duration_ms', 0)
        
        status_symbol = "✓" if status == "success" else "✗"
        print(
            f"[AgentLogger] {status_symbol} {agent_name}: {duration:.2f}ms ({status})",
            flush=True
        )
        
        if log_entry.get('error'):
            error = log_entry['error']
            print(f"  Error: {error.get('type')}: {error.get('message')}", flush=True)
