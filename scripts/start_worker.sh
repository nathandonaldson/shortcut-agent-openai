#!/bin/bash
# Start background worker for processing Shortcut Enhancement System tasks

# Default values
WORKER_ID=""
POLLING_INTERVAL=1.0
TASK_TYPES=""
REDIS_URL=""
LOG_LEVEL="INFO"
LOG_FILE="logs/worker_$(date +%Y%m%d_%H%M%S).log"

# Parse command line options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --worker-id)
      WORKER_ID="$2"
      shift 2
      ;;
    --polling-interval)
      POLLING_INTERVAL="$2"
      shift 2
      ;;
    --task-types)
      TASK_TYPES="$2"
      shift 2
      ;;
    --redis-url)
      REDIS_URL="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="$2"
      shift 2
      ;;
    --log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --worker-id ID            Worker ID for tracking (default: auto-generated)"
      echo "  --polling-interval SECS   Seconds between queue polls (default: 1.0)"
      echo "  --task-types TYPES        Comma-separated list of task types to process (default: all)"
      echo "  --redis-url URL           Redis URL (default: from environment)"
      echo "  --log-level LEVEL         Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)"
      echo "  --log-file PATH           Log file path (default: logs/worker_TIMESTAMP.log)"
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information."
      exit 1
      ;;
  esac
done

# Ensure the script is run from the project root
cd "$(dirname "$0")/.." || { echo "Error: Could not navigate to project root"; exit 1; }

# Check for Python virtual environment
if [ -d "agent_venv" ]; then
  echo "Activating virtual environment..."
  # shellcheck disable=SC1091
  source agent_venv/bin/activate
fi

# Ensure required dependencies
echo "Checking dependencies..."
pip install -q redis aioredis

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Build the command
CMD="python3 scripts/start_worker.py"

if [ -n "$WORKER_ID" ]; then
  CMD="$CMD --worker-id \"$WORKER_ID\""
fi

if [ -n "$POLLING_INTERVAL" ]; then
  CMD="$CMD --polling-interval $POLLING_INTERVAL"
fi

if [ -n "$TASK_TYPES" ]; then
  CMD="$CMD --task-types \"$TASK_TYPES\""
fi

if [ -n "$REDIS_URL" ]; then
  CMD="$CMD --redis-url \"$REDIS_URL\""
fi

if [ -n "$LOG_LEVEL" ]; then
  CMD="$CMD --log-level $LOG_LEVEL"
fi

if [ -n "$LOG_FILE" ]; then
  CMD="$CMD --log-file \"$LOG_FILE\""
fi

# Print configuration
echo "======================================================="
echo "Starting Shortcut Enhancement System Background Worker"
echo "======================================================="
echo "Worker ID:        ${WORKER_ID:-auto-generated}"
echo "Polling Interval: $POLLING_INTERVAL seconds"
echo "Task Types:       ${TASK_TYPES:-all types}"
echo "Log Level:        $LOG_LEVEL"
echo "Log File:         $LOG_FILE"
echo "-------------------------------------------------------"

# Execute the worker
echo "Starting worker..."
echo "Command: $CMD"
eval "$CMD"

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "Worker exited with error code: $EXIT_CODE"
  exit $EXIT_CODE
fi