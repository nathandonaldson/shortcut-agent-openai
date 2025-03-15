#!/usr/bin/env python3
"""
Test script for verifying agent handoffs with the OpenAI Agent SDK.

This script simulates a webhook event and checks that the triage agent
properly hands off to the analysis or update agent.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_handoffs")

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
from utils.env import load_env_vars, setup_openai_configuration
load_env_vars()

# Setup OpenAI configuration and tracing
setup_openai_configuration()

# Import webhook handler
from api.webhook.handler import handle_webhook
from context.workspace.workspace_context import WorkspaceContext

async def test_handoff(workspace_id: str, story_id: str, label: str = "enhance") -> Dict[str, Any]:
    """
    Test agent handoffs by simulating a webhook event.
    
    Args:
        workspace_id: The Shortcut workspace ID
        story_id: The story ID to process
        label: The label to add ("enhance" or "analyse")
        
    Returns:
        The webhook processing result
    """
    logger.info(f"Testing handoff for workspace {workspace_id}, story {story_id}, label {label}")
    
    # Create a sample webhook payload
    # This simulates a label being added to a story
    webhook_payload = {
        "action": "update",
        "id": int(story_id),
        "changes": {
            "labels": {
                "adds": [{"name": label}]
            }
        },
        "primary_id": int(story_id),
        "references": []
    }
    
    # Process the webhook
    result = await handle_webhook(workspace_id, webhook_payload)
    
    return result

async def main() -> None:
    """Main function for testing handoffs"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Agent Handoffs")
    parser.add_argument("--workspace", required=True, help="Shortcut workspace ID")
    parser.add_argument("--story", required=True, help="Story ID to process")
    parser.add_argument("--type", choices=["enhance", "analyse"], default="enhance",
                       help="Workflow type (enhance or analyse)")
    args = parser.parse_args()
    
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable is not set")
        logger.error("Handoffs require the OpenAI Agent SDK which needs an API key")
        sys.exit(1)
    
    # Run the test
    try:
        logger.info("Starting handoff test")
        result = await test_handoff(args.workspace, args.story, args.type)
        
        # Check if handoff was processed
        if "result" in result and "handoff" in result["result"]:
            handoff = result["result"]["handoff"]
            logger.info(f"Handoff detected: {json.dumps(handoff, indent=2)}")
            logger.info("Handoff test successful!")
        else:
            logger.warning("No handoff detected in the result")
            logger.info(f"Result: {json.dumps(result, indent=2)}")
        
        # Print the result
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 