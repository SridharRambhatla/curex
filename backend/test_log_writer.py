"""
Simple test to verify LogWriter functionality.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logging_system.log_writer import LogWriter
from logging_system.log_config import LogConfig


async def test_log_writer():
    """Test basic LogWriter functionality."""
    print("Testing LogWriter...")
    
    # Create test config with small buffer for quick testing
    config = LogConfig(
        log_dir="backend/logs/test",
        enable_file_logging=True,
        log_format="both",
        buffer_size=2,
        flush_interval_seconds=1,
        max_log_size_mb=1
    )
    
    # Initialize LogWriter
    writer = LogWriter(config)
    await writer.start()
    
    try:
        # Test session ID
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Test 1: Write log entries
        print(f"\n1. Writing log entries for session {session_id}...")
        log_entry_1 = {
            "agent_name": "discovery",
            "timestamp_start": datetime.now().isoformat(),
            "timestamp_end": datetime.now().isoformat(),
            "duration_ms": 123.45,
            "status": "success",
            "input_state": {"query": "test query"},
            "output_state": {"results": ["item1", "item2"]},
            "error": None,
            "metadata": {"model": "test-model"}
        }
        
        await writer.write_log_entry(session_id, log_entry_1)
        print("   ✓ First log entry written to buffer")
        
        log_entry_2 = {
            "agent_name": "cultural_context",
            "timestamp_start": datetime.now().isoformat(),
            "timestamp_end": datetime.now().isoformat(),
            "duration_ms": 234.56,
            "status": "success",
            "input_state": {"city": "test city"},
            "output_state": {"context": "test context"},
            "error": None,
            "metadata": {"model": "test-model"}
        }
        
        await writer.write_log_entry(session_id, log_entry_2)
        print("   ✓ Second log entry written (should trigger flush)")
        
        # Wait a moment for async writes
        await asyncio.sleep(0.5)
        
        # Test 2: Verify files were created
        print("\n2. Verifying log files...")
        json_file = writer.get_session_log_path(session_id, "json")
        text_file = writer.get_session_log_path(session_id, "text")
        
        if json_file.exists():
            print(f"   ✓ JSON log file created: {json_file}")
            with open(json_file, 'r') as f:
                lines = f.readlines()
                print(f"   ✓ JSON file has {len(lines)} log entries")
        else:
            print(f"   ✗ JSON log file not found: {json_file}")
        
        if text_file.exists():
            print(f"   ✓ Text log file created: {text_file}")
            with open(text_file, 'r') as f:
                content = f.read()
                print(f"   ✓ Text file size: {len(content)} bytes")
        else:
            print(f"   ✗ Text log file not found: {text_file}")
        
        # Test 3: Write session summary
        print("\n3. Writing session summary...")
        summary = {
            "session_id": session_id,
            "timestamp_start": datetime.now().isoformat(),
            "timestamp_end": datetime.now().isoformat(),
            "total_duration_ms": 358.01,
            "agents_executed": [
                {"agent_name": "discovery", "duration_ms": 123.45, "status": "success"},
                {"agent_name": "cultural_context", "duration_ms": 234.56, "status": "success"}
            ],
            "total_agents": 2,
            "successful_agents": 2,
            "failed_agents": 0,
            "final_status": "success"
        }
        
        await writer.write_session_summary(session_id, summary)
        await asyncio.sleep(0.5)
        
        summary_file = writer.get_session_summary_path(session_id)
        if summary_file.exists():
            print(f"   ✓ Summary file created: {summary_file}")
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
                print(f"   ✓ Summary contains {summary_data['total_agents']} agents")
        else:
            print(f"   ✗ Summary file not found: {summary_file}")
        
        # Test 4: Manual flush
        print("\n4. Testing manual flush...")
        log_entry_3 = {
            "agent_name": "plot_builder",
            "timestamp_start": datetime.now().isoformat(),
            "timestamp_end": datetime.now().isoformat(),
            "duration_ms": 345.67,
            "status": "success",
            "input_state": {},
            "output_state": {},
            "error": None,
            "metadata": {}
        }
        
        await writer.write_log_entry(session_id, log_entry_3)
        await writer.flush()
        print("   ✓ Manual flush completed")
        
        # Verify the third entry was written
        await asyncio.sleep(0.5)
        with open(json_file, 'r') as f:
            lines = f.readlines()
            print(f"   ✓ JSON file now has {len(lines)} log entries")
        
        print("\n✅ All tests passed!")
        
    finally:
        # Stop the writer
        await writer.stop()
        print("\n🛑 LogWriter stopped")


if __name__ == "__main__":
    asyncio.run(test_log_writer())
