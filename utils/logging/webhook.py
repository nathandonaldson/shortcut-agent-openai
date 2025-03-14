"""
Webhook logging adapter for the Shortcut Enhancement System.
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from utils.logging.logger import get_logger, trace_context

# Create webhook logger
webhook_logger = get_logger("webhook.handler")

def log_webhook_receipt(workspace_id: str,
                       path: str,
                       client_ip: str,
                       headers: Dict[str, str],
                       data: Dict[str, Any]) -> str:
    """
    Log the receipt of a webhook.
    
    Args:
        workspace_id: Workspace ID from the URL
        path: Request path
        client_ip: Client IP address
        headers: Request headers
        data: Webhook data
        
    Returns:
        Request ID for correlation
    """
    # Generate a request ID
    request_id = str(uuid.uuid4())
    
    # Extract story ID if available
    story_id = extract_story_id(data)
    
    # Create trace context
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log webhook receipt
        webhook_logger.info(
            "Webhook received",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            path=path,
            client_ip=client_ip,
            content_type=headers.get("Content-Type", "")
        )
        
        # Log webhook data (limited to avoid huge logs)
        webhook_logger.debug(
            "Webhook data",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            data_preview=str(data)[:500] + ("..." if len(str(data)) > 500 else "")
        )
        
        # Save webhook data to file
        save_webhook_log(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            path=path,
            client_ip=client_ip,
            headers=headers,
            data=data
        )
    
    return request_id

def log_webhook_validation(request_id: str,
                          workspace_id: str,
                          story_id: Optional[str],
                          is_valid: bool,
                          reason: Optional[str] = None) -> None:
    """
    Log webhook validation result.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID (if available)
        is_valid: Whether the webhook is valid
        reason: Reason for validation failure (if any)
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log validation result
        if is_valid:
            webhook_logger.info(
                "Webhook validated",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id
            )
        else:
            webhook_logger.warning(
                f"Webhook validation failed: {reason}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                reason=reason
            )

def log_webhook_processing_start(request_id: str,
                                workspace_id: str,
                                story_id: str) -> None:
    """
    Log the start of webhook processing.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        webhook_logger.info(
            "Processing webhook",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            event="process_start"
        )

def log_webhook_processing_complete(request_id: str,
                                   workspace_id: str,
                                   story_id: str,
                                   result: Dict[str, Any],
                                   duration_ms: int) -> None:
    """
    Log the completion of webhook processing.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        result: Processing result
        duration_ms: Processing duration in milliseconds
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        webhook_logger.info(
            "Webhook processing complete",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            event="process_complete",
            duration_ms=duration_ms,
            processed=result.get("processed", False),
            workflow=result.get("workflow", "none")
        )

def log_webhook_processing_error(request_id: str,
                               workspace_id: str,
                               story_id: Optional[str],
                               error: str,
                               duration_ms: int) -> None:
    """
    Log an error during webhook processing.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID (if available)
        error: Error message
        duration_ms: Processing duration until error (milliseconds)
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        webhook_logger.error(
            f"Webhook processing error: {error}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            event="process_error",
            error=error,
            duration_ms=duration_ms
        )

def extract_story_id(webhook_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract the story ID from webhook data.
    
    Args:
        webhook_data: The webhook data
        
    Returns:
        Story ID or None if not found
    """
    # Extract story ID - exact field name depends on webhook structure
    # Check primary_id first (new format)
    if "primary_id" in webhook_data:
        return str(webhook_data["primary_id"])
    
    # Check id directly (old format)
    if "id" in webhook_data:
        return str(webhook_data["id"])
    
    # Check actions[].id (new format)
    if "actions" in webhook_data and webhook_data["actions"]:
        for action in webhook_data["actions"]:
            if "id" in action and action.get("entity_type") == "story":
                return str(action["id"])
    
    # Check story_id (possible format)
    if "story_id" in webhook_data:
        return str(webhook_data["story_id"])
    
    # Check resource.id (possible format)
    if "resource" in webhook_data and "id" in webhook_data["resource"]:
        return str(webhook_data["resource"]["id"])
    
    return None

def save_webhook_log(request_id: str,
                    workspace_id: str,
                    story_id: Optional[str],
                    path: str,
                    client_ip: str,
                    headers: Dict[str, str],
                    data: Dict[str, Any]) -> None:
    """
    Save webhook data to a log file.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID (if available)
        path: Request path
        client_ip: Client IP address
        headers: Request headers
        data: Webhook data
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create log filename with request ID and timestamp
        filename = f"webhook_{timestamp}_{request_id[:8]}.json"
        filepath = os.path.join(logs_dir, filename)
        
        # Prepare log data
        log_data = {
            "timestamp": timestamp,
            "request_id": request_id,
            "workspace_id": workspace_id,
            "story_id": story_id,
            "path": path,
            "client_ip": client_ip,
            "headers": headers,
            "data": data
        }
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        webhook_logger.debug(f"Webhook data saved to {filepath}")
    except Exception as e:
        webhook_logger.error(f"Error saving webhook log: {str(e)}")

def log_triage_decision(request_id: str,
                       workspace_id: str,
                       story_id: str,
                       decision: str,
                       triage_result: Dict[str, Any]) -> None:
    """
    Log a triage decision.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        decision: Triage decision (workflow type)
        triage_result: Full triage result
    """
    triage_logger = get_logger("triage.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        if triage_result.get("processed", False):
            triage_logger.info(
                f"Triage decision: {decision}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                decision=decision,
                processed=True
            )
            
            # Log task info if available
            if "task_info" in triage_result:
                task_info = triage_result["task_info"]
                triage_logger.info(
                    "Task queued",
                    request_id=request_id,
                    workspace_id=workspace_id,
                    story_id=story_id,
                    task_type=decision,
                    task_key=task_info.get("task_key", "unknown")
                )
        else:
            triage_logger.info(
                f"Triage decision: skip processing",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                reason=triage_result.get("reason", "unknown"),
                processed=False
            )