#!/usr/bin/env python3
"""
Utility script to create a test story in Shortcut and add the "analyse" tag to it.
This is useful for testing the webhook and agent functionality.
"""

import os
import sys
import json
import time
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import environment utilities
from utils.env import load_env_vars, get_required_env

# Import Shortcut tools
from tools.shortcut.shortcut_tools import (
    create_story, 
    update_story, 
    get_story_details,
    get_workspace_labels,
    get_workflows
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("create_test_story")

async def create_test_story_with_tag(
    workspace_id: str,
    api_key: str,
    tag: str = "analyse",
    project_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    wait_seconds: int = 5
) -> Dict[str, Any]:
    """
    Create a test story in Shortcut and add the specified tag.
    
    Args:
        workspace_id: Shortcut workspace ID
        api_key: Shortcut API key
        tag: Tag to add (default: "analyse")
        project_id: Project ID to create the story in (optional)
        workflow_id: Workflow ID to create the story in (optional)
        wait_seconds: Seconds to wait before adding the tag
        
    Returns:
        Dictionary with story details
    """
    # Generate a timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create story data
    story_data = {
        "name": f"Test Story for Analysis {timestamp}",
        "description": f"""
# Test Story for Analysis

This is a test story created by the create_test_story.py script at {timestamp}.

## Background
This story is created to test the Shortcut Enhancement System's analysis functionality.

## Requirements
- The system should analyze this story
- The system should add a comment with the analysis results
- The system should update the story labels

## Acceptance Criteria
- [ ] Story is analyzed by the system
- [ ] Analysis results are added as a comment
- [ ] Story labels are updated appropriately
        """,
        "story_type": "feature"
    }
    
    # Add project ID if provided
    if project_id:
        story_data["project_id"] = int(project_id)
    
    # Add workflow ID if provided
    if workflow_id:
        story_data["workflow_id"] = int(workflow_id)
    else:
        # Get workflows and use the first one
        try:
            workflows = await get_workflows(api_key)
            if workflows:
                workflow_id = str(workflows[0]["id"])
                story_data["workflow_id"] = int(workflow_id)
                logger.info(f"Using workflow ID {workflow_id} ({workflows[0]['name']})")
        except Exception as e:
            logger.warning(f"Error getting workflows: {str(e)}")
    
    # Create the story
    logger.info(f"Creating test story in workspace {workspace_id}")
    story = await create_story(api_key, story_data)
    
    # Get the story ID
    story_id = story.get("id")
    if not story_id:
        raise ValueError("Failed to get story ID from created story")
    
    logger.info(f"Created story with ID {story_id}")
    
    # Wait before adding the tag
    if wait_seconds > 0:
        logger.info(f"Waiting {wait_seconds} seconds before adding the tag...")
        time.sleep(wait_seconds)
    
    # Get workspace labels to check if the tag exists
    labels = await get_workspace_labels(api_key)
    
    # Check if the tag exists
    tag_exists = any(label.get("name") == tag for label in labels)
    
    # Add the tag to the story
    logger.info(f"Adding '{tag}' tag to story {story_id}")
    update_data = {
        "labels": {
            "adds": [{"name": tag}]
        }
    }
    
    updated_story = await update_story(story_id, api_key, update_data)
    
    # Get the full story details
    story_details = await get_story_details(story_id, api_key)
    
    logger.info(f"Successfully added '{tag}' tag to story {story_id}")
    logger.info(f"Story URL: https://app.shortcut.com/{workspace_id}/story/{story_id}")
    
    return story_details

async def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Create a test story in Shortcut and add a tag")
    parser.add_argument("--workspace", "-w", help="Shortcut workspace ID")
    parser.add_argument("--tag", "-t", default="analyse", help="Tag to add (default: analyse)")
    parser.add_argument("--project", "-p", help="Project ID to create the story in")
    parser.add_argument("--workflow", "-f", help="Workflow ID to create the story in")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait before adding the tag")
    args = parser.parse_args()
    
    # Load environment variables
    load_env_vars()
    
    # Get workspace ID
    workspace_id = args.workspace
    if not workspace_id:
        # Try to get from environment
        workspace_id = os.environ.get("SHORTCUT_WORKSPACE_ID")
        if not workspace_id:
            workspace_id = "workspace1"  # Default fallback
    
    # Get API key
    api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id}")
    if not api_key:
        # Try uppercase
        api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id.upper()}")
    if not api_key:
        # Try lowercase
        api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id.lower()}")
    if not api_key:
        # Fall back to default
        api_key = os.environ.get("SHORTCUT_API_KEY")
    
    if not api_key:
        logger.error(f"No API key found for workspace {workspace_id}")
        sys.exit(1)
    
    try:
        # Create the test story and add the tag
        story = await create_test_story_with_tag(
            workspace_id=workspace_id,
            api_key=api_key,
            tag=args.tag,
            project_id=args.project,
            workflow_id=args.workflow,
            wait_seconds=args.wait
        )
        
        # Print the story details
        print(json.dumps(story, indent=2))
        
    except Exception as e:
        logger.exception(f"Error creating test story: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 