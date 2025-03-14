import json
import os
import logging
import time
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from shortcut_agents.triage.triage_agent_refactored import process_webhook
from tools.shortcut.shortcut_tools import get_story_details

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_pipeline")

def get_api_key(workspace_id: str) -> str:
    """
    Get the API key for a specific workspace.
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

async def handler(request):
    """
    Test endpoint for the pipeline.
    
    This allows testing the full pipeline without a real webhook.
    It simulates a webhook event for the given parameters.
    """
    # Parse the request body
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON"})
        }
    
    # Get the required parameters
    workspace_id = body.get("workspace_id")
    story_id = body.get("story_id")
    workflow_type = body.get("workflow_type")
    
    if not workspace_id or not story_id or not workflow_type:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Missing required parameters",
                "required": ["workspace_id", "story_id", "workflow_type"]
            })
        }
    
    # Validate workflow type
    if workflow_type not in ["enhance", "analyse"]:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid workflow_type",
                "valid_values": ["enhance", "analyse"]
            })
        }
    
    # Run the test pipeline
    try:
        result = await run_test_pipeline(workspace_id, story_id, workflow_type)
        
        # Return the result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "completed",
                "result": result
            })
        }
    except Exception as e:
        logger.exception(f"Error running test pipeline: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": str(e)
            })
        }

async def run_test_pipeline(workspace_id: str, story_id: str, workflow_type: str) -> Dict[str, Any]:
    """
    Run a test pipeline for the given parameters.
    
    This simulates a webhook event for a story with the specified workflow type.
    """
    start_time = time.time()
    logger.info(f"Running test pipeline for {workflow_type} on story {story_id}")
    
    try:
        # Get API key for the workspace
        api_key = get_api_key(workspace_id)
        
        # Create workspace context
        context = WorkspaceContext(
            workspace_id=workspace_id,
            api_key=api_key,
            story_id=story_id
        )
        
        # Get story details
        story_data = await get_story_details(story_id, api_key)
        context.set_story_data(story_data)
        
        # Create a simulated webhook payload
        # This simulates a label being added to the story
        webhook_payload = {
            "action": "update",
            "id": int(story_id),
            "changes": {
                "labels": {
                    "adds": [{"name": workflow_type}]
                }
            },
            "primary_id": int(story_id),
            "references": []
        }
        
        # Process the webhook with the triage agent
        result = await process_webhook(webhook_payload, context)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Test pipeline completed in {processing_time:.2f} seconds")
        
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "story_id": story_id,
            "workflow_type": workflow_type,
            "processing_time": f"{processing_time:.2f}s",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error in test pipeline: {str(e)}")
        raise