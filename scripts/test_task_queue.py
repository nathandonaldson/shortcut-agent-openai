#!/usr/bin/env python3
"""
Test script for the task queue system.

This script tests the Redis-based task queue by:
1. Adding a test task to the queue
2. Verifying it can be retrieved
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_task_queue")

# Import task queue components
from utils.queue.task_queue import task_queue, Task, TaskType, TaskPriority

async def test_task_queue():
    """Test task queue functionality"""
    logger.info("Testing task queue functionality")
    
    # Create a test task
    test_task = Task(
        workspace_id="test-workspace",
        story_id="test-story-123",
        task_type=TaskType.TRIAGE,
        priority=TaskPriority.HIGH,
        payload={
            "webhook_data": {"test": True},
            "request_id": "test-request-123"
        }
    )
    
    # Add the task to the queue
    logger.info("Adding test task to queue")
    task_id = await task_queue.add_task(test_task)
    logger.info(f"Task added with ID: {task_id}")
    
    # Get queue stats
    stats = await task_queue.get_queue_stats()
    logger.info(f"Queue stats: {stats}")
    
    # Try to retrieve the task
    logger.info("Retrieving task from queue")
    worker_id = "test-worker"
    retrieved_task = await task_queue.get_next_task([TaskType.TRIAGE], worker_id)
    
    if retrieved_task:
        logger.info(f"Retrieved task: {retrieved_task.task_id}")
        logger.info(f"Task data: {retrieved_task.payload}")
        
        # Mark the task as completed
        logger.info("Marking task as completed")
        await task_queue.complete_task(
            retrieved_task, 
            {"result": "Test completed successfully"}, 
            worker_id
        )
        
        # Get queue stats again
        stats = await task_queue.get_queue_stats()
        logger.info(f"Queue stats after completion: {stats}")
        
        return True
    else:
        logger.error("Failed to retrieve task from queue")
        return False

async def test_webhook_queue(workspace_id, story_id):
    """Test queueing a realistic webhook task"""
    logger.info(f"Testing webhook task queueing for story {story_id}")
    
    # Create a test webhook data
    webhook_data = {
        "actions": [
            {
                "id": story_id,
                "entity_type": "story",
                "action": "update",
                "changes": {
                    "labels": {
                        "adds": [{"name": "enhance"}]
                    }
                }
            }
        ]
    }
    
    # Create a task
    test_task = Task(
        workspace_id=workspace_id,
        story_id=story_id,
        task_type=TaskType.TRIAGE,
        priority=TaskPriority.HIGH,
        payload={
            "webhook_data": webhook_data,
            "request_id": f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        }
    )
    
    # Add the task to the queue
    logger.info("Adding webhook task to queue")
    task_id = await task_queue.add_task(test_task)
    logger.info(f"Webhook task added with ID: {task_id}")
    
    # Get queue stats
    stats = await task_queue.get_queue_stats()
    logger.info(f"Queue stats: {stats}")
    
    return task_id

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test task queue functionality')
    parser.add_argument('--workspace', default='workspace1', help='Workspace ID to use for test')
    parser.add_argument('--story', default='123', help='Story ID to use for test')
    args = parser.parse_args()
    
    # Run both tests
    loop = asyncio.get_event_loop()
    
    logger.info("----- Testing basic task queue functionality -----")
    basic_result = loop.run_until_complete(test_task_queue())
    
    logger.info("\n----- Testing webhook task queueing -----")
    webhook_task_id = loop.run_until_complete(test_webhook_queue(args.workspace, args.story))
    
    logger.info("\n----- Test Summary -----")
    logger.info(f"Basic queue test: {'PASSED' if basic_result else 'FAILED'}")
    logger.info(f"Webhook task queued with ID: {webhook_task_id}")
    logger.info("A worker should now be able to process this task")
    logger.info("Check worker logs to see if it processes the task")

if __name__ == "__main__":
    import argparse
    main()