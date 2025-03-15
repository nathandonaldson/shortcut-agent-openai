#!/usr/bin/env python3
"""
End-to-end test script that:
1. Creates a test story with the "analyse" tag
2. Waits for the story to be processed
3. Retrieves the story details to verify it was enhanced
"""

import os
import sys
import json
import time
import asyncio
import argparse
import logging
from typing import Dict, Any, Optional

# Add parent directory to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import environment utilities
from utils.env import load_env_vars

# Import Shortcut tools
from tools.shortcut.shortcut_tools import get_story_details

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_end_to_end")

async def create_test_story(workspace_id: str, api_key: str, tag: str = "analyse") -> Dict[str, Any]:
    """
    Create a test story using the create_test_story.py script.
    
    Args:
        workspace_id: Shortcut workspace ID
        api_key: Shortcut API key
        tag: Tag to add (default: "analyse")
        
    Returns:
        Dictionary with story details
    """
    logger.info(f"Creating test story with '{tag}' tag")
    
    # Import the create_test_story function
    from scripts.create_test_story import create_test_story_with_tag
    
    # Create the story
    story = await create_test_story_with_tag(
        workspace_id=workspace_id,
        api_key=api_key,
        tag=tag,
        wait_seconds=0  # No need to wait, we'll add the tag immediately
    )
    
    story_id = story.get("id")
    logger.info(f"Created story with ID {story_id}")
    logger.info(f"Story URL: https://app.shortcut.com/{workspace_id}/story/{story_id}")
    
    return story

async def wait_for_processing(story_id: str, api_key: str, max_wait_time: int = 20, check_interval: int = 2) -> Dict[str, Any]:
    """
    Wait for the story to be processed by checking for changes in the story.
    
    Args:
        story_id: ID of the story to check
        api_key: Shortcut API key
        max_wait_time: Maximum time to wait in seconds (default: 20 seconds)
        check_interval: Time between checks in seconds (default: 2 seconds)
        
    Returns:
        The processed story details
    """
    logger.info(f"Waiting for story {story_id} to be processed (max wait: {max_wait_time} seconds)")
    
    # Get initial story details
    initial_story = await get_story_details(story_id, api_key)
    initial_comments_count = len(initial_story.get("comments", []))
    initial_labels = [label.get("name") for label in initial_story.get("labels", [])]
    
    logger.info(f"Initial state - Comments: {initial_comments_count}, Labels: {initial_labels}")
    
    # Start waiting
    start_time = time.time()
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        # Wait for the check interval
        await asyncio.sleep(check_interval)
        
        # Get current story details
        current_story = await get_story_details(story_id, api_key)
        current_comments_count = len(current_story.get("comments", []))
        current_labels = [label.get("name") for label in current_story.get("labels", [])]
        
        # Check if there are new comments or labels
        if current_comments_count > initial_comments_count:
            logger.info(f"Story processed! New comments detected: {current_comments_count - initial_comments_count}")
            return current_story
        
        # Check if labels have changed (excluding the trigger label)
        new_labels = [label for label in current_labels if label != "analyse" and label not in initial_labels]
        if new_labels:
            logger.info(f"Story processed! New labels detected: {new_labels}")
            return current_story
        
        # Update elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Still waiting... Elapsed time: {int(elapsed_time)} seconds")
    
    logger.warning(f"Reached maximum wait time ({max_wait_time} seconds). Story may not have been processed.")
    return await get_story_details(story_id, api_key)

def verify_enhancement(original_story: Dict[str, Any], processed_story: Dict[str, Any]) -> bool:
    """
    Verify that the story was enhanced by checking for new comments and labels.
    
    Args:
        original_story: The original story details
        processed_story: The processed story details
        
    Returns:
        True if the story was enhanced, False otherwise
    """
    # Check for new comments
    original_comments = original_story.get("comments", [])
    processed_comments = processed_story.get("comments", [])
    
    new_comments = len(processed_comments) - len(original_comments)
    
    # Check for new labels (excluding the trigger label)
    original_labels = [label.get("name") for label in original_story.get("labels", [])]
    processed_labels = [label.get("name") for label in processed_story.get("labels", [])]
    
    new_labels = [label for label in processed_labels if label != "analyse" and label not in original_labels]
    
    # Print verification results
    logger.info("=== Enhancement Verification ===")
    logger.info(f"New comments: {new_comments}")
    if new_comments > 0:
        for i, comment in enumerate(processed_comments[-new_comments:]):
            logger.info(f"Comment {i+1}: {comment.get('text')[:100]}...")
    
    logger.info(f"New labels: {new_labels}")
    
    # Story is considered enhanced if there are new comments or labels
    is_enhanced = new_comments > 0 or len(new_labels) > 0
    
    if is_enhanced:
        logger.info("✅ Story was successfully enhanced!")
    else:
        logger.warning("❌ Story does not appear to have been enhanced.")
    
    return is_enhanced

async def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="End-to-end test for story creation and enhancement")
    parser.add_argument("--workspace", "-w", help="Shortcut workspace ID")
    parser.add_argument("--tag", "-t", default="analyse", help="Tag to add (default: analyse)")
    parser.add_argument("--wait-time", type=int, default=20, help="Maximum time to wait for processing in seconds (default: 20)")
    parser.add_argument("--check-interval", type=int, default=2, help="Time between checks in seconds (default: 2)")
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
        # Step 1: Create a test story
        original_story = await create_test_story(workspace_id, api_key, args.tag)
        story_id = original_story.get("id")
        
        # Step 2: Wait for the story to be processed
        processed_story = await wait_for_processing(
            story_id, 
            api_key, 
            max_wait_time=args.wait_time, 
            check_interval=args.check_interval
        )
        
        # Step 3: Verify the story was enhanced
        is_enhanced = verify_enhancement(original_story, processed_story)
        
        # Exit with appropriate status code
        sys.exit(0 if is_enhanced else 1)
        
    except Exception as e:
        logger.exception(f"Error in end-to-end test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 