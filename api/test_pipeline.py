import json
import os
from typing import Dict, Any

# This is a test endpoint for the pipeline
# It allows testing the full pipeline without a real webhook

def handler(request):
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
    result = run_test_pipeline(workspace_id, story_id, workflow_type)
    
    # Return the result
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "completed",
            "result": result
        })
    }

def run_test_pipeline(workspace_id: str, story_id: str, workflow_type: str) -> Dict[str, Any]:
    """
    Run a test pipeline for the given parameters.
    This is a placeholder for actual implementation.
    """
    # In a real implementation, you would:
    # 1. Create a simulated webhook payload
    # 2. Create a context object
    # 3. Run the triage agent
    # 4. Return the result
    
    # For now, just return a dummy result
    return {
        "status": "success",
        "message": f"Test pipeline run for {workflow_type} on story {story_id} in workspace {workspace_id}"
    }