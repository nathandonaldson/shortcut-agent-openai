# Background Task Processing Architecture

This directory contains the implementation of the background task processing architecture for the Shortcut Enhancement System. The architecture separates webhook handling (fast, synchronous operations) from story enhancement processing (slow, asynchronous operations) using a Redis-based task queue.

## Components

### Task Queue Manager

The `TaskQueueManager` class in `task_queue.py` provides a Redis-based implementation for task queueing. It supports:

- Task prioritization
- Multiple task types
- Worker tracking
- Task retries
- Error handling
- Queue statistics
- Cleanup of old tasks

### Worker

The `TaskWorker` class in `worker.py` implements a background worker that:

- Polls the queue for new tasks
- Processes tasks with the appropriate agents
- Handles task success/failure
- Manages task dependencies
- Provides statistics
- Supports graceful shutdown

### Integration with Webhook Handler

The webhook handler in `api/webhook/handler.py` has been updated to support:

- Queueing tasks for background processing
- Configurable inline/background processing
- Environment-based configuration
- Consistent logging and tracing

## Task Flow

1. **Webhook Reception**: Webhook received and validated
2. **Task Queueing**: Task created and added to Redis queue
3. **Worker Processing**: Background worker picks up task and processes it
4. **Agent Execution**: Appropriate agent(s) run to process the task
5. **Result Storage**: Results stored and task marked as completed
6. **Webhooks**: Notifications sent upon completion (if configured)

## Usage

### Running a Worker

To start a background worker:

```bash
# Using the shell script
./scripts/start_worker.sh

# With specific options
./scripts/start_worker.sh --worker-id my-worker --polling-interval 2.0 --task-types triage,analysis,enhancement

# Directly using Python
python scripts/start_worker.py --worker-id my-worker --log-level DEBUG
```

### Environment Variables

- `USE_BACKGROUND_PROCESSING`: Set to "true" to use background processing (default: true)
- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379/0)
- `LOG_LEVEL`: Logging level (default: INFO)

### Monitoring

- Worker logs are written to the logs directory
- Redis queue statistics can be viewed using the Redis CLI

## Architecture Decisions

1. **Redis for Task Queuing**: Redis provides atomic operations, persistence, and sorted sets for priority queues
2. **Asynchronous Workers**: Async IO for high throughput and resource efficiency
3. **Task Prioritization**: Tasks are prioritized based on their importance
4. **Graceful Shutdown**: Workers handle signals for clean shutdown
5. **Error Handling**: Failed tasks can be retried with increasing priority
6. **Logging and Tracing**: Comprehensive logging with request correlation
7. **Configurability**: Environment variables and command-line options for flexible deployment

## OpenAI Agent SDK Integration

The worker process integrates with the OpenAI Agent SDK by:

1. Creating proper workspace contexts for each task
2. Setting up agent instances with appropriate configuration
3. Configuring lifecycle hooks for agents
4. Implementing proper handoffs between agents
5. Using OpenAI's trace context for request tracing
6. Adding appropriate metadata for trace filtering
7. Handling edge cases and SDK limitations

## Development and Deployment

### Local Development

```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Set environment variables
export REDIS_URL=redis://localhost:6379/0
export USE_BACKGROUND_PROCESSING=true

# Start a worker
./scripts/start_worker.sh --log-level DEBUG

# Process webhooks
# The webhook handler will now queue tasks instead of processing them inline
```

### Production Deployment

For production deployment, the worker process can be:

1. Deployed as a separate service on Vercel or other platforms
2. Scaled independently of the webhook handler
3. Configured with appropriate timeouts and monitoring
4. Integrated with HA Redis or a managed Redis service

## Error Handling

The architecture handles errors at multiple levels:

1. **Task Queueing**: Failed queue operations are logged and reported
2. **Worker Processing**: Workers handle exceptions and track error rates
3. **Task Retries**: Failed tasks can be retried with configurable backoff
4. **Graceful Degradation**: Critical errors are handled appropriately
5. **Monitoring**: Error rates and patterns are tracked for alerting

## Future Enhancements

Possible future enhancements include:

1. **Distributed Worker Coordination**: Using Redis locks for better coordination
2. **Worker Heartbeats**: Tracking worker health and rebalancing tasks
3. **Task Dependencies**: Implementing dependency resolution between tasks
4. **Task Scheduling**: Adding support for delayed and recurring tasks
5. **UI Dashboard**: Adding a simple dashboard for monitoring
6. **Multi-tenancy**: Better isolation between workspaces
7. **Metrics Collection**: Integration with metrics collection systems