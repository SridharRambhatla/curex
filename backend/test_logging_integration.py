"""
Quick test to verify logging integration with agents.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.discovery_agent import run_discovery_agent
from logging_system import start_global_logger, stop_global_logger


async def test_discovery_with_logging():
    """Test that discovery agent logs properly."""
    print("=" * 60)
    print("Testing Discovery Agent with Logging")
    print("=" * 60)
    
    # Start the global logger
    await start_global_logger()
    print("✓ Global logger started\n")
    
    test_state = {
        "session_id": "test_logging_integration",
        "user_query": "I want a solo date idea involving art or crafts",
        "city": "Bangalore",
        "budget_range": (1000, 2500),
        "interest_pods": ["craft_explorer", "art_enthusiast"]
    }
    
    try:
        print("Calling discovery agent...")
        result = run_discovery_agent(test_state)
        
        print(f"\n✓ Agent executed successfully")
        print(f"✓ Found {len(result.get('discovered_experiences', []))} experiences")
        
        # Wait a moment for async logging to complete
        await asyncio.sleep(2)
        
        # Check if log file was created
        log_dir = Path("logs")  # Relative to backend directory
        session_logs = list(log_dir.glob("*test_logging_integration*"))
        
        if session_logs:
            print(f"\n✓ Log files created:")
            for log_file in session_logs:
                print(f"  - {log_file.name} ({log_file.stat().st_size} bytes)")
        else:
            print("\n✗ No log files found")
            print(f"  Checked directory: {log_dir.absolute()}")
        
    finally:
        # Stop the global logger
        await stop_global_logger()
        print("\n✓ Global logger stopped")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_discovery_with_logging())
