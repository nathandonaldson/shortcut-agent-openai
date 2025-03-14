#!/usr/bin/env python3
"""
Start a background worker for processing tasks from the queue.

This script starts a worker process that processes enhancement and analysis tasks.
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the worker module
from utils.queue.worker import TaskWorker, TaskType

# Import environment utility
from utils.env import load_env_vars

# Parse arguments
parser = argparse.ArgumentParser(description="Start a background worker for task processing")
parser.add_argument("--worker-id", help="Worker ID for tracking")
parser.add_argument("--polling-interval", type=float, default=1.0, help="Seconds between queue polls")
parser.add_argument("--task-types", help="Comma-separated list of task types to process")
parser.add_argument("--redis-url", help="Redis URL for task queue")
parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                    default="INFO", help="Logging level")
parser.add_argument("--log-file", help="Log file path (logs to console if not specified)")

args = parser.parse_args()

# Load environment variables
load_env_vars()

# Set Redis URL from argument or environment
if args.redis_url:
    os.environ["REDIS_URL"] = args.redis_url

# Configure logging
log_level = getattr(logging, args.log_level)
log_handlers = []

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log_handlers.append(console_handler)

# Add file handler if specified
if args.log_file:
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(args.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    log_handlers.append(file_handler)

# Configure root logger
logging.basicConfig(
    level=log_level,
    handlers=log_handlers,
    force=True
)

# Get logger for this script
logger = logging.getLogger("worker_script")

# Set Redis URL in environment if provided
if args.redis_url:
    os.environ["REDIS_URL"] = args.redis_url
    logger.info(f"Using Redis URL: {args.redis_url}")

# Parse task types
task_types = None
if args.task_types:
    task_types = [t.strip() for t in args.task_types.split(",")]
    logger.info(f"Processing task types: {task_types}")

async def run_worker():
    """Run the worker with the specified configuration"""
    # Create and start the worker
    worker = TaskWorker(
        worker_id=args.worker_id,
        polling_interval=args.polling_interval,
        task_types=task_types
    )
    
    logger.info(f"Starting worker {worker.worker_id}")
    logger.info(f"Polling interval: {args.polling_interval}s")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping worker")
    except Exception as e:
        logger.exception(f"Worker error: {str(e)}")
    finally:
        logger.info("Shutting down worker")
        await worker.stop()

def main():
    """Main entry point"""
    logger.info("Starting background worker")
    
    # Print configuration
    logger.info(f"Worker ID: {args.worker_id or 'auto-generated'}")
    logger.info(f"Log level: {args.log_level}")
    if args.log_file:
        logger.info(f"Logging to file: {args.log_file}")
    
    # Run the worker
    asyncio.run(run_worker())
    
    logger.info("Worker process terminated")

if __name__ == "__main__":
    main()