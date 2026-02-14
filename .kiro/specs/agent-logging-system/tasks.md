# Implementation Plan

- [x] 1. Set up logging system directory structure and configuration





  - Create backend/logging_system/ directory with __init__.py
  - Create backend/logs/ directory with .gitignore
  - Create LogConfig class in log_config.py with environment variable loading
  - Add logging configuration to .env.example
  - _Requirements: 4.1, 4.2_

- [ ] 2. Implement core LogWriter for async file I/O




  - Create LogWriter class in log_writer.py with async file operations
  - Implement buffered writing with configurable flush interval
  - Implement log rotation when file size exceeds max_log_size_mb
  - Add thread-safe write operations for parallel agent execution
  - Implement session summary writing
  - _Requirements: 8.1, 8.2, 8.4, 8.5, 3.5_


- [x] 3. Implement AgentLogger decorator for capturing agent execution



  - Create AgentLogger class in agent_logger.py
  - Implement log_execution decorator that works with both sync and async functions
  - Capture input state snapshot before agent execution
  - Capture output state snapshot after agent execution
  - Measure execution time with microsecond precision
  - Handle exceptions and log error details with traceback
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_
-

- [-] 4. Implement sensitive data sanitization


  - Create sanitization utilities in utils.py
  - Implement pattern matching for API keys, secrets, tokens
  - Implement email and phone number sanitization
  - Add configurable sanitization rules
  - Apply sanitization to both input and output states before logging
  - _Requirements: 3.4_

- [-] 5. Implement log formatting and output



  - Create JSON formatter for structured logs
  - Create human-readable text formatter
  - Implement dual-format output (both JSON and text)
  - Add metadata fields to log entries (session_id, agent_name, timestamps, etc.)
  - Implement session summary formatting
  - _Requirements: 3.1, 3.2, 3.3, 1.4, 1.5_



- [ ] 6. Implement LogRetriever for querying logs

  - Create LogRetriever class in log_retriever.py
  - Implement get_session_logs with filtering by agent and status
  - Implement session log parsing from JSON files

  - Add error handling for missing or corrupted log files
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 7. Implement flow visualization and Mermaid diagram generation

  - Add get_agent_flow method to LogRetriever
  - Implement Mermaid diagram generation from session logs
  - Show execution order and timing in diagram
  - Indicate parallel execution in diagram
  - Highlight failed agents with different styling
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 8. Implement session comparison functionality
  - Add compare_sessions method to LogRetriever
  - Implement field-level comparison between sessions
  - Generate comparison report in JSON format
  - Add CSV export option for comparison reports
  - Highlight differences in agent outputs
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 9. Integrate logging into coordinator and agents
  - Initialize LogWriter and AgentLogger instances in coordinator.py
  - Wrap run_discovery_agent with @agent_logger.log_execution decorator
  - Wrap run_cultural_context with decorator
  - Wrap run_community with decorator
  - Wrap run_plot_builder with decorator
  - Wrap run_budget_optimizer with decorator
  - Add session summary logging at workflow completion
  - Track parallel execution metadata for cultural_context and community agents
  - _Requirements: 2.3, 2.4, 2.5_

- [ ] 10. Add API endpoint for log retrieval
  - Add /api/agent-logs/{session_id} GET endpoint to main.py
  - Support query parameters for agent and status filtering
  - Support format parameter (json, text, mermaid)
  - Return session logs in requested format
  - Add error handling for invalid session_id
  - _Requirements: 5.1, 5.2, 5.3, 6.5_

- [ ] 11. Implement log cleanup and retention management
  - Create background task for log cleanup
  - Implement retention policy based on AGENT_LOG_RETENTION_DAYS
  - Add disk space monitoring and warnings
  - Implement safe deletion with error handling
  - _Requirements: 3.5_

- [ ] 12. Add logging configuration to environment setup
  - Update .env.example with all logging environment variables
  - Add logging configuration section to README or docs
  - Set sensible defaults for development and production
  - Document all configuration options
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 13. Write unit tests for logging components
  - Write tests for LogConfig environment variable loading
  - Write tests for LogWriter async operations and buffering
  - Write tests for AgentLogger decorator with sync and async functions
  - Write tests for sanitization utilities
  - Write tests for LogRetriever query methods
  - Write tests for Mermaid diagram generation
  - Write tests for session comparison
  - _Requirements: All requirements_

- [ ] 14. Write integration tests for end-to-end logging
  - Test complete workflow with logging enabled
  - Test parallel agent execution logging
  - Test log file creation and formatting
  - Test session summary generation
  - Test log retrieval API endpoint
  - _Requirements: All requirements_

- [ ] 15. Create validation script for testing agent flow
  - Create standalone script to run test requests through the system
  - Automatically retrieve and display logs for each test session
  - Generate Mermaid diagrams for visual validation
  - Compare multiple test runs to validate consistency
  - Output validation report showing all agent inputs/outputs
  - _Requirements: 1.1, 1.2, 5.1, 6.1, 7.1_
