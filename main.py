"""
Main entry point for local development.
This is not used in production on Vercel, only for local testing.
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

# Ensure project root is in sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Load environment variables
from utils.env import load_env_vars
load_env_vars()

# Import webhook handler
from api.webhook.handler import handle_webhook
from api.test_pipeline import run_test_pipeline

async def simulate_webhook(workspace_id: str, story_id: str, label: str = "enhance") -> Dict[str, Any]:
    """
    Simulate a webhook event for local testing.
    
    Args:
        workspace_id: The Shortcut workspace ID
        story_id: The story ID to process
        label: The label to add ("enhance" or "analyse")
        
    Returns:
        The webhook processing result
    """
    logger.info(f"Simulating webhook for workspace {workspace_id}, story {story_id}, label {label}")
    
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

async def run_test(workspace_id: str, story_id: str, workflow_type: str) -> Dict[str, Any]:
    """
    Run a test pipeline for the given parameters.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID
        workflow_type: The workflow type ("enhance" or "analyse")
        
    Returns:
        The test results
    """
    logger.info(f"Running test pipeline for {workflow_type} on story {story_id}")
    
    # Run the test pipeline
    result = await run_test_pipeline(workspace_id, story_id, workflow_type)
    
    return result

async def main() -> None:
    """Main function for local development and testing"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Shortcut Enhancement System - Local Development")
    parser.add_argument("--test", action="store_true", help="Run a test pipeline")
    parser.add_argument("--simulate", action="store_true", help="Simulate a webhook event")
    parser.add_argument("--workspace", required=True, help="Shortcut workspace ID")
    parser.add_argument("--story", required=True, help="Story ID to process")
    parser.add_argument("--type", choices=["enhance", "analyse"], default="enhance",
                       help="Workflow type (enhance or analyse)")
    args = parser.parse_args()
    
    # Run the appropriate function
    try:
        if args.test:
            result = await run_test(args.workspace, args.story, args.type)
            logger.info("Test pipeline completed")
        elif args.simulate:
            result = await simulate_webhook(args.workspace, args.story, args.type)
            logger.info("Webhook simulation completed")
        else:
            logger.error("No action specified. Use --test or --simulate")
            return
        
        # Print the result
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())