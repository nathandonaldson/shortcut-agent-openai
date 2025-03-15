"""
Function tools for interacting with the Shortcut API.
In development mode, these functions use mock data.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable
import time
import asyncio
import aiohttp

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
    return os.environ.get("VERCEL_ENV", "development") == "development" and not os.environ.get("USE_REAL_SHORTCUT", "").lower() in ("true", "1", "yes")

class RealShortcutClient:
    """Real implementation of Shortcut client using API requests"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "Shortcut-Token": api_key}
        self.base_url = "https://api.app.shortcut.com/api/v3"
        
    async def get_story(self, story_id: str) -> Dict[str, Any]:
        """Get a story by ID"""
        logger.info(f"Getting story from Shortcut API: {story_id}")
        
        url = f"{self.base_url}/stories/{story_id}"
        
        # Debug logging - mask most of the API key but show a few chars to validate
        api_key_snippet = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "***masked***"
        logger.info(f"Using API key starting with {api_key_snippet} for story {story_id}")
        logger.info(f"Request URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting story {story_id}: {response.status} {error_text}")
                    logger.error(f"Headers used: Content-Type=application/json, API key length: {len(self.api_key)} chars")
                    # Test with a direct synchronous request to compare
                    try:
                        import requests
                        test_response = requests.get(url, headers={"Shortcut-Token": self.api_key})
                        logger.info(f"Direct test request status: {test_response.status_code}")
                    except Exception as test_err:
                        logger.error(f"Direct test also failed: {str(test_err)}")
                    
                    raise Exception(f"Failed to get story: {response.status}")
    
    async def update_story(self, story_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a story"""
        logger.info(f"Updating story in Shortcut API: {story_id}")
        logger.debug(f"Update data: {json.dumps(data, indent=2)}")
        
        url = f"{self.base_url}/stories/{story_id}"
        
        # Log the exact data being sent
        logger.info(f"Sending update to Shortcut API: {json.dumps(data)}")
        
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully updated story {story_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Error updating story {story_id}: {response.status} {error_text}")
                    raise Exception(f"Failed to update story: {response.status} - {error_text}")
    
    async def create_comment(self, story_id: str, text: str) -> Dict[str, Any]:
        """Create a comment on a story"""
        logger.info(f"Creating comment on story in Shortcut API: {story_id}")
        
        url = f"{self.base_url}/stories/{story_id}/comments"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"text": text}) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Error creating comment on story {story_id}: {response.status} {error_text}")
                    raise Exception(f"Failed to create comment: {response.status}")

class MockShortcutClient:
    """Mock implementation of Shortcut client for local development"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def get_story(self, story_id: str) -> Dict[str, Any]:
        """Mock implementation of get_story"""
        logger.info(f"[MOCK] Getting story: {story_id}")
        time.sleep(0.5)  # Simulate API delay
        
        # Return a copy of the mock story with the requested ID
        story = MOCK_STORY.copy()
        
        # Handle both string and integer IDs
        try:
            story_id_int = int(story_id)
            story["id"] = story_id_int
        except (ValueError, TypeError):
            # If we can't convert to int, just use the string ID
            story["id"] = story_id
        
        return story
    
    async def update_story(self, story_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock implementation of update_story"""
        logger.info(f"[MOCK] Updating story: {story_id}")
        logger.info(f"[MOCK] Update data: {json.dumps(data, indent=2)}")
        time.sleep(0.5)  # Simulate API delay
        
        # Return a copy of the mock story with updates applied
        story = MOCK_STORY.copy()
        
        # Handle both string and integer IDs
        try:
            story_id_int = int(story_id)
            story["id"] = story_id_int
        except (ValueError, TypeError):
            # If we can't convert to int, just use the string ID
            story["id"] = story_id
        
        story.update(data)
        
        # Updated timestamp
        story["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        return story
    
    async def create_comment(self, story_id: str, text: str) -> Dict[str, Any]:
        """Mock implementation of create_comment"""
        logger.info(f"[MOCK] Creating comment on story: {story_id}")
        logger.info(f"[MOCK] Comment text: {text}")
        time.sleep(0.5)  # Simulate API delay
        
        # Handle both string and integer IDs
        try:
            story_id_int = int(story_id)
        except (ValueError, TypeError):
            # If we can't convert to int, just use the string ID
            story_id_int = story_id
        
        return {
            "id": 98765,
            "text": text,
            "story_id": story_id_int,
            "author_id": "user-system",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

def get_shortcut_client(api_key: str):
    """
    Get a Shortcut API client.
    
    Args:
        api_key: The Shortcut API key
        
    Returns:
        A Shortcut client instance
    """
    if is_development_mode():
        logger.info("Using mock Shortcut client for development")
        return MockShortcutClient(api_key)
    else:
        logger.info("Using real Shortcut client")
        return RealShortcutClient(api_key)

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
    return await client.get_story(story_id)

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
    return await client.update_story(story_id, updates)

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
    return await client.create_comment(story_id, text)

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
    # Import task queue
    from utils.queue.task_queue import task_queue, Task, TaskType, TaskPriority
    
    logger.info(f"Queueing enhancement task for story {story_id} in workspace {workspace_id}")
    
    # Get the story details
    story_data = await get_story_details(story_id, api_key)
    
    # Create task for the queue
    task = Task(
        workspace_id=workspace_id,
        story_id=story_id,
        task_type=TaskType.ENHANCEMENT,
        priority=TaskPriority.NORMAL,
        payload={
            "story_data": story_data,
            "workflow_type": "enhance"
        }
    )
    
    # Add the task to the queue
    task_id = await task_queue.add_task(task)
    
    logger.info(f"Enhancement task queued with ID: {task_id}")
    
    return {
        "task_id": task_id,
        "task_status": "queued",
        "task_type": "enhancement"
    }

async def queue_analysis_task(workspace_id: str, story_id: str, api_key: str) -> Dict[str, Any]:
    """
    Queue a story for analysis.
    
    Args:
        workspace_id: Shortcut workspace ID
        story_id: Story ID to analyze
        api_key: Shortcut API key
        
    Returns:
        Task details
    """
    from utils.queue.task_queue import task_queue, Task, TaskType, TaskPriority
    from context.workspace.workspace_context import WorkspaceContext
    
    # Get story details
    story_data = await get_story_details(story_id, api_key)
    
    # Create a task for analysis
    task = Task(
        workspace_id=workspace_id,
        story_id=story_id,
        task_type=TaskType.ANALYSIS,
        priority=TaskPriority.NORMAL,
        payload={
            "story_data": story_data,
            "workflow_type": "analyse"
        }
    )
    
    # Add to queue
    await task_queue.add_task(task)
    
    return {
        "task_id": task.task_id,
        "status": "queued",
        "task_type": task.task_type,
        "story_id": story_id
    }

async def create_story(api_key: str, story_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new story in Shortcut.
    
    Args:
        api_key: Shortcut API key
        story_data: Story data to create
        
    Returns:
        Created story details
    """
    client = get_shortcut_client(api_key)
    
    if isinstance(client, MockShortcutClient):
        # In development mode, return mock data
        mock_story = MOCK_STORY.copy()
        mock_story.update({
            "id": int(time.time()),
            "name": story_data.get("name", "Mock Story"),
            "description": story_data.get("description", "Mock description"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })
        return mock_story
    
    # In production, create a real story
    async with aiohttp.ClientSession() as session:
        url = f"{client.base_url}/stories"
        async with session.post(url, headers=client.headers, json=story_data) as response:
            if response.status != 201:
                error_text = await response.text()
                logger.error(f"Error creating story: {error_text}")
                raise ValueError(f"Failed to create story: {response.status} - {error_text}")
            
            return await response.json()

async def get_workspace_labels(api_key: str) -> List[Dict[str, Any]]:
    """
    Get all labels in a workspace.
    
    Args:
        api_key: Shortcut API key
        
    Returns:
        List of labels
    """
    client = get_shortcut_client(api_key)
    
    if isinstance(client, MockShortcutClient):
        # In development mode, return mock data
        return [
            {"id": 1000, "name": "enhancement"},
            {"id": 1001, "name": "auth"},
            {"id": 1002, "name": "enhance"},
            {"id": 1003, "name": "analyse"},
            {"id": 1004, "name": "bug"}
        ]
    
    # In production, get real labels
    async with aiohttp.ClientSession() as session:
        url = f"{client.base_url}/labels"
        async with session.get(url, headers=client.headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error getting labels: {error_text}")
                raise ValueError(f"Failed to get labels: {response.status} - {error_text}")
            
            return await response.json()

async def get_workflows(api_key: str) -> List[Dict[str, Any]]:
    """
    Get all workflows in a workspace.
    
    Args:
        api_key: Shortcut API key
        
    Returns:
        List of workflows
    """
    client = get_shortcut_client(api_key)
    
    if isinstance(client, MockShortcutClient):
        # In development mode, return mock data
        return [
            {
                "id": 500001,
                "name": "Default",
                "states": [
                    {"id": 500101, "name": "Unstarted"},
                    {"id": 500102, "name": "Started"},
                    {"id": 500103, "name": "Done"}
                ]
            }
        ]
    
    # In production, get real workflows
    async with aiohttp.ClientSession() as session:
        url = f"{client.base_url}/workflows"
        async with session.get(url, headers=client.headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error getting workflows: {error_text}")
                raise ValueError(f"Failed to get workflows: {response.status} - {error_text}")
            
            return await response.json()

async def get_projects(api_key: str) -> List[Dict[str, Any]]:
    """
    Get all projects in a workspace.
    
    Args:
        api_key: Shortcut API key
        
    Returns:
        List of projects
    """
    client = get_shortcut_client(api_key)
    
    if isinstance(client, MockShortcutClient):
        # In development mode, return mock data
        return [
            {
                "id": 12345,
                "name": "Backend",
                "description": "Backend services"
            },
            {
                "id": 12346,
                "name": "Frontend",
                "description": "Frontend applications"
            }
        ]
    
    # In production, get real projects
    async with aiohttp.ClientSession() as session:
        url = f"{client.base_url}/projects"
        async with session.get(url, headers=client.headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error getting projects: {error_text}")
                raise ValueError(f"Failed to get projects: {response.status} - {error_text}")
            
            return await response.json()