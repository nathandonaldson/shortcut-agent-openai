#!/usr/bin/env python3
"""
Utility script to get the details of a story in Shortcut.
"""

import os
import sys
import json
import asyncio
import argparse
import logging

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
logger = logging.getLogger("get_story_details")

async def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Get the details of a story in Shortcut")
    parser.add_argument("--workspace", "-w", help="Shortcut workspace ID")
    parser.add_argument("--story", "-s", required=True, help="Story ID to get details for")
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
        # Get the story details
        story = await get_story_details(args.story, api_key)
        
        # Print the story details
        print(json.dumps(story, indent=2))
        
    except Exception as e:
        logger.exception(f"Error getting story details: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 