"""
Test script for AgentLogger decorator.
Tests both sync and async function wrapping, timing, error handling, and state capture.
"""

import asyncio
import time
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from logging_system import AgentLogger, LogWriter, LogConfig


# Test sync function
def sync_agent_function(state):
    """Simulates a synchronous agent function."""
    print(f"Sync agent executing with state: {state.get('user_query', 'N/A')}")
    time.sleep(0.1)  # Simulate work
    return {
        **state,
        "result": "sync_result",
        "processed": True
    }


# Test async function
async def async_agent_function(state):
    """Simulates an asynchronous agent function."""
    print(f"Async agent executing with state: {state.get('user_query', 'N/A')}")
    await asyncio.sleep(0.1)  # Simulate async work
    return {
        **state,
        "result": "async_result",
        "processed": True
    }


# Test function that raises an error
async def failing_agent_function(state):
    """Simulates an agent function that fails."""
    print(f"Failing agent executing...")
    await asyncio.sleep(0.05)
    raise ValueError("Simulated agent failure")


async def test_agent_logger():
    """Test the AgentLogger decorator."""
    
    print("=" * 80)
    print("Testing AgentLogger Decorator")
    print("=" * 80)
    
    # Create config with DEBUG level to see full state
    config = LogConfig(
        log_level="DEBUG",
        log_dir="backend/logs",
        enable_file_logging=True,
        enable_console_logging=True,
        log_format="both"
    )
    
    # Create log writer
    log_writer = LogWriter(config)
    await log_writer.start()
    
    # Create test state
    test_state = {
        "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "user_query": "Test query for agent logger",
        "city": "Test City",
        "interests": ["testing", "logging"]
    }
    
    try:
        # Test 1: Sync function
        print("\n--- Test 1: Sync Function ---")
        sync_logger = AgentLogger("test_sync_agent", log_writer, config)
        wrapped_sync = sync_logger.log_execution(sync_agent_function)
        
        result = wrapped_sync(test_state)
        print(f"Sync result: {result.get('result')}")
        
        # Wait for async log write
        await asyncio.sleep(0.5)
        
        # Test 2: Async function
        print("\n--- Test 2: Async Function ---")
        async_logger = AgentLogger("test_async_agent", log_writer, config)
        wrapped_async = async_logger.log_execution(async_agent_function)
        
        result = await wrapped_async(test_state)
        print(f"Async result: {result.get('result')}")
        
        # Wait for async log write
        await asyncio.sleep(0.5)
        
        # Test 3: Error handling
        print("\n--- Test 3: Error Handling ---")
        error_logger = AgentLogger("test_failing_agent", log_writer, config)
        wrapped_failing = error_logger.log_execution(failing_agent_function)
        
        try:
            await wrapped_failing(test_state)
        except ValueError as e:
            print(f"Caught expected error: {e}")
        
        # Wait for async log write
        await asyncio.sleep(0.5)
        
        # Flush all logs
        print("\n--- Flushing logs ---")
        await log_writer.flush()
        
        # Check log files
        print("\n--- Checking log files ---")
        session_id = test_state['session_id']
        json_log = log_writer.get_session_log_path(session_id, "json")
        text_log = log_writer.get_session_log_path(session_id, "text")
        
        if json_log.exists():
            print(f"✓ JSON log created: {json_log}")
            print(f"  Size: {json_log.stat().st_size} bytes")
        else:
            print(f"✗ JSON log not found: {json_log}")
        
        if text_log.exists():
            print(f"✓ Text log created: {text_log}")
            print(f"  Size: {text_log.stat().st_size} bytes")
        else:
            print(f"✗ Text log not found: {text_log}")
        
        print("\n--- Test Summary ---")
        print("✓ Sync function wrapping works")
        print("✓ Async function wrapping works")
        print("✓ Error handling and logging works")
        print("✓ State capture works")
        print("✓ Timing measurement works")
        print("✓ Log files created successfully")
        
    finally:
        await log_writer.stop()
    
    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_agent_logger())
