#!/usr/bin/env python
"""
Test script to verify the OpenAI Agent SDK integration with real API credentials.
This script will attempt to use the real OpenAI Agent SDK if available.

Requirements:
- Valid OPENAI_API_KEY environment variable
- OpenAI Agent SDK installed
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_real_sdk")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set.")
    logger.error("Please set a valid API key to test with the real SDK.")
    sys.exit(1)

# Ensure USE_MOCK_AGENTS is set to false
os.environ["USE_MOCK_AGENTS"] = "false"

# Import required modules
try:
    from shortcut_agents.triage.triage_agent import TriageOutput, create_triage_agent, process_webhook
    from shortcut_agents.analysis.models import (
        ComponentScore, AnalysisResult, AnalysisMetadata, StoryAnalysisOutput
    )
    from shortcut_agents.analysis.analysis_agent import create_analysis_agent
    from shortcut_agents.update.models import UpdateResult
    from shortcut_agents.update.update_agent import create_update_agent
    from context.workspace.workspace_context import WorkspaceContext
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

async def test_triage_agent_with_sdk():
    """Test the Triage Agent with real OpenAI Agent SDK."""
    logger.info("Testing Triage Agent with real OpenAI Agent SDK...")
    
    # Create a workspace context
    workspace_context = WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345"
    )
    
    # Create a test webhook payload
    webhook_payload = {
        "primary_id": "12345",
        "actions": [{
            "action": "update",
            "changes": {
                "labels": {
                    "adds": [{"name": "enhance"}]
                }
            }
        }]
    }
    
    try:
        # Create a triage agent
        agent = create_triage_agent()
        
        # Run the agent with the real SDK
        result = await agent.run(webhook_payload, workspace_context)
        
        logger.info(f"Triage Agent completed with status: {result.get('status')}")
        
        if result.get("status") == "success":
            logger.info("Triage Agent test passed!")
        else:
            logger.error(f"Triage Agent error: {result.get('error')}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error testing Triage Agent: {e}")
        return {"status": "error", "error": str(e)}

async def test_analysis_agent_with_sdk():
    """Test the Analysis Agent with real OpenAI Agent SDK."""
    logger.info("Testing Analysis Agent with real OpenAI Agent SDK...")
    
    # Create a workspace context
    workspace_context = WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345"
    )
    
    # Create a test story
    story_data = {
        "id": "12345",
        "name": "Add User Authentication Feature",
        "description": """
        We need to implement user authentication for our web application.
        
        Users should be able to sign up, login, and logout.
        
        ## Acceptance Criteria
        - User can sign up with email and password
        - User can login with credentials
        - User can logout
        """,
        "story_type": "feature",
        "labels": [{"name": "enhance"}]
    }
    
    try:
        # Create an analysis agent
        agent = create_analysis_agent()
        
        # Run the agent with the real SDK
        result = await agent.run(story_data, workspace_context)
        
        logger.info(f"Analysis Agent completed with status: {result.get('status')}")
        
        if result.get("status") == "success":
            logger.info("Analysis Agent test passed!")
        else:
            logger.error(f"Analysis Agent error: {result.get('error')}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error testing Analysis Agent: {e}")
        return {"status": "error", "error": str(e)}

async def test_update_agent_with_sdk():
    """Test the Update Agent with real OpenAI Agent SDK."""
    logger.info("Testing Update Agent with real OpenAI Agent SDK...")
    
    # Create a workspace context
    workspace_context = WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345"
    )
    
    # Create a test update input
    update_input = {
        "story_id": "12345",
        "workspace_id": "test-workspace",
        "update_type": "analysis",
        "analysis_result": {
            "overall_score": 7,
            "title_analysis": {
                "score": 8,
                "strengths": ["Clear", "Concise"],
                "weaknesses": ["Could be more specific"],
                "recommendations": ["Add more context"]
            },
            "description_analysis": {
                "score": 6,
                "strengths": ["Basic info provided"],
                "weaknesses": ["Lacks detail"],
                "recommendations": ["Add more details"]
            },
            "acceptance_criteria_analysis": {
                "score": 7,
                "strengths": ["Covers basic scenarios"],
                "weaknesses": ["Missing edge cases"],
                "recommendations": ["Consider error scenarios"]
            },
            "priority_areas": ["Description improvement", "Edge case handling"],
            "summary": "Overall good story but needs more details in description."
        }
    }
    
    try:
        # Create an update agent
        agent = create_update_agent()
        
        # Run the agent with the real SDK
        result = await agent.run(update_input, workspace_context)
        
        logger.info(f"Update Agent completed with status: {result.get('status')}")
        
        if result.get("status") == "success":
            logger.info("Update Agent test passed!")
        else:
            logger.error(f"Update Agent error: {result.get('error')}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error testing Update Agent: {e}")
        return {"status": "error", "error": str(e)}

async def test_all_agents():
    """Test all agents with the real SDK."""
    logger.info("Testing all agents with real OpenAI Agent SDK...")
    
    results = {}
    
    # Test Triage Agent
    triage_result = await test_triage_agent_with_sdk()
    results["triage"] = triage_result
    
    # Test Analysis Agent
    analysis_result = await test_analysis_agent_with_sdk()
    results["analysis"] = analysis_result
    
    # Test Update Agent
    update_result = await test_update_agent_with_sdk()
    results["update"] = update_result
    
    # Summarize results
    successes = sum(1 for r in results.values() if r.get("status") == "success")
    total = len(results)
    
    logger.info(f"SDK Integration Test Results: {successes}/{total} passed")
    
    # Output results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"sdk_test_results_{timestamp}.json"
    
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Detailed results saved to {result_file}")
    
    return results

async def main():
    """Main entry point."""
    # Check if OpenAI Agent SDK is available
    try:
        # This import will fail if SDK is not properly installed
        from agents import Agent, Runner
        logger.info("OpenAI Agent SDK is available. Running integration tests...")
    except ImportError:
        logger.error("OpenAI Agent SDK is not available. Please install it before running this test.")
        return
    
    # Run the test for all agents
    await test_all_agents()

if __name__ == "__main__":
    asyncio.run(main())