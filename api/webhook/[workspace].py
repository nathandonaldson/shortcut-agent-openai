from http.server import BaseHTTPRequestHandler
import json
import os
from typing import Dict, Any, Optional

# This is a placeholder for proper implementation
# In a real implementation, you would:
# 1. Validate the webhook data
# 2. Enqueue the task for processing
# 3. Return a 200 response immediately

def handler(request):
    # Get the workspace ID from the path parameters
    workspace_id = request.path.split('/')[-1]
    
    # Parse the request body
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON"})
        }
    
    # Validate the webhook (basic validation)
    if not validate_webhook(body, workspace_id):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid webhook data"})
        }
    
    # Enqueue the task for processing
    task_id = enqueue_task(workspace_id, body)
    
    # Return a success response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "accepted",
            "task_id": task_id
        })
    }

def validate_webhook(data: Dict[str, Any], workspace_id: str) -> bool:
    """
    Validate the webhook data.
    Basic validation to check if it's a story update with a label change.
    """
    # Check if this is a story update
    if data.get("action") != "update":
        return False
    
    # Check if there's a label change
    changes = data.get("changes", {})
    if "labels" not in changes:
        return False
    
    return True

def enqueue_task(workspace_id: str, webhook_data: Dict[str, Any]) -> str:
    """
    Enqueue a task for processing.
    This is a placeholder for actual implementation with Redis/KV store.
    """
    # Generate a task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # In a real implementation, you would store the task in Redis/KV store
    # For now, just log it
    print(f"Task {task_id} enqueued for workspace {workspace_id}")
    
    # Extract the story ID for reference
    story_id = webhook_data.get("id")
    
    # Return the task ID
    return task_id