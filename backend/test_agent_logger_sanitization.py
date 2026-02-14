"""
Integration test for AgentLogger with sanitization.
"""

import asyncio
import json
import os
from logging_system import AgentLogger, LogConfig, LogWriter


async def test_agent_logger_sanitization():
    """Test that AgentLogger properly sanitizes sensitive data."""
    print("\n=== Testing AgentLogger Sanitization ===")
    
    # Create a test log directory
    test_log_dir = "backend/logs/test_sanitization"
    os.makedirs(test_log_dir, exist_ok=True)
    
    # Create config with sanitization enabled
    config = LogConfig(
        log_level="DEBUG",
        log_dir=test_log_dir,
        enable_file_logging=True,
        enable_console_logging=False,
        log_format="json",
        sanitize_sensitive_data=True,
        max_log_size_mb=10,
        buffer_size=1,
        flush_interval_seconds=1
    )
    
    # Create logger
    log_writer = LogWriter(config)
    agent_logger = AgentLogger("test_agent", log_writer, config)
    
    # Define a test agent function with sensitive data
    @agent_logger.log_execution
    async def test_agent(state):
        """Test agent that processes state."""
        # Simulate some processing
        await asyncio.sleep(0.01)
        
        # Return state with additional sensitive data
        return {
            **state,
            "result": "success",
            "api_response": "Data from API",
            "internal_token": "secret_internal_token_12345"
        }
    
    # Create input state with sensitive data
    input_state = {
        "session_id": "test-session-123",
        "user_query": "Find experiences in Bangalore",
        "api_key": "AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "user_email": "user@example.com",
        "auth_token": "bearer_token_abc123",
        "google_cloud_project": "my-project-id-12345"
    }
    
    # Execute the agent
    print("Executing test agent with sensitive data...")
    result = await test_agent(input_state)
    
    # Wait for log to be written
    await asyncio.sleep(0.5)
    await log_writer.flush()
    
    # Read the log file
    log_file = os.path.join(test_log_dir, "session_test-session-123.json")
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            log_content = f.read()
            log_entries = [json.loads(line) for line in log_content.strip().split('\n')]
        
        print(f"\nFound {len(log_entries)} log entries")
        
        # Check the first log entry
        log_entry = log_entries[0]
        
        print("\n--- Checking Input State Sanitization ---")
        input_state_logged = log_entry.get('input_state', {})
        
        # Verify sensitive fields are redacted
        assert input_state_logged.get('api_key') == "***REDACTED***", \
            f"API key not sanitized: {input_state_logged.get('api_key')}"
        print("✓ api_key sanitized")
        
        assert input_state_logged.get('auth_token') == "***REDACTED***", \
            f"Auth token not sanitized: {input_state_logged.get('auth_token')}"
        print("✓ auth_token sanitized")
        
        # Verify email is sanitized in user_email field
        user_email = input_state_logged.get('user_email', '')
        assert 'user@example.com' not in user_email, \
            f"Email not sanitized: {user_email}"
        assert '[EMAIL_REDACTED]' in user_email, \
            f"Email not properly redacted: {user_email}"
        print("✓ user_email sanitized")
        
        # Verify partial masking for google_cloud_project
        project = input_state_logged.get('google_cloud_project', '')
        assert project.startswith('my-p'), \
            f"Project ID not partially masked correctly: {project}"
        assert project.endswith('2345'), \
            f"Project ID not partially masked correctly: {project}"
        assert '*' in project, \
            f"Project ID not partially masked: {project}"
        print(f"✓ google_cloud_project partially masked: {project}")
        
        # Verify non-sensitive fields are preserved
        assert input_state_logged.get('user_query') == "Find experiences in Bangalore", \
            "Non-sensitive field was modified"
        print("✓ Non-sensitive fields preserved")
        
        print("\n--- Checking Output State Sanitization ---")
        output_state_logged = log_entry.get('output_state', {})
        
        # Verify output sensitive fields are redacted
        assert output_state_logged.get('internal_token') == "***REDACTED***", \
            f"Internal token not sanitized: {output_state_logged.get('internal_token')}"
        print("✓ internal_token sanitized in output")
        
        # Verify non-sensitive output fields are preserved
        assert output_state_logged.get('result') == "success", \
            "Non-sensitive output field was modified"
        print("✓ Non-sensitive output fields preserved")
        
        # Verify metadata indicates sanitization was applied
        metadata = log_entry.get('metadata', {})
        assert metadata.get('sanitized') == True, \
            "Metadata doesn't indicate sanitization was applied"
        print("✓ Metadata indicates sanitization applied")
        
        print("\n" + "="*50)
        print("✓ AgentLogger sanitization integration test passed!")
        print("="*50)
        
    else:
        print(f"✗ Log file not found: {log_file}")
        raise FileNotFoundError(f"Expected log file not created: {log_file}")
    
    # Cleanup
    if os.path.exists(log_file):
        os.remove(log_file)
    if os.path.exists(test_log_dir):
        os.rmdir(test_log_dir)


if __name__ == "__main__":
    print("Running AgentLogger sanitization integration test...")
    
    try:
        asyncio.run(test_agent_logger_sanitization())
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
