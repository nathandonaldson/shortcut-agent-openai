"""
Triage Agent for determining how to process Shortcut stories.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional

from openai import OpenAI

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from tools.shortcut.shortcut_tools import (
    get_story_details, 
    queue_enhancement_task, 
    queue_analysis_task
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("triage_agent")

# Triage agent system message
TRIAGE_SYSTEM_MESSAGE = """
You are the Triage Agent for a Shortcut story enhancement system. Your job is to:

1. Analyze the incoming webhook data to determine if it requires processing
2. Determine the appropriate workflow based on the story labels
3. Queue the appropriate task (enhancement or analysis)

You should only process story updates with specific labels:
- Stories with the "enhance" label should be queued for enhancement
- Stories with the "analyse" or "analyze" label should be queued for analysis only

Ignore all other webhook events that don't involve these labels being added.
"""

def get_triage_model() -> str:
    """Get the model to use for the triage agent"""
    # Use environment variable with default fallback
    return os.environ.get("MODEL_TRIAGE", "gpt-3.5-turbo")

def create_triage_agent():
    """Create and configure the triage agent (simplified version)"""
    
    model = get_triage_model()
    logger.info(f"Creating triage agent with model: {model}")
    
    # In a real implementation, we would create an OpenAI Agents SDK agent
    # For now, we'll just return a dummy object for local testing
    return {
        "name": "Triage Agent",
        "model": model,
        "instructions": TRIAGE_SYSTEM_MESSAGE
    }

async def process_webhook(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook event and determine the appropriate action.
    
    Args:
        webhook_data: The raw webhook data from Shortcut
        workspace_context: The workspace context
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing webhook for workspace: {workspace_context.workspace_id}")
    
    # Create the triage agent (simplified for local testing)
    triage_agent = create_triage_agent()
    logger.info(f"Using triage agent: {triage_agent['name']} with model {triage_agent['model']}")
    
    # In a real implementation, we would use the OpenAI Agents SDK to run the agent
    # For now, we'll implement simplified logic for testing
    
    # Extract the story ID from the webhook data
    story_id = str(webhook_data.get("id", ""))
    if not story_id and "primary_id" in webhook_data:
        story_id = str(webhook_data.get("primary_id", ""))
    
    logger.info(f"Processing story ID: {story_id}")
    
    # Get label changes
    label_adds = []
    
    # Check direct changes (old format)
    changes = webhook_data.get("changes", {})
    if "labels" in changes and "adds" in changes.get("labels", {}):
        label_adds.extend(changes["labels"]["adds"])
    
    # Check actions[].changes (new format)
    if "actions" in webhook_data and webhook_data["actions"]:
        for action in webhook_data["actions"]:
            action_changes = action.get("changes", {})
            
            # Check for label_ids
            if "label_ids" in action_changes and "adds" in action_changes.get("label_ids", {}):
                # In this format, we get label IDs
                label_id_adds = action_changes["label_ids"]["adds"]
                
                # If references are provided, map IDs to names
                if "references" in webhook_data:
                    for label_ref in webhook_data.get("references", []):
                        if label_ref.get("entity_type") == "label":
                            for label_id_obj in label_id_adds:
                                if isinstance(label_id_obj, dict) and label_id_obj.get("id") == label_ref.get("id"):
                                    label_adds.append({"name": label_ref.get("name")})
                                elif isinstance(label_id_obj, int) and label_id_obj == label_ref.get("id"):
                                    label_adds.append({"name": label_ref.get("name")})
                else:
                    # Just add the IDs as is
                    for label_id_obj in label_id_adds:
                        if isinstance(label_id_obj, dict) and "name" in label_id_obj:
                            label_adds.append({"name": label_id_obj.get("name")})
            
            # Also check direct labels field
            if "labels" in action_changes and "adds" in action_changes.get("labels", {}):
                label_adds.extend(action_changes["labels"]["adds"])
    
    # Check if we found any label additions
    if not label_adds:
        logger.info("No label additions found in webhook data")
        return {
            "processed": False,
            "reason": "No label additions found",
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id
        }
    
    # Check for specific labels
    label_names = [label.get("name", "").lower() for label in label_adds]
    logger.info(f"Labels added: {label_names}")
    
    # Determine workflow type based on labels
    if "enhance" in label_names:
        logger.info("Enhancement workflow triggered")
        # Queue for enhancement
        task_info = await queue_enhancement_task(
            workspace_context.workspace_id,
            story_id,
            workspace_context.api_key
        )
        
        return {
            "processed": True,
            "workflow": "enhance",
            "task_info": task_info,
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id
        }
        
    elif "analyse" in label_names or "analyze" in label_names:
        logger.info("Analysis workflow triggered")
        # Queue for analysis
        task_info = await queue_analysis_task(
            workspace_context.workspace_id,
            story_id,
            workspace_context.api_key
        )
        
        return {
            "processed": True,
            "workflow": "analyse",
            "task_info": task_info,
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id
        }
    
    logger.info("No relevant labels found")
    return {
        "processed": False,
        "reason": "No relevant labels found",
        "labels": label_names,
        "workspace_id": workspace_context.workspace_id,
        "story_id": story_id
    }