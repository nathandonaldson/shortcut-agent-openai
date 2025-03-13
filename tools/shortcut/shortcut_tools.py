"""
Function tools for interacting with the Shortcut API.
In development mode, these functions use mock data.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shortcut_tools")

# Mock data for local development
MOCK_STORY = {
    "id": 12345,
    "name": "Improve error handling in authentication flow",
    "description": "We need to improve error handling in the authentication flow. Currently, when a user encounters an error during login, they just see a generic error message. We should provide more specific feedback.",
    "labels": [
        {"id": 1000, "name": "enhancement"},
        {"id": 1001, "name": "auth"},
        {"id": 1002, "name": "enhance"}  # Special label for our system
    ],
    "workflow_state_id": 500001,
    "created_at": "2023-01-15T10:00:00Z",
    "updated_at": "2023-01-20T15:30:00Z",
    "requested_by_id": "user-123"
}

def is_development_mode() -> bool:
    """Check if the system is running in development mode"""
    return os.environ.get("VERCEL_ENV", "development") == "development"

def get_shortcut_client(api_key: str):
    """
    Get a Shortcut API client.
    This is a placeholder - in a real implementation, you would initialize 
    a proper API client. For now, we'll just return a dictionary of mocked functions.
    """
    if is_development_mode():
        logger.info("Using mock Shortcut client for development")
        
        # Return mock client functions
        return {
            "get_story": mock_get_story,
            "update_story": mock_update_story,
            "create_comment": mock_create_comment
        }
    else:
        # In production, you would create a real client
        # This is a placeholder - you would use a proper Shortcut API library
        logger.info("Using real Shortcut client")
        
        raise NotImplementedError("Real Shortcut client not implemented yet")

# Mock functions for local development

def mock_get_story(story_id: str) -> Dict[str, Any]:
    """Mock function to get a story by ID"""
    logger.info(f"[MOCK] Getting story: {story_id}")
    time.sleep(0.5)  # Simulate API delay
    
    # Return a copy of the mock story with the requested ID
    story = MOCK_STORY.copy()
    story["id"] = int(story_id)
    return story

def mock_update_story(story_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Mock function to update a story"""
    logger.info(f"[MOCK] Updating story: {story_id}")
    logger.info(f"[MOCK] Update data: {json.dumps(data, indent=2)}")
    time.sleep(0.5)  # Simulate API delay
    
    # Return a copy of the mock story with updates applied
    story = MOCK_STORY.copy()
    story["id"] = int(story_id)
    story.update(data)
    
    # Updated timestamp
    story["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    return story

def mock_create_comment(story_id: str, text: str) -> Dict[str, Any]:
    """Mock function to create a comment on a story"""
    logger.info(f"[MOCK] Creating comment on story: {story_id}")
    logger.info(f"[MOCK] Comment text: {text}")
    time.sleep(0.5)  # Simulate API delay
    
    return {
        "id": 98765,
        "text": text,
        "story_id": int(story_id),
        "author_id": "user-system",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

# Function tools for the OpenAI Agent SDK

async def get_story_details(story_id: str, api_key: str) -> Dict[str, Any]:
    """
    Get details of a Shortcut story by ID.
    
    Args:
        story_id: The ID of the story to retrieve
        api_key: The Shortcut API key
        
    Returns:
        Dictionary with story details
    """
    client = get_shortcut_client(api_key)
    return client["get_story"](story_id)

async def update_story(story_id: str, api_key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a Shortcut story.
    
    Args:
        story_id: The ID of the story to update
        api_key: The Shortcut API key
        updates: Dictionary of fields to update
        
    Returns:
        Updated story data
    """
    client = get_shortcut_client(api_key)
    return client["update_story"](story_id, updates)

async def add_comment(story_id: str, api_key: str, text: str) -> Dict[str, Any]:
    """
    Add a comment to a Shortcut story.
    
    Args:
        story_id: The ID of the story to comment on
        api_key: The Shortcut API key
        text: The comment text
        
    Returns:
        Created comment data
    """
    client = get_shortcut_client(api_key)
    return client["create_comment"](story_id, text)

async def queue_enhancement_task(workspace_id: str, story_id: str, api_key: str) -> Dict[str, Any]:
    """
    Queue a story for enhancement.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID to enhance
        api_key: The Shortcut API key
        
    Returns:
        Task information
    """
    # Import here to avoid circular imports
    from utils.storage.local_storage import local_storage
    
    logger.info(f"Queueing enhancement task for story {story_id} in workspace {workspace_id}")
    
    # Get the story details
    story_data = await get_story_details(story_id, api_key)
    
    # Create task data
    task_data = {
        "workspace_id": workspace_id,
        "story_id": story_id,
        "story_data": story_data,
        "task_type": "enhancement",
        "status": "queued",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Save the task
    task_key = local_storage.save_task(workspace_id, story_id, task_data)
    
    # In a production system, you would actually queue this in a background job system
    logger.info(f"Task queued with key: {task_key}")
    
    return {
        "task_key": task_key,
        "task_status": "queued"
    }

async def queue_analysis_task(workspace_id: str, story_id: str, api_key: str) -> Dict[str, Any]:
    """
    Queue a story for analysis only.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID to analyze
        api_key: The Shortcut API key
        
    Returns:
        Task information
    """
    # Import here to avoid circular imports
    from utils.storage.local_storage import local_storage
    
    logger.info(f"Queueing analysis task for story {story_id} in workspace {workspace_id}")
    
    # Get the story details
    story_data = await get_story_details(story_id, api_key)
    
    # Create task data
    task_data = {
        "workspace_id": workspace_id,
        "story_id": story_id,
        "story_data": story_data,
        "task_type": "analysis",
        "status": "queued",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Save the task
    task_key = local_storage.save_task(workspace_id, story_id, task_data)
    
    # In a production system, you would actually queue this in a background job system
    logger.info(f"Task queued with key: {task_key}")
    
    return {
        "task_key": task_key,
        "task_status": "queued"
    }