#!/usr/bin/env python
"""
Test script to verify the Pydantic models for agent outputs.
"""

import sys
import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_agent_models")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from shortcut_agents.triage.triage_agent import TriageOutput, create_triage_agent
from shortcut_agents.analysis.models import (
    ComponentScore, AnalysisResult, AnalysisMetadata, StoryAnalysisOutput
)
from shortcut_agents.update.models import UpdateResult
from context.workspace.workspace_context import WorkspaceContext

async def test_triage_output():
    """Test TriageOutput Pydantic model."""
    logger.info("Testing TriageOutput model...")
    
    # Create an instance
    output = TriageOutput(
        processed=True,
        workflow="enhance",
        story_id="12345",
        workspace_id="test-workspace",
        reason=None,
        next_steps=["Queue for enhancement"]
    )
    
    # Test model_dump (Pydantic v2)
    if hasattr(output, "model_dump") and callable(output.model_dump):
        result = output.model_dump()
        logger.info(f"model_dump result: {json.dumps(result, indent=2)}")
    
    # Test dict (Pydantic v1)
    if hasattr(output, "dict") and callable(output.dict):
        result = output.dict()
        logger.info(f"dict result: {json.dumps(result, indent=2)}")
    
    logger.info("TriageOutput model test completed successfully.")
    return output

async def test_analysis_output():
    """Test AnalysisResult and related Pydantic models."""
    logger.info("Testing Analysis models...")
    
    # Create ComponentScore instances
    title_analysis = ComponentScore(
        score=8,
        strengths=["Clear objective", "Uses action verb"],
        weaknesses=["Missing context", "Could be more specific"],
        recommendations=["Add more context to the title", "Make title more specific"]
    )
    
    description_analysis = ComponentScore(
        score=6,
        strengths=["Basic information present", "Includes purpose"],
        weaknesses=["Lacks detail", "Missing background context"],
        recommendations=["Include more detailed requirements", "Add background context"]
    )
    
    acceptance_criteria_analysis = ComponentScore(
        score=5,
        strengths=["Basic criteria included"],
        weaknesses=["Not specific enough", "Missing testable outcomes"],
        recommendations=["Make criteria more specific", "Add testable outcomes"]
    )
    
    # Create AnalysisResult
    analysis_result = AnalysisResult(
        overall_score=7,
        title_analysis=title_analysis,
        description_analysis=description_analysis,
        acceptance_criteria_analysis=acceptance_criteria_analysis,
        priority_areas=["Improve description detail", "Add acceptance criteria"],
        summary="This story needs improvements in several areas."
    )
    
    # Create AnalysisMetadata
    metadata = AnalysisMetadata(
        workspace_id="test-workspace",
        story_id="12345",
        timestamp="2025-03-14T12:00:00Z",
        model_used="gpt-4o-mini",
        version="1.0"
    )
    
    # Create StoryAnalysisOutput
    output = StoryAnalysisOutput(
        result=analysis_result,
        metadata=metadata,
        raw_story={"id": "12345", "name": "Test Story", "description": "Description"}
    )
    
    # Test model_dump (Pydantic v2)
    if hasattr(output, "model_dump") and callable(output.model_dump):
        result = output.model_dump()
        logger.info(f"model_dump result available (length: {len(str(result))})")
    
    # Test dict (Pydantic v1)
    if hasattr(output, "dict") and callable(output.dict):
        result = output.dict()
        logger.info(f"dict result available (length: {len(str(result))})")
    
    logger.info("Analysis models test completed successfully.")
    return output

async def test_update_output():
    """Test UpdateResult Pydantic model."""
    logger.info("Testing UpdateResult model...")
    
    # Create an instance
    output = UpdateResult(
        success=True,
        story_id="12345",
        workspace_id="test-workspace",
        update_type="enhancement",
        fields_updated=["title", "description"],
        tags_added=["enhanced"],
        tags_removed=["enhance"],
        comment_added=True,
        error_message=None
    )
    
    # Test model_dump (Pydantic v2)
    if hasattr(output, "model_dump") and callable(output.model_dump):
        result = output.model_dump()
        logger.info(f"model_dump result: {json.dumps(result, indent=2)}")
    
    # Test dict (Pydantic v1)
    if hasattr(output, "dict") and callable(output.dict):
        result = output.dict()
        logger.info(f"dict result: {json.dumps(result, indent=2)}")
    
    logger.info("UpdateResult model test completed successfully.")
    return output

async def test_agent_with_models():
    """Test agent execution with models."""
    logger.info("Testing agent with models...")
    
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
    
    # Create a triage agent
    agent = create_triage_agent()
    
    # Set the USE_MOCK_AGENTS environment variable to ensure mock mode
    os.environ["USE_MOCK_AGENTS"] = "true"
    
    # Run the agent in simplified mode
    result = await agent.run_simplified(webhook_payload, workspace_context)
    
    logger.info(f"Agent result: {json.dumps(result, indent=2)}")
    logger.info("Agent test completed successfully.")
    return result

async def main():
    """Run the tests."""
    logger.info("Starting agent output models test...")
    
    # Run the tests
    triage_output = await test_triage_output()
    analysis_output = await test_analysis_output()
    update_output = await test_update_output()
    agent_result = await test_agent_with_models()
    
    logger.info("All tests completed successfully.")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())