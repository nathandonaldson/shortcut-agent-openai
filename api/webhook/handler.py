"""
Webhook handler for Shortcut events.
Processes incoming webhooks and routes them appropriately.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext
from agents.triage.triage_agent import process_webhook

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_handler")

def get_api_key(workspace_id: str) -> str:
    """
    Get the API key for a specific workspace.
    
    Args:
        workspace_id: The ID of the workspace
        
    Returns:
        The API key for the workspace
    """
    # Look for workspace-specific API key in environment variables
    env_var_name = f"SHORTCUT_API_KEY_{workspace_id.upper()}"
    api_key = os.environ.get(env_var_name)
    
    if not api_key:
        # Fall back to generic API key
        api_key = os.environ.get("SHORTCUT_API_KEY")
        
    if not api_key:
        logger.error(f"No API key found for workspace: {workspace_id}")
        raise ValueError(f"No API key found for workspace: {workspace_id}")
        
    return api_key

def validate_webhook(data: Dict[str, Any], workspace_id: str) -> bool:
    """
    Validate a webhook payload.
    
    Args:
        data: The webhook data
        workspace_id: The workspace ID from the URL
        
    Returns:
        True if the webhook is valid, False otherwise
    """
    # Basic validation - check required fields
    if not isinstance(data, dict):
        logger.warning("Invalid webhook data: not a dictionary")
        return False
        
    # Check if it's a story update
    if data.get("action") != "update":
        logger.info("Ignoring non-update webhook event")
        return False
        
    # Check if there's a label change
    changes = data.get("changes", {})
    if "labels" not in changes:
        logger.info("Ignoring update without label changes")
        return False
        
    return True

def extract_story_id(webhook_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract the story ID from webhook data.
    
    Args:
        webhook_data: The webhook data
        
    Returns:
        The story ID or None if not found
    """
    # Extract story ID - exact field name depends on webhook structure
    # This is a simplified example - you may need to adjust based on actual payload
    if "id" in webhook_data:
        return str(webhook_data["id"])
    elif "story_id" in webhook_data:
        return str(webhook_data["story_id"])
    elif "resource" in webhook_data and "id" in webhook_data["resource"]:
        return str(webhook_data["resource"]["id"])
    else:
        logger.warning("Could not extract story ID from webhook data")
        return None

async def handle_webhook(workspace_id: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main webhook handler function.
    
    Args:
        workspace_id: The workspace ID from the URL
        webhook_data: The webhook payload
        
    Returns:
        Response data
    """
    start_time = time.time()
    logger.info(f"Received webhook for workspace: {workspace_id}")
    
    # Basic validation
    if not validate_webhook(webhook_data, workspace_id):
        return {
            "status": "skipped",
            "reason": "Invalid or irrelevant webhook data",
            "workspace_id": workspace_id
        }
    
    # Extract story ID
    story_id = extract_story_id(webhook_data)
    if not story_id:
        return {
            "status": "error",
            "reason": "Could not extract story ID",
            "workspace_id": workspace_id
        }
    
    try:
        # Get API key for the workspace
        api_key = get_api_key(workspace_id)
        
        # Create workspace context
        context = WorkspaceContext(
            workspace_id=workspace_id,
            api_key=api_key,
            story_id=story_id
        )
        
        # Process the webhook with the triage agent
        result = await process_webhook(webhook_data, context)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Webhook processed in {processing_time:.2f} seconds")
        
        return {
            "status": "processed",
            "workspace_id": workspace_id,
            "story_id": story_id,
            "processing_time": f"{processing_time:.2f}s",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error processing webhook: {str(e)}")
        return {
            "status": "error",
            "reason": str(e),
            "workspace_id": workspace_id,
            "story_id": story_id if story_id else None
        }