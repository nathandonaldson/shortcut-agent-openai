#!/usr/bin/env python
"""
Test script for agent handoffs.

This script tests the handoff functionality between agents by directly creating them.
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
logger = logging.getLogger("test_handoffs")

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from utils.env import load_env_vars, setup_openai_configuration
load_env_vars()

# Setup OpenAI configuration and tracing
setup_openai_configuration()

# Import required modules
from shortcut_agents.triage.triage_agent import create_triage_agent
from shortcut_agents.update.update_agent import create_update_agent
from shortcut_agents.analysis.analysis_agent import create_analysis_agent
from context.workspace.workspace_context import WorkspaceContext
from tools.shortcut.shortcut_tools import get_story_details

async def test_direct_agent_creation(workspace_id: str, story_id: str, workflow: str = "enhance") -> Dict[str, Any]:
    """
    Test agent creation and handoff directly.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID
        workflow: The workflow to test (default: enhance)
        
    Returns:
        The result of the test
    """
    logger.info(f"Testing direct agent creation for workspace {workspace_id}, story {story_id}, workflow {workflow}")
    
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
    
    # Set story data in context
    context.story_data = story_data
    
    # Create agents
    logger.info("Creating agents")
    
    if workflow == "enhance":
        logger.info("Creating update agent for enhancement")
        agent = create_update_agent()
        
        # Prepare input data
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
    else:
        logger.info("Creating analysis agent for analysis")
        agent = create_analysis_agent()
        
        # Prepare input data
        input_data = {
            "workflow": "analyse",
            "story_id": story_id,
            "workspace_id": workspace_id,
            "story_data": story_data
        }
    
    # Run the agent with simplified implementation
    logger.info(f"Running {workflow} agent with simplified implementation")
    
    # Get the run_simplified method
    run_simplified = getattr(agent, "run_simplified", None)
    
    if run_simplified:
        # Run the simplified implementation
        result = await run_simplified(input_data, context)
        
        return {
            "status": "success",
            "agent": workflow,
            "result": result
        }
    else:
        return {
            "status": "error",
            "message": f"Agent does not have run_simplified method"
        }


async def async_main():
    """Async main function to run the test."""
    parser = argparse.ArgumentParser(description="Test agent handoffs")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--workflow", choices=["enhance", "analyse"], default="enhance", 
                        help="Workflow to test (default: enhance)")
    
    args = parser.parse_args()
    
    # Run the test
    result = await test_direct_agent_creation(args.workspace, args.story, args.workflow)
    
    # Print the result
    print(json.dumps(result, indent=2))
    
    return result


def main():
    """Main function to run the async test."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    main() 