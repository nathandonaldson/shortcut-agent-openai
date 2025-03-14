# Shortcut Enhancement System Logging Framework

This comprehensive logging framework provides structured, contextual logging for the Shortcut Enhancement System, with full integration with the OpenAI Agent SDK.

## Features

- **Structured JSON Logging**: All logs are formatted as JSON for easy parsing and querying
- **Context-Rich Logs**: Every log entry includes relevant context like workspace ID, story ID, and request ID
- **Trace Correlation**: All logs are correlated with trace and request IDs
- **OpenAI Agent SDK Integration**: Built-in integration with OpenAI Agent SDK for tracking traces, spans, and tools
- **Customizable Log Formats**: Support for both JSON (machine-readable) and text (human-readable) formats
- **Environment-Aware**: Different log configurations for development and production
- **Log Viewer**: Included utility for viewing and filtering logs with color-coded output
- **Real-Time Log Following**: Tool for following logs in real-time during webhook processing

## Core Components

The logging system is composed of the following components:

- `logger.py`: Core logging implementation with structured logger and trace context
- `webhook.py`: Webhook-specific logging utilities
- `agent.py`: Agent-specific logging utilities for tracing agent execution
- `trace_processor.py`: OpenAI Agent SDK trace processor implementation
- `openai_sdk.py`: OpenAI Agent SDK integration hooks
- `viewer.py`: Log viewing and filtering utilities

## How to Use

### Basic Logging

```python
from utils.logging.logger import get_logger

# Get a logger for a component
logger = get_logger("my_component")

# Log at different levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Log with additional context
logger.info("Processing story", workspace_id="workspace1", story_id="12345")
```

### Trace Context

```python
from utils.logging.logger import get_logger, trace_context

logger = get_logger("my_component")

# Set trace context for a block of code
with trace_context(request_id="req123", workspace_id="workspace1", story_id="12345"):
    # All logs within this block will include the context
    logger.info("Processing webhook")
    
    # Nested operations inherit context
    process_story()
```

### Operation Tracking

```python
from utils.logging.logger import get_logger

logger = get_logger("my_component")

# Track an operation with timing
with logger.operation("process_webhook", workspace_id="workspace1", story_id="12345"):
    # Operation start is logged automatically
    process_webhook()
    # Operation end and duration are logged automatically
```

### Function Decorators

```python
from utils.logging.logger import logged_operation

# Log a function execution as an operation
@logged_operation("my_component", "process_webhook")
def process_webhook(workspace_id, story_id):
    # Function execution is logged as an operation
    pass
```

### Webhook Logging

```python
from utils.logging.webhook import (
    log_webhook_receipt,
    log_webhook_validation,
    log_webhook_processing_start,
    log_webhook_processing_complete
)

# Log webhook receipt
request_id = log_webhook_receipt(
    workspace_id="workspace1",
    path="/api/webhook/workspace1",
    client_ip="127.0.0.1",
    headers={"Content-Type": "application/json"},
    data=webhook_data
)

# Log webhook validation
log_webhook_validation(
    request_id=request_id,
    workspace_id="workspace1",
    story_id="12345",
    is_valid=True
)

# Log processing start
log_webhook_processing_start(
    request_id=request_id,
    workspace_id="workspace1",
    story_id="12345"
)

# Process webhook...

# Log processing complete
log_webhook_processing_complete(
    request_id=request_id,
    workspace_id="workspace1",
    story_id="12345",
    result=result,
    duration_ms=duration_ms
)
```

### Agent Logging

```python
from utils.logging.agent import (
    log_agent_start,
    log_agent_completion,
    log_agent_handoff,
    log_tool_use,
    log_tool_result
)

# Log agent start
log_agent_start(
    agent_type="triage",
    agent_name="Triage Agent",
    request_id="req123",
    workspace_id="workspace1",
    story_id="12345",
    model="gpt-3.5-turbo"
)

# Log agent completion
log_agent_completion(
    agent_type="triage",
    agent_name="Triage Agent",
    request_id="req123",
    workspace_id="workspace1",
    story_id="12345",
    duration_ms=1500,
    result_summary={"processed": True, "workflow": "enhance"}
)

# Log agent handoff
log_agent_handoff(
    from_agent_type="triage",
    from_agent_name="Triage Agent",
    to_agent_type="analysis",
    to_agent_name="Analysis Agent",
    request_id="req123",
    workspace_id="workspace1",
    story_id="12345",
    handoff_reason="Story needs enhancement"
)
```

### OpenAI Agent SDK Integration

```python
from openai.types.agent import Agent, FunctionTool
from utils.logging.openai_sdk import LoggingAgentHooks

# Create agent with logging hooks
agent = Agent(
    name="Analysis Agent",
    instructions="Analyze story quality",
    model="gpt-3.5-turbo",
    tools=[
        FunctionTool(function=analyze_title),
        FunctionTool(function=analyze_description)
    ],
    hooks=LoggingAgentHooks(
        agent_type="analysis",
        agent_name="Analysis Agent"
    )
)
```

## Log Viewing

The logging system includes utilities for viewing and filtering logs:

### Command-Line Log Viewer

```bash
# View all logs
python scripts/follow_logs.py

# View logs for a specific request
python scripts/follow_logs.py --request-id req123

# View logs for a specific workspace and story
python scripts/follow_logs.py --workspace-id workspace1 --story-id 12345

# View logs above a certain level
python scripts/follow_logs.py --level WARNING

# Follow the most recent webhook
python scripts/follow_logs.py --webhook
```

### Real-Time Log Following

The `follow_logs.py` script can be used to follow logs in real-time:

```bash
# Follow logs for all requests
python scripts/follow_logs.py

# Follow logs for the most recent webhook
python scripts/follow_logs.py --webhook
```

When using the `start_webhook_server.sh` script, a log follower is automatically started in debug mode.

## Configuration

The logging system can be configured globally using the `configure_global_logging` function:

```python
from utils.logging.logger import configure_global_logging

# Configure global logging
configure_global_logging(
    log_dir="logs",
    log_filename="application.log",
    console_level="INFO",
    file_level="DEBUG",
    console_format="text",
    file_format="json"
)
```

## Trace Correlation with OpenAI Agent SDK

The logging system automatically integrates with the OpenAI Agent SDK to correlate logs with traces:

1. The trace processor captures all OpenAI Agent SDK traces and spans
2. Trace and span IDs are added to the trace context
3. All logs within the same trace include the trace ID
4. Full trace data is stored in the logs/traces directory

## Best Practices

1. **Use Structured Logging**: Always include relevant context fields in log calls
2. **Use Trace Context**: Wrap operations in trace_context to ensure correlation
3. **Log Operations**: Use the operation context manager for tracking operations
4. **Use Request IDs**: Always include request_id in logs for correlation
5. **Log at Appropriate Levels**: Use the right log level for each message
6. **Include Relevant Context**: Include workspace_id and story_id in all logs
7. **Monitor Traces**: Use the trace viewer to monitor agent execution

## Debugging Tips

1. **Check request_id**: When debugging an issue, filter logs by request_id
2. **View Trace Data**: Examine trace data in logs/traces for agent execution details
3. **Follow Webhooks**: Use the `--webhook` flag with `follow_logs.py` to follow webhook processing
4. **Check Operation Timing**: Look for operation_start and operation_end events to identify performance bottlenecks
5. **Filter by Component**: Use component names to focus on specific parts of the system

## Customization

The logging system is designed to be extensible. You can create custom loggers, add trace processors, and extend the logging utilities to meet your specific needs.

## Deployment Considerations

- In production, logs are formatted as JSON for machine readability
- In development, logs are formatted as text for human readability
- The log viewer automatically detects log file formats
- The log follower works in both development and production environments