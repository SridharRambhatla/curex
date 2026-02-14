"""
LogWriter for async file I/O operations.
Handles buffered writing, log rotation, and thread-safe operations.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import aiofiles
from .log_config import LogConfig


class LogWriter:
    """
    Async log writer with buffering, rotation, and thread-safe operations.
    """
    
    def __init__(self, config: Optional[LogConfig] = None):
        """
        Initialize LogWriter with configuration.
        
        Args:
            config: LogConfig instance, defaults to loading from environment
        """
        self.config = config or LogConfig.from_env()
        self.config.validate()
        
        # Create log directory if it doesn't exist
        self.log_dir = Path(self.config.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Buffer for log entries
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        
        # Background flush task
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Track file sizes for rotation
        self._file_sizes: Dict[str, int] = {}
        
    async def start(self):
        """Start the background flush task."""
        if not self._running:
            self._running = True
            self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def stop(self):
        """Stop the background flush task and flush remaining logs."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
    
    async def write_log_entry(
        self,
        session_id: str,
        log_entry: Dict[str, Any],
        format: str = "json"
    ):
        """
        Write a single log entry asynchronously.
        
        Args:
            session_id: Unique session identifier
            log_entry: Dictionary containing log data
            format: Output format ('json', 'text', or 'both')
        """
        if not self.config.enable_file_logging:
            return
        
        # Use configured format if not specified
        if format == "json":
            format = self.config.log_format
        
        # Add to buffer
        with self._buffer_lock:
            self._buffer.append({
                'session_id': session_id,
                'log_entry': log_entry,
                'format': format
            })
            
            # Flush if buffer is full
            if len(self._buffer) >= self.config.buffer_size:
                await self.flush()
    
    async def write_session_summary(
        self,
        session_id: str,
        summary: Dict[str, Any]
    ):
        """
        Write session summary after workflow completion.
        
        Args:
            session_id: Unique session identifier
            summary: Dictionary containing session summary data
        """
        if not self.config.enable_file_logging:
            return
        
        summary_file = self.log_dir / f"session_{session_id}_summary.json"
        
        # Check if rotation is needed
        await self._rotate_if_needed(summary_file)
        
        # Write summary
        async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            await f.write('\n')
        
        # Update file size tracking
        self._file_sizes[str(summary_file)] = summary_file.stat().st_size
    
    async def flush(self):
        """Force flush all buffered logs to disk."""
        with self._buffer_lock:
            if not self._buffer:
                return
            
            # Copy buffer and clear it
            entries_to_write = self._buffer.copy()
            self._buffer.clear()
        
        # Group entries by session_id and format
        grouped_entries: Dict[tuple, List[Dict[str, Any]]] = {}
        for entry in entries_to_write:
            key = (entry['session_id'], entry['format'])
            if key not in grouped_entries:
                grouped_entries[key] = []
            grouped_entries[key].append(entry['log_entry'])
        
        # Write grouped entries
        for (session_id, format), log_entries in grouped_entries.items():
            if format in ['json', 'both']:
                await self._write_json_logs(session_id, log_entries)
            if format in ['text', 'both']:
                await self._write_text_logs(session_id, log_entries)
    
    async def _write_json_logs(self, session_id: str, log_entries: List[Dict[str, Any]]):
        """Write log entries in JSON format."""
        json_file = self.log_dir / f"session_{session_id}.json"
        
        # Check if rotation is needed
        await self._rotate_if_needed(json_file)
        
        # Append entries to file
        async with aiofiles.open(json_file, 'a', encoding='utf-8') as f:
            for entry in log_entries:
                await f.write(json.dumps(entry, ensure_ascii=False))
                await f.write('\n')
        
        # Update file size tracking
        self._file_sizes[str(json_file)] = json_file.stat().st_size
    
    async def _write_text_logs(self, session_id: str, log_entries: List[Dict[str, Any]]):
        """Write log entries in human-readable text format."""
        text_file = self.log_dir / f"session_{session_id}.txt"
        
        # Check if rotation is needed
        await self._rotate_if_needed(text_file)
        
        # Append entries to file
        async with aiofiles.open(text_file, 'a', encoding='utf-8') as f:
            for entry in log_entries:
                formatted_text = self._format_log_entry_as_text(entry)
                await f.write(formatted_text)
                await f.write('\n' + '='*80 + '\n')
        
        # Update file size tracking
        self._file_sizes[str(text_file)] = text_file.stat().st_size
    
    def _format_log_entry_as_text(self, entry: Dict[str, Any]) -> str:
        """Format a log entry as human-readable text."""
        lines = []
        lines.append(f"Agent: {entry.get('agent_name', 'unknown')}")
        lines.append(f"Status: {entry.get('status', 'unknown')}")
        lines.append(f"Start: {entry.get('timestamp_start', 'N/A')}")
        lines.append(f"End: {entry.get('timestamp_end', 'N/A')}")
        lines.append(f"Duration: {entry.get('duration_ms', 0):.2f}ms")
        
        if entry.get('error'):
            lines.append(f"\nError: {entry['error'].get('type', 'Unknown')}")
            lines.append(f"Message: {entry['error'].get('message', 'N/A')}")
            if entry['error'].get('traceback'):
                lines.append(f"Traceback:\n{entry['error']['traceback']}")
        
        if self.config.log_level == "DEBUG":
            lines.append(f"\nInput State:")
            lines.append(json.dumps(entry.get('input_state', {}), indent=2))
            lines.append(f"\nOutput State:")
            lines.append(json.dumps(entry.get('output_state', {}), indent=2))
        
        return '\n'.join(lines)
    
    async def _rotate_if_needed(self, file_path: Path):
        """
        Rotate log file if it exceeds max size.
        
        Args:
            file_path: Path to the log file to check
        """
        if not file_path.exists():
            return
        
        file_size_bytes = file_path.stat().st_size
        max_size_bytes = self.config.max_log_size_mb * 1024 * 1024
        
        if file_size_bytes >= max_size_bytes:
            # Create rotated filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            rotated_path = file_path.parent / rotated_name
            
            # Rename current file
            file_path.rename(rotated_path)
            
            # Remove from size tracking
            if str(file_path) in self._file_sizes:
                del self._file_sizes[str(file_path)]
    
    async def _periodic_flush(self):
        """Background task to periodically flush the buffer."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but don't crash the flush task
                print(f"Error in periodic flush: {e}", flush=True)
    
    def get_session_log_path(self, session_id: str, format: str = "json") -> Path:
        """
        Get the path to a session log file.
        
        Args:
            session_id: Unique session identifier
            format: Log format ('json' or 'text')
        
        Returns:
            Path to the log file
        """
        if format == "json":
            return self.log_dir / f"session_{session_id}.json"
        elif format == "text":
            return self.log_dir / f"session_{session_id}.txt"
        else:
            raise ValueError(f"Invalid format: {format}")
    
    def get_session_summary_path(self, session_id: str) -> Path:
        """
        Get the path to a session summary file.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Path to the summary file
        """
        return self.log_dir / f"session_{session_id}_summary.json"
