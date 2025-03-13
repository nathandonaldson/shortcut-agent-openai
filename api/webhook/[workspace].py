import json
import asyncio
from typing import Dict, Any

from api.webhook.handler import handle_webhook

async def handler(request):
    """
    Webhook handler for Shortcut events.
    
    This is the entry point for the Vercel serverless function.
    It receives webhook payloads from Shortcut and processes them.
    
    Args:
        request: The Vercel serverless function request object
        
    Returns:
        Response object for the serverless function
    """
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
    
    # Process the webhook
    result = await handle_webhook(workspace_id, body)
    
    # Return a success response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "accepted",
            "result": result
        })
    }