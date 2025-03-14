"""
Webhook handler for Shortcut events.
Processes incoming webhooks and routes them appropriately.
"""

import os
import json
import time
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext
from shortcut_agents.triage.triage_agent import process_webhook
from utils.logging.logger import get_logger, trace_context
from utils.logging.webhook import (
    log_webhook_receipt,
    log_webhook_validation,
    log_webhook_processing_start,
    log_webhook_processing_complete,
    log_webhook_processing_error,
    extract_story_id,
    log_triage_decision
)

# Create component logger
logger = get_logger("webhook.handler")

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
        action_found = False
        if "actions" in data and data["actions"]:
            for action in data["actions"]:
                if action.get("action") == "update":
                    action_found = True
                    break
        
        if not action_found:
            logger.info("Ignoring non-update webhook event")
            return False
        
    # Check if there's a label change
    label_change_found = False
    
    # Check direct "changes" field (old format)
    changes = data.get("changes", {})
    if "labels" in changes:
        label_change_found = True
    
    # Check actions[].changes format (new format)
    if "actions" in data and data["actions"]:
        for action in data["actions"]:
            action_changes = action.get("changes", {})
            if "label_ids" in action_changes or "labels" in action_changes:
                label_change_found = True
                break
    
    if not label_change_found:
        logger.info("Ignoring update without label changes")
        return False
        
    return True

async def handle_webhook(workspace_id: str, webhook_data: Dict[str, Any], request_path: str = "", client_ip: str = "") -> Dict[str, Any]:
    """
    Main webhook handler function.
    
    Args:
        workspace_id: The workspace ID from the URL
        webhook_data: The webhook payload
        request_path: The request path (for logging)
        client_ip: The client IP address (for logging)
        
    Returns:
        Response data
    """
    start_time = time.time()
    
    # Log webhook receipt and get request ID for correlation
    request_id = log_webhook_receipt(
        workspace_id=workspace_id,
        path=request_path,
        client_ip=client_ip,
        headers={"Content-Type": "application/json"},
        data=webhook_data
    )
    
    # Extract story ID
    story_id = extract_story_id(webhook_data)
    
    # Set up trace context
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Basic validation
        is_valid = validate_webhook(webhook_data, workspace_id)
        log_webhook_validation(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            is_valid=is_valid,
            reason="Invalid or irrelevant webhook data" if not is_valid else None
        )
        
        if not is_valid:
            # Calculate processing time
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "status": "skipped",
                "reason": "Invalid or irrelevant webhook data",
                "workspace_id": workspace_id,
                "request_id": request_id,
                "duration_ms": duration_ms
            }
        
        # Verify story ID
        if not story_id:
            # Log error
            log_webhook_processing_error(
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=None,
                error="Could not extract story ID",
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
            return {
                "status": "error",
                "reason": "Could not extract story ID",
                "workspace_id": workspace_id,
                "request_id": request_id
            }
        
        try:
            # Log processing start
            log_webhook_processing_start(
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id
            )
            
            # Get API key for the workspace
            api_key = get_api_key(workspace_id)
            
            # Create workspace context with request ID
            context = WorkspaceContext(
                workspace_id=workspace_id,
                api_key=api_key,
                story_id=story_id
            )
            
            # Add request_id to context for correlation
            context.request_id = request_id
            
            # Process the webhook with the triage agent
            logger.info(f"Processing webhook with triage agent")
            result = await process_webhook(webhook_data, context)
            
            # Log triage decision
            log_triage_decision(
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                decision=result.get("workflow", "unknown"),
                triage_result=result
            )
            
            # Calculate processing time
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log processing complete
            log_webhook_processing_complete(
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                result=result,
                duration_ms=duration_ms
            )
            
            return {
                "status": "processed",
                "workspace_id": workspace_id,
                "story_id": story_id,
                "request_id": request_id,
                "duration_ms": duration_ms,
                "result": result
            }
            
        except Exception as e:
            # Calculate processing time
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            log_webhook_processing_error(
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Re-log as standard logger for compatibility
            logger.exception(f"Error processing webhook: {str(e)}")
            
            return {
                "status": "error",
                "reason": str(e),
                "workspace_id": workspace_id,
                "story_id": story_id if story_id else None,
                "request_id": request_id,
                "duration_ms": duration_ms
            }