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
from typing import Dict, Any, Optional, Tuple

# Add parent directory to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import environment utilities
from utils.env import load_env_vars, get_required_env

# Import Shortcut tools
from tools.shortcut.shortcut_tools import (
    create_story, 
    update_story, 
    get_story_details,
    get_workspace_labels
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("create_test_story")

async def get_workflow_and_project(api_key: str, reference_story_id: str = "309") -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Get workflow and project IDs from a reference story.
    
    Args:
        api_key: Shortcut API key
        reference_story_id: ID of a reference story to get workflow and project from
        
    Returns:
        Tuple of (workflow_id, project_id, workflow_state_id)
    """
    try:
        logger.info(f"Getting reference story {reference_story_id} to extract workflow and project IDs")
        story = await get_story_details(reference_story_id, api_key)
        
        workflow_id = story.get("workflow_id")
        project_id = story.get("project_id")
        workflow_state_id = story.get("workflow_state_id")
        
        if workflow_id:
            logger.info(f"Found workflow ID: {workflow_id}")
        if project_id:
            logger.info(f"Found project ID: {project_id}")
        if workflow_state_id:
            logger.info(f"Found workflow state ID: {workflow_state_id}")
            
        return workflow_id, project_id, workflow_state_id
    except Exception as e:
        logger.warning(f"Error getting reference story: {str(e)}")
        return None, None, None

async def create_test_story_with_tag(
    workspace_id: str,
    api_key: str,
    tag: str = "analyse",
    reference_story_id: str = "309",
    wait_seconds: int = 5
) -> Dict[str, Any]:
    """
    Create a test story in Shortcut and add the specified tag.
    
    Args:
        workspace_id: Shortcut workspace ID
        api_key: Shortcut API key
        tag: Tag to add (default: "analyse")
        reference_story_id: ID of a reference story to get workflow and project from
        wait_seconds: Seconds to wait before adding the tag
        
    Returns:
        Dictionary with story details
    """
    # Get workflow and project IDs from reference story
    workflow_id, project_id, workflow_state_id = await get_workflow_and_project(api_key, reference_story_id)
    
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
    
    # Try to use either project_id or workflow_state_id
    if project_id:
        story_data["project_id"] = project_id
        logger.info(f"Using project ID: {project_id}")
    elif workflow_state_id:
        # Use workflow_state_id which is required for creating stories
        story_data["workflow_state_id"] = workflow_state_id
        logger.info(f"Using workflow_state_id: {workflow_state_id}")
    else:
        logger.warning("No project ID or workflow state ID found. Story creation may fail.")
    
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
    
    # Add the tag to the story
    logger.info(f"Adding '{tag}' tag to story {story_id}")
    update_data = {
        "labels": [{"name": tag}]
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
    parser.add_argument("--reference", "-r", default="309", help="Reference story ID to get workflow and project from")
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
            reference_story_id=args.reference,
            wait_seconds=args.wait
        )
        
        # Print the story details
        print(json.dumps(story, indent=2))
        
    except Exception as e:
        logger.exception(f"Error creating test story: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 