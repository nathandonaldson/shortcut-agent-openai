#!/usr/bin/env python
"""
Test script for triage agent handoffs.

This script tests the handoff functionality from the triage agent to other agents.
"""

import os
import sys
import json
import logging
import argparse
import asyncio
from datetime import datetime
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_triage_handoff")

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from utils.env import load_env_vars, setup_openai_configuration
load_env_vars()

# Setup OpenAI configuration and tracing
setup_openai_configuration()

# Import required modules
from shortcut_agents.triage.triage_agent import TriageAgent
from context.workspace.workspace_context import WorkspaceContext
from tools.shortcut.shortcut_tools import get_story_details

async def test_triage_handoff(workspace_id: str, story_id: str, label: str = "enhance") -> Dict[str, Any]:
    """
    Test triage agent handoff.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID
        label: The label to test (default: enhance)
        
    Returns:
        The result of the test
    """
    logger.info(f"Testing triage handoff for workspace {workspace_id}, story {story_id}, label {label}")
    
    # Get API key for the workspace
    api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id.upper()}", 
                            os.environ.get("SHORTCUT_API_KEY"))
    
    if not api_key:
        raise ValueError(f"No API key found for workspace {workspace_id}")
    
    # Create workspace context
    context = WorkspaceContext(
        workspace_id=workspace_id,
        story_id=story_id,
        api_key=api_key
    )
    
    # Get story details
    story_data = await get_story_details(story_id, api_key)
    logger.info(f"Retrieved story details for story {story_id}")
    
    # Add the label to the story data
    if "labels" not in story_data:
        story_data["labels"] = []
    
    # Remove any existing labels that might conflict
    if label == "enhance":
        # Remove analyse label if it exists
        story_data["labels"] = [l for l in story_data["labels"] if l.get("name", "").lower() != "analyse"]
    elif label == "analyse":
        # Remove enhance label if it exists
        story_data["labels"] = [l for l in story_data["labels"] if l.get("name", "").lower() != "enhance"]
    
    # Check if the label already exists
    label_exists = False
    for existing_label in story_data["labels"]:
        if existing_label.get("name", "").lower() == label.lower():
            label_exists = True
            break
    
    # Add the label if it doesn't exist
    if not label_exists:
        story_data["labels"].append({"name": label})
        logger.info(f"Added {label} label to story data")
    
    # Set story data in context
    context.story_data = story_data
    
    # Create triage agent
    logger.info("Creating triage agent")
    triage_agent = TriageAgent()
    
    # Create a sample webhook payload
    webhook_payload = {
        "actions": [
            {
                "action": "label_update",
                "entity_type": "story",
                "id": story_id,
                "changes": {
                    "labels": {
                        "adds": [{"name": label}]
                    }
                }
            }
        ]
    }
    
    # Run the triage agent with simplified implementation
    logger.info("Running triage agent with simplified implementation")
    
    # Get the run_simplified method
    run_simplified = getattr(triage_agent, "run_simplified", None)
    
    if run_simplified:
        # Run the simplified implementation
        triage_result = await run_simplified(webhook_payload, context)
        
        # Check if triage was successful
        if triage_result.get("status") == "success" and triage_result.get("result", {}).get("processed"):
            # Get the workflow type
            workflow = triage_result.get("result", {}).get("workflow")
            
            if workflow == "enhance":
                # Import the update agent
                from shortcut_agents.update.update_agent import create_update_agent
                
                # Create the update agent
                logger.info("Creating update agent for enhancement")
                update_agent = create_update_agent()
                
                # Prepare input data for the update agent
                input_data = {
                    "workflow": "enhance",
                    "story_id": story_id,
                    "workspace_id": workspace_id,
                    "story_data": story_data,
                    "update_type": "enhancement",
                    "enhancement_result": {
                        "title": "Enhanced title",
                        "description": "Enhanced description",
                        "acceptance_criteria": "Enhanced acceptance criteria"
                    }
                }
                
                # Run the update agent with simplified implementation
                logger.info("Running update agent with simplified implementation")
                update_result = await update_agent.run_simplified(input_data, context)
                
                # Return the combined result
                return {
                    "status": "success",
                    "triage": triage_result,
                    "update": update_result
                }
            
            elif workflow in ["analyse", "analyze"]:
                # Import the analysis agent
                from shortcut_agents.analysis.analysis_agent import create_analysis_agent
                
                # Create the analysis agent
                logger.info("Creating analysis agent for analysis")
                analysis_agent = create_analysis_agent()
                
                # Prepare input data for the analysis agent
                input_data = {
                    "workflow": "analyse",
                    "story_id": story_id,
                    "workspace_id": workspace_id,
                    "story_data": story_data
                }
                
                # Run the analysis agent with simplified implementation
                logger.info("Running analysis agent with simplified implementation")
                analysis_result = await analysis_agent.run_simplified(input_data, context)
                
                # Return the combined result
                return {
                    "status": "success",
                    "triage": triage_result,
                    "analysis": analysis_result
                }
        
        # If no handoff was needed or possible, return the triage result
        return triage_result
    else:
        return {
            "status": "error",
            "message": "Triage agent does not have run_simplified method"
        }


async def async_main():
    """Async main function to run the test."""
    parser = argparse.ArgumentParser(description="Test triage agent handoffs")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--label", choices=["enhance", "analyse"], default="enhance", 
                        help="Label to test (default: enhance)")
    
    args = parser.parse_args()
    
    # Run the test
    result = await test_triage_handoff(args.workspace, args.story, args.label)
    
    # Print the result
    print(json.dumps(result, indent=2))
    
    return result


def main():
    """Main function to run the async test."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    main() 