"""
Local storage implementation for development purposes.
Uses an in-memory dictionary to store tasks.
"""

import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local_storage")

class LocalStorage:
    """Simple in-memory storage for local development"""
    
    def __init__(self):
        """Initialize an empty storage dictionary"""
        self.storage: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized local storage")
    
    def get_task_key(self, workspace_id: str, story_id: str) -> str:
        """Generate a unique key for a task based on workspace and story IDs"""
        return f"{workspace_id}:{story_id}"
    
    def save_task(self, workspace_id: str, story_id: str, task_data: Dict[str, Any]) -> str:
        """Save a task to storage and return the task key"""
        task_key = self.get_task_key(workspace_id, story_id)
        self.storage[task_key] = task_data
        
        # Log the saved task for debugging
        logger.info(f"Saved task: {task_key}")
        logger.debug(f"Task data: {json.dumps(task_data, indent=2)}")
        
        return task_key
    
    def get_task(self, workspace_id: str, story_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task from storage"""
        task_key = self.get_task_key(workspace_id, story_id)
        
        task = self.storage.get(task_key)
        
        if task:
            logger.info(f"Retrieved task: {task_key}")
        else:
            logger.info(f"Task not found: {task_key}")
            
        return task
    
    def update_task(self, workspace_id: str, story_id: str, 
                   task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing task in storage"""
        task_key = self.get_task_key(workspace_id, story_id)
        
        if task_key in self.storage:
            # Update the existing task
            self.storage[task_key].update(task_data)
            logger.info(f"Updated task: {task_key}")
            logger.debug(f"Updated task data: {json.dumps(self.storage[task_key], indent=2)}")
            return self.storage[task_key]
        else:
            logger.warning(f"Tried to update non-existent task: {task_key}")
            return None
    
    def delete_task(self, workspace_id: str, story_id: str) -> bool:
        """Delete a task from storage"""
        task_key = self.get_task_key(workspace_id, story_id)
        
        if task_key in self.storage:
            del self.storage[task_key]
            logger.info(f"Deleted task: {task_key}")
            return True
        else:
            logger.warning(f"Tried to delete non-existent task: {task_key}")
            return False
    
    def list_tasks(self, workspace_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """List all tasks, optionally filtered by workspace"""
        if workspace_id:
            # Filter tasks by workspace ID
            tasks = {k: v for k, v in self.storage.items() if k.startswith(f"{workspace_id}:")}
            logger.info(f"Listed {len(tasks)} tasks for workspace: {workspace_id}")
        else:
            # Return all tasks
            tasks = self.storage
            logger.info(f"Listed all tasks ({len(tasks)})")
            
        return tasks

# Create a singleton instance for use throughout the application
local_storage = LocalStorage()