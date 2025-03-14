"""
Task Queue Manager for the Shortcut Enhancement System.

This module provides a Redis-based task queue implementation for background 
processing of enhancement and analysis tasks.
"""

import os
import json
import time
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple

import redis.asyncio as aioredis
from pydantic import BaseModel, Field, ConfigDict

# Set up logging
logger = logging.getLogger("task_queue")

class TaskStatus:
    """Task status constants"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class TaskPriority:
    """Task priority constants"""
    HIGH = 10
    NORMAL = 20
    LOW = 30

class TaskType:
    """Task type constants"""
    TRIAGE = "triage"
    ANALYSIS = "analysis"
    ENHANCEMENT = "enhancement"
    UPDATE = "update"

class Task(BaseModel):
    """Task model for queue operations"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    story_id: str
    task_type: str
    priority: int = Field(default=TaskPriority.NORMAL)
    status: str = Field(default=TaskStatus.PENDING)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary for storage"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from a dictionary"""
        return cls(**data)

class TaskQueueManager:
    """
    Redis-based task queue manager for the Shortcut Enhancement System.
    
    This class handles the queuing, retrieval, and management of background tasks.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the task queue manager.
        
        Args:
            redis_url: Redis connection URL, defaults to environment variable REDIS_URL
        """
        # Get Redis URL from environment if not provided
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        
        # Set Redis connection to None initially
        self._redis: Optional[aioredis.Redis] = None
        
        # Key prefixes for Redis
        self.task_prefix = "task:"
        self.queue_prefix = "task_queue:"
        self.processing_prefix = "processing:"
        self.failed_prefix = "failed:"
        self.complete_prefix = "complete:"
        
        # Redis connection lock
        self._redis_lock = asyncio.Lock()
        
        logger.info(f"Initialized TaskQueueManager with Redis URL: {self.redis_url}")
    
    async def get_redis(self) -> aioredis.Redis:
        """
        Get the Redis connection, creating it if necessary.
        
        Returns:
            Redis connection
        """
        async with self._redis_lock:
            if self._redis is None:
                logger.info("Creating new Redis connection")
                self._redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                # Verify connection
                await self._redis.ping()
                logger.info("Redis connection established")
            else:
                # Verify existing connection is still alive
                try:
                    await self._redis.ping()
                except Exception as e:
                    logger.warning(f"Redis connection error: {str(e)}, reconnecting...")
                    self._redis = aioredis.from_url(
                        self.redis_url,
                        decode_responses=True
                    )
                    await self._redis.ping()
                    logger.info("Redis connection re-established")
            
            return self._redis
    
    async def close(self):
        """Close the Redis connection"""
        if self._redis:
            logger.info("Closing Redis connection")
            await self._redis.close()
            self._redis = None
    
    def _get_task_key(self, task_id: str) -> str:
        """Get the Redis key for a task"""
        return f"{self.task_prefix}{task_id}"
    
    def _get_queue_key(self, task_type: str) -> str:
        """Get the Redis key for a queue by task type"""
        # The worker iterates through task types and checks task_queue:pending
        # So we need to just use a single consistent key
        return f"{self.queue_prefix}{TaskStatus.PENDING}"
    
    def _get_processing_key(self, worker_id: str) -> str:
        """Get the Redis key for processing tasks by worker"""
        return f"{self.processing_prefix}{worker_id}"
    
    async def add_task(self, task: Task) -> str:
        """
        Add a task to the queue.
        
        Args:
            task: The task to add
            
        Returns:
            The task ID
        """
        redis = await self.get_redis()
        
        # Update timestamps
        task.created_at = datetime.utcnow().isoformat()
        task.updated_at = task.created_at
        
        # Convert task to JSON
        task_data = json.dumps(task.to_dict())
        
        # Get the appropriate queue key
        queue_key = self._get_queue_key(task.task_type)
        task_key = self._get_task_key(task.task_id)
        
        # Debug logs
        logger.info(f"Task key: {task_key}")
        logger.info(f"Queue key: {queue_key}")
        
        # Store the task data
        await redis.set(task_key, task_data)
        
        # Before adding, check if the queue already has anything in it
        existing_count = await redis.zcard(queue_key)
        logger.info(f"Queue {queue_key} has {existing_count} tasks before adding new task")
        
        # Add to the appropriate queue with priority as score (lower = higher priority)
        try:
            # Use ZADD NX to prevent duplication
            result = await redis.zadd(queue_key, {task.task_id: task.priority}, nx=True)
            logger.info(f"Successfully added task {task.task_id} to queue {queue_key}, result: {result}")
        
            # Verify task was added
            new_count = await redis.zcard(queue_key)
            if new_count > existing_count:
                logger.info(f"Task added successfully. Queue now has {new_count} tasks.")
            else:
                logger.warning(f"Task might not have been added! Queue size unchanged: {new_count}")
        except Exception as e:
            logger.error(f"Error adding task to queue: {str(e)}")
        
        logger.info(f"Added task {task.task_id} to queue {task.task_type} with priority {task.priority}")
        
        return task.task_id
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task or None if not found
        """
        redis = await self.get_redis()
        
        task_key = self._get_task_key(task_id)
        task_data = await redis.get(task_key)
        
        if not task_data:
            logger.warning(f"Task {task_id} not found")
            return None
        
        try:
            task_dict = json.loads(task_data)
            task = Task.from_dict(task_dict)
            return task
        except Exception as e:
            logger.error(f"Error deserializing task {task_id}: {e}")
            return None
    
    async def update_task(self, task: Task) -> bool:
        """
        Update a task in storage.
        
        Args:
            task: The task to update
            
        Returns:
            True if successful, False otherwise
        """
        redis = await self.get_redis()
        
        # Update timestamp
        task.updated_at = datetime.utcnow().isoformat()
        
        # Convert task to JSON
        task_data = json.dumps(task.to_dict())
        
        task_key = self._get_task_key(task.task_id)
        
        # Store the task data
        await redis.set(task_key, task_data)
        
        logger.info(f"Updated task {task.task_id} with status {task.status}")
        
        return True
    
    async def get_next_task(self, task_types: List[str] = None, worker_id: str = "default") -> Optional[Task]:
        """
        Get the next task from the queue based on priority.
        
        Args:
            task_types: List of task types to check, defaults to all types
            worker_id: Worker ID for tracking
            
        Returns:
            The next task or None if no tasks are available
        """
        redis = await self.get_redis()
        
        # Default to all task types if none specified
        if not task_types:
            task_types = [TaskType.TRIAGE, TaskType.ANALYSIS, TaskType.ENHANCEMENT, TaskType.UPDATE]
        
        # Check each queue in order of task type
        for task_type in task_types:
            queue_key = self._get_queue_key(task_type)
            
            # Get the task with the highest priority (lowest score)
            result = await redis.zpopmin(queue_key, 1)
            
            if not result:
                continue
            
            task_id, priority = result[0]
            
            # Get the task data
            task = await self.get_task(task_id)
            
            if not task:
                logger.warning(f"Task {task_id} was in queue but data not found")
                continue
            
            # Mark the task as processing
            task.status = TaskStatus.PROCESSING
            await self.update_task(task)
            
            # Add to processing set for this worker
            processing_key = self._get_processing_key(worker_id)
            await redis.sadd(processing_key, task_id)
            
            logger.info(f"Worker {worker_id} retrieved task {task_id} of type {task_type}")
            
            return task
        
        # No tasks found in any queue
        return None
    
    async def complete_task(self, task: Task, result: Dict[str, Any], worker_id: str = "default") -> bool:
        """
        Mark a task as completed with results.
        
        Args:
            task: The task to complete
            result: The task result data
            worker_id: Worker ID for tracking
            
        Returns:
            True if successful, False otherwise
        """
        redis = await self.get_redis()
        
        # Update task status and result
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.utcnow().isoformat()
        
        # Update the task
        await self.update_task(task)
        
        # Remove from processing set
        processing_key = self._get_processing_key(worker_id)
        await redis.srem(processing_key, task.task_id)
        
        # Add to completed set with timestamp
        await redis.zadd(self.complete_prefix, {task.task_id: time.time()})
        
        logger.info(f"Task {task.task_id} completed by worker {worker_id}")
        
        return True
    
    async def fail_task(self, task: Task, error: str, retry: bool = True, worker_id: str = "default") -> bool:
        """
        Mark a task as failed with error information.
        
        Args:
            task: The task that failed
            error: Error message
            retry: Whether to retry the task (if max retries not reached)
            worker_id: Worker ID for tracking
            
        Returns:
            True if successful, False otherwise
        """
        redis = await self.get_redis()
        
        # Check if we should retry
        should_retry = retry and task.retry_count < task.max_retries
        
        if should_retry:
            # Increment retry count
            task.retry_count += 1
            task.status = TaskStatus.RETRY
            task.error = error
            
            # Re-queue with higher priority (add 1 to priority)
            queue_key = self._get_queue_key(task.task_type)
            await redis.zadd(queue_key, {task.task_id: task.priority - 1})
            
            logger.info(f"Task {task.task_id} failed, retrying (attempt {task.retry_count}/{task.max_retries})")
        else:
            # Mark as failed
            task.status = TaskStatus.FAILED
            task.error = error
            
            # Add to failed set with timestamp
            await redis.zadd(self.failed_prefix, {task.task_id: time.time()})
            
            logger.warning(f"Task {task.task_id} failed permanently: {error}")
        
        # Update task
        task.updated_at = datetime.utcnow().isoformat()
        await self.update_task(task)
        
        # Remove from processing set
        processing_key = self._get_processing_key(worker_id)
        await redis.srem(processing_key, task.task_id)
        
        return True
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the task queues.
        
        Returns:
            Dictionary with queue statistics
        """
        redis = await self.get_redis()
        
        stats = {
            "queued": {},
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        # Count queued tasks by type
        for task_type in [TaskType.TRIAGE, TaskType.ANALYSIS, TaskType.ENHANCEMENT, TaskType.UPDATE]:
            queue_key = self._get_queue_key(task_type)
            count = await redis.zcard(queue_key)
            stats["queued"][task_type] = count
        
        # Count processing tasks
        processing_keys = await redis.keys(f"{self.processing_prefix}*")
        for key in processing_keys:
            count = await redis.scard(key)
            stats["processing"] += count
        
        # Count completed and failed tasks
        stats["completed"] = await redis.zcard(self.complete_prefix)
        stats["failed"] = await redis.zcard(self.failed_prefix)
        
        return stats
    
    async def clean_old_tasks(self, days: int = 7) -> int:
        """
        Clean up old completed and failed tasks.
        
        Args:
            days: Number of days to keep tasks
            
        Returns:
            Number of tasks removed
        """
        redis = await self.get_redis()
        
        # Calculate cutoff timestamp
        cutoff = time.time() - (days * 24 * 60 * 60)
        
        # Remove old completed tasks
        completed_removed = await redis.zremrangebyscore(self.complete_prefix, 0, cutoff)
        
        # Remove old failed tasks
        failed_removed = await redis.zremrangebyscore(self.failed_prefix, 0, cutoff)
        
        total_removed = completed_removed + failed_removed
        logger.info(f"Cleaned up {total_removed} old tasks (completed: {completed_removed}, failed: {failed_removed})")
        
        return total_removed

# Singleton instance for use throughout the application
task_queue = TaskQueueManager()