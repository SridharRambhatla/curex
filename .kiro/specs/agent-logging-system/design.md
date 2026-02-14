# Agent Logging System — Design Document

## Overview

The Agent Logging System provides comprehensive observability for the Sidequest multi-agent architecture. It captures the complete execution flow of requests through the supervisor pattern, logging inputs, outputs, timing, and errors for each agent. The system is designed to be non-intrusive, performant, and easy to use for debugging and validation.

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Coordinator                              │
│                  (Supervisor Agent)                         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   AgentLogger        │
         │   (Decorator/Wrapper)│
         └──────────┬───────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Discovery│ │Cultural │ │Community│
   │  Agent  │ │ Context │ │  Agent  │
   └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
         ┌──────────────────────┐
         │   LogWriter          │
         │   (Async File I/O)   │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   backend/logs/      │
         │   - session_*.json   │
         │   - session_*.txt    │
         │   - agent_flow.log   │
         └──────────────────────┘
```

### Component Interaction Flow

1. **Request Initiation**: Coordinator receives request, creates session_id
2. **Agent Wrapping**: Each agent call is wrapped by AgentLogger decorator
3. **Pre-Execution**: AgentLogger captures input state and start time
4. **Agent Execution**: Agent runs normally (no modification needed)
5. **Post-Execution**: AgentLogger captures output, end time, and status
6. **Async Write**: LogWriter queues log entry for async file write
7. **Log Storage**: Logs written to session-specific files in backend/logs/

## Components and Interfaces

### 1. AgentLogger (Core Logging Decorator)

**Purpose**: Wraps agent functions to capture execution metadata

**Interface**:
```python
class AgentLogger:
    def __init__(self, agent_name: str, log_level: str = "INFO"):
        """Initialize logger for a specific agent"""
        
    def log_execution(self, func: Callable) -> Callable:
        """Decorator that wraps agent execution"""
        
    async def _log_agent_call(
        self,
        agent_name: str,
        input_state: dict,
        output_state: dict,
        duration_ms: float,
        status: str,
        error: Optional[Exception] = None
    ):
        """Internal method to log agent execution"""
```

**Key Features**:
- Decorator pattern for non-intrusive integration
- Captures input/output state snapshots
- Measures execution time with microsecond precision
- Handles both sync and async agent functions
- Sanitizes sensitive data before logging

### 2. LogWriter (Async File I/O Manager)

**Purpose**: Handles asynchronous writing of logs to disk

**Interface**:
```python
class LogWriter:
    def __init__(self, log_dir: str = "backend/logs"):
        """Initialize log writer with directory"""
        
    async def write_log_entry(
        self,
        session_id: str,
        log_entry: dict,
        format: str = "json"
    ):
        """Write a single log entry asynchronously"""
        
    async def write_session_summary(
        self,
        session_id: str,
        summary: dict
    ):
        """Write session summary after workflow completion"""
        
    def flush(self):
        """Force flush all buffered logs"""
```

**Key Features**:
- Async I/O using asyncio for non-blocking writes
- Buffered writes (flush every 10 entries or 5 seconds)
- Automatic log rotation (max 100MB per file)
- Creates log directory if it doesn't exist
- Thread-safe for parallel agent execution

### 3. LogRetriever (Query Interface)

**Purpose**: Provides API for retrieving and analyzing logs

**Interface**:
```python
class LogRetriever:
    def __init__(self, log_dir: str = "backend/logs"):
        """Initialize log retriever"""
        
    def get_session_logs(
        self,
        session_id: str,
        agent_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[dict]:
        """Retrieve logs for a specific session"""
        
    def get_agent_flow(self, session_id: str) -> dict:
        """Get execution flow diagram data"""
        
    def compare_sessions(
        self,
        session_ids: List[str],
        fields: Optional[List[str]] = None
    ) -> dict:
        """Compare logs across multiple sessions"""
        
    def generate_mermaid_diagram(self, session_id: str) -> str:
        """Generate Mermaid flow diagram"""
```

**Key Features**:
- Fast session lookup using file indexing
- Filter by agent name or status
- Generate flow diagrams in Mermaid format
- Compare sessions for regression testing
- Export to JSON, CSV, or text formats

### 4. LogConfig (Configuration Manager)

**Purpose**: Centralized configuration for logging behavior

**Interface**:
```python
class LogConfig:
    log_level: str  # DEBUG, INFO, WARNING, ERROR
    log_dir: str
    enable_file_logging: bool
    enable_console_logging: bool
    log_format: str  # json, text, both
    sanitize_sensitive_data: bool
    max_log_size_mb: int
    buffer_size: int
    flush_interval_seconds: int
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        """Load configuration from environment variables"""
```

**Environment Variables**:
```bash
AGENT_LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
AGENT_LOG_DIR=backend/logs        # Log directory path
AGENT_LOG_FILE_ENABLED=true       # Enable file logging
AGENT_LOG_CONSOLE_ENABLED=true    # Enable console logging
AGENT_LOG_FORMAT=json             # json, text, both
AGENT_LOG_SANITIZE=true           # Sanitize sensitive data
AGENT_LOG_MAX_SIZE_MB=100         # Max log file size
AGENT_LOG_BUFFER_SIZE=10          # Buffer size for writes
AGENT_LOG_FLUSH_INTERVAL=5        # Flush interval in seconds
```

## Data Models

### LogEntry Schema

```python
{
    "session_id": "uuid-string",
    "agent_name": "discovery" | "cultural_context" | "community" | "plot_builder" | "budget_optimizer",
    "timestamp_start": "2026-02-14T10:30:00.123456",
    "timestamp_end": "2026-02-14T10:30:02.456789",
    "duration_ms": 2333.333,
    "status": "success" | "error" | "timeout",
    "input_state": {
        "user_query": "...",
        "city": "...",
        // ... (sanitized state)
    },
    "output_state": {
        "discovered_experiences": [...],
        // ... (sanitized state)
    },
    "error": {
        "type": "ValueError",
        "message": "...",
        "traceback": "..."
    } | null,
    "metadata": {
        "model": "gemini-2.0-flash",
        "parallel_execution": false,
        "retry_count": 0
    }
}
```

### SessionSummary Schema

```python
{
    "session_id": "uuid-string",
    "timestamp_start": "2026-02-14T10:30:00.000000",
    "timestamp_end": "2026-02-14T10:30:15.000000",
    "total_duration_ms": 15000.0,
    "user_query": "...",
    "city": "...",
    "agents_executed": [
        {
            "agent_name": "discovery",
            "duration_ms": 2333.333,
            "status": "success",
            "order": 1
        },
        {
            "agent_name": "cultural_context",
            "duration_ms": 1500.0,
            "status": "success",
            "order": 2,
            "parallel_with": ["community"]
        },
        // ...
    ],
    "total_agents": 5,
    "successful_agents": 5,
    "failed_agents": 0,
    "experiences_found": 8,
    "final_status": "success" | "partial_success" | "error"
}
```

## Integration Points

### 1. Coordinator Integration

Modify `backend/agents/coordinator.py` to initialize logging:

```python
from logging_system.agent_logger import AgentLogger
from logging_system.log_writer import LogWriter

# Initialize at module level
log_writer = LogWriter()
discovery_logger = AgentLogger("discovery", log_writer)
cultural_logger = AgentLogger("cultural_context", log_writer)
# ... etc

# Wrap agent calls
@discovery_logger.log_execution
def run_discovery(state):
    # existing code
    pass
```

### 2. Agent Function Wrapping

Each agent function gets wrapped with minimal changes:

**Before**:
```python
def run_discovery_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # agent logic
    return result
```

**After**:
```python
@agent_logger.log_execution
def run_discovery_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # agent logic (unchanged)
    return result
```

### 3. API Endpoint for Log Retrieval

Add endpoint to `backend/main.py`:

```python
from logging_system.log_retriever import LogRetriever

log_retriever = LogRetriever()

@app.get("/api/agent-logs/{session_id}")
async def get_agent_logs(
    session_id: str,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    format: str = "json"
):
    """Retrieve logs for a session"""
    logs = log_retriever.get_session_logs(
        session_id,
        agent_filter=agent,
        status_filter=status
    )
    
    if format == "mermaid":
        return {"diagram": log_retriever.generate_mermaid_diagram(session_id)}
    
    return {"session_id": session_id, "logs": logs}
```

## File Structure

```
backend/
├── logging_system/
│   ├── __init__.py
│   ├── agent_logger.py       # AgentLogger class
│   ├── log_writer.py         # LogWriter class
│   ├── log_retriever.py      # LogRetriever class
│   ├── log_config.py         # LogConfig class
│   └── utils.py              # Sanitization, formatting utils
├── logs/
│   ├── session_<uuid>.json   # Per-session JSON logs
│   ├── session_<uuid>.txt    # Per-session human-readable logs
│   ├── agent_flow.log        # Consolidated flow log
│   └── .gitignore            # Ignore log files in git
└── agents/
    └── coordinator.py        # Modified to use logging
```

## Error Handling

### Agent Execution Errors

1. **Capture**: AgentLogger catches all exceptions from wrapped functions
2. **Log**: Full error details logged including traceback
3. **Propagate**: Exception re-raised to maintain existing error handling
4. **Status**: Log entry marked with status="error"

### Logging System Errors

1. **Graceful Degradation**: If logging fails, agent execution continues
2. **Error Logging**: Logging errors written to stderr
3. **Fallback**: If file logging fails, fall back to console only
4. **No Blocking**: Logging errors never block agent execution

### Disk Space Management

1. **Log Rotation**: Automatic rotation at 100MB per file
2. **Retention**: Keep last 30 days of logs by default
3. **Cleanup**: Background task to remove old logs
4. **Monitoring**: Log warning when disk space < 1GB

## Testing Strategy

### Unit Tests

1. **AgentLogger Tests**
   - Test decorator wrapping sync/async functions
   - Test input/output capture
   - Test timing measurement accuracy
   - Test error handling and propagation
   - Test sensitive data sanitization

2. **LogWriter Tests**
   - Test async file writing
   - Test buffering and flushing
   - Test log rotation
   - Test concurrent writes (parallel agents)
   - Test directory creation

3. **LogRetriever Tests**
   - Test session log retrieval
   - Test filtering by agent/status
   - Test Mermaid diagram generation
   - Test session comparison
   - Test export formats

4. **LogConfig Tests**
   - Test environment variable loading
   - Test default values
   - Test validation

### Integration Tests

1. **End-to-End Workflow Test**
   - Run complete workflow with logging enabled
   - Verify all agents logged correctly
   - Verify session summary generated
   - Verify log files created

2. **Parallel Execution Test**
   - Test logging during parallel agent execution
   - Verify no race conditions
   - Verify correct execution order captured

3. **Performance Test**
   - Measure logging overhead (should be < 5ms per agent)
   - Test with logging disabled (should be 0ms overhead)
   - Test async write performance

### Validation Tests

1. **Log Integrity Test**
   - Verify all log entries have required fields
   - Verify timestamps are sequential
   - Verify session_id consistency

2. **Sanitization Test**
   - Verify API keys removed from logs
   - Verify sensitive user data sanitized
   - Verify sanitization doesn't break JSON

## Performance Considerations

### Overhead Targets

- **Logging Enabled (INFO)**: < 5ms per agent call
- **Logging Enabled (DEBUG)**: < 20ms per agent call
- **Logging Disabled**: 0ms overhead (decorator check only)
- **Async Write**: Non-blocking, < 10ms to queue

### Optimization Strategies

1. **Lazy Serialization**: Only serialize state when log level requires it
2. **Shallow Copies**: Use shallow copies for state snapshots
3. **Buffered Writes**: Buffer 10 entries before flushing
4. **Async I/O**: All file writes are async
5. **Conditional Logging**: Skip expensive operations when log level doesn't require them

### Memory Management

1. **Buffer Limits**: Max 100 entries in memory buffer
2. **State Snapshots**: Use shallow copies to avoid deep copy overhead
3. **Log Rotation**: Prevent unbounded log file growth
4. **Cleanup**: Background task to remove old logs

## Security Considerations

### Sensitive Data Sanitization

Automatically sanitize these fields from logs:
- `GOOGLE_API_KEY`
- `GOOGLE_CLOUD_PROJECT` (partial masking)
- User email addresses
- Phone numbers
- Payment information
- Any field matching pattern `*_key`, `*_secret`, `*_token`

### Access Control

- Log files stored in backend/logs/ (not publicly accessible)
- API endpoint requires authentication (future: add auth middleware)
- No sensitive data in log filenames
- Logs excluded from git via .gitignore

### Data Retention

- Default retention: 30 days
- Configurable via `AGENT_LOG_RETENTION_DAYS`
- Automatic cleanup of old logs
- Option to archive logs before deletion

## Deployment Considerations

### Environment Setup

1. Create logs directory: `mkdir -p backend/logs`
2. Set environment variables in `.env`
3. Ensure write permissions for log directory
4. Configure log rotation in production

### Production Configuration

Recommended settings for production:
```bash
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE_ENABLED=true
AGENT_LOG_CONSOLE_ENABLED=false
AGENT_LOG_FORMAT=json
AGENT_LOG_SANITIZE=true
AGENT_LOG_MAX_SIZE_MB=100
AGENT_LOG_RETENTION_DAYS=30
```

### Monitoring

- Monitor log directory disk usage
- Alert if logging fails for > 5 minutes
- Track logging overhead in APM
- Monitor log file sizes

## Future Enhancements

1. **Structured Logging**: Integrate with ELK stack or CloudWatch
2. **Real-time Streaming**: WebSocket endpoint for live log streaming
3. **Log Analytics**: Built-in analytics dashboard
4. **Distributed Tracing**: OpenTelemetry integration
5. **Log Compression**: Compress old logs to save space
6. **Remote Storage**: Option to store logs in S3/GCS
