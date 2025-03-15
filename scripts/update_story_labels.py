#!/usr/bin/env python3
"""
Simple script to update labels on a Shortcut story.
"""

import os
import sys
import json
import argparse
import asyncio
import logging
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("update_labels")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.shortcut.shortcut_tools import update_story, get_story_details
from utils.env import load_env_vars

async def update_labels(workspace_id: str, story_id: str, labels_to_add: List[str], labels_to_remove: List[str]):
    """Update labels on a Shortcut story."""
    # Load environment variables
    load_env_vars()
    
    # Get API key for workspace
    api_key_var = f"SHORTCUT_API_KEY_{workspace_id.upper()}"
    api_key = os.environ.get(api_key_var)
    if not api_key:
        api_key = os.environ.get("SHORTCUT_API_KEY")
    
    if not api_key:
        logger.error(f"No API key found for workspace {workspace_id}")
        return
    
    # Get current story details
    logger.info(f"Getting story details for {story_id}")
    story = await get_story_details(story_id, api_key)
    
    # Prepare label update
    update_data = {}
    
    # For adding labels, we need to get the current labels and add to them
    current_labels = story.get("labels", [])
    current_label_names = [label["name"] for label in current_labels]
    
    # Add new labels that aren't already present
    new_labels = current_labels.copy()
    for label_to_add in labels_to_add:
        if label_to_add not in current_label_names:
            new_labels.append({"name": label_to_add})
    
    # Remove labels that should be removed
    final_labels = [label for label in new_labels if label["name"] not in labels_to_remove]
    
    # Set the labels array directly
    update_data["labels"] = final_labels
    
    # Log the update data
    logger.info(f"Updating labels with data: {json.dumps(update_data)}")
    
    # Update the story
    try:
        updated_story = await update_story(story_id, api_key, update_data)
        logger.info(f"Successfully updated story {story_id}")
        
        # Get the updated labels
        updated_labels = [label["name"] for label in updated_story.get("labels", [])]
        logger.info(f"Updated labels: {updated_labels}")
        
        return updated_story
    except Exception as e:
        logger.error(f"Error updating story: {str(e)}")
        return None

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update labels on a Shortcut story")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--add", action="append", default=[], help="Labels to add (can be specified multiple times)")
    parser.add_argument("--remove", action="append", default=[], help="Labels to remove (can be specified multiple times)")
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Updating story {args.story} in workspace {args.workspace}")
    logger.info(f"Adding labels: {args.add}")
    logger.info(f"Removing labels: {args.remove}")
    
    result = await update_labels(args.workspace, args.story, args.add, args.remove)
    
    if result:
        print("\n" + "=" * 80)
        print(f"LABEL UPDATE SUCCESS")
        print("=" * 80)
        print(f"Story: {result.get('name')}")
        print(f"Labels: {[label['name'] for label in result.get('labels', [])]}")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(f"LABEL UPDATE FAILED")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main()) 