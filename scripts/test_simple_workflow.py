#!/usr/bin/env python
"""
Test the Pydantic models and agent implementations directly.
This script bypasses the webhook handler and tests each agent directly.
"""

import os
import sys
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_simple_workflow")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force using mock agents for this integration test
os.environ["USE_MOCK_AGENTS"] = "true"

# Import required modules
try:
    from shortcut_agents.triage.triage_agent import process_webhook, TriageOutput
    from shortcut_agents.analysis.analysis_agent import process_analysis
    from shortcut_agents.update.update_agent import process_update
    from context.workspace.workspace_context import WorkspaceContext, WorkflowType
    from utils.tracing import create_trace_id, record_handoff
    from utils.logging.logger import get_logger, trace_context
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

async def test_enhance_workflow():
    """Test the full enhancement workflow (triage -> analysis -> update)."""
    logger.info("Testing enhance workflow...")
    
    # 1. Create a test story data
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
        "actions": [{
            "action": "update",
            "changes": {
                "labels": {
                    "adds": [{"name": "enhance"}]
                }
            }
        }]
    }
    
    # 2. Set up the workspace context
    workspace_context = WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345",
        request_id=f"test_{int(datetime.now().timestamp())}"
    )
    
    # 3. Process triage
    logger.info("Step 1: Processing triage...")
    triage_result = await process_webhook(story_data, workspace_context)
    
    if triage_result.get("status") == "error":
        logger.error(f"Triage error: {triage_result.get('error')}")
        return {"status": "error", "stage": "triage", "error": triage_result.get("error")}
    
    # Check if the webhook should be processed
    triage_output = triage_result.get("result", {})
    if not triage_output.get("processed", False):
        logger.info(f"Story not processed: {triage_output.get('reason')}")
        return {
            "status": "skipped", 
            "reason": triage_output.get("reason", "Not a relevant story")
        }
    
    # 4. Process analysis
    logger.info("Step 2: Processing analysis...")
    analysis_result = await process_analysis(story_data, workspace_context)
    
    if analysis_result.get("status") == "error":
        logger.error(f"Analysis error: {analysis_result.get('error')}")
        return {"status": "error", "stage": "analysis", "error": analysis_result.get("error")}
    
    # 5. Process update 
    logger.info("Step 3: Processing update...")
    update_result = await process_update(workspace_context, "enhancement", analysis_result.get("result", {}))
    
    if update_result.get("status") == "error":
        logger.error(f"Update error: {update_result.get('error')}")
        return {"status": "error", "stage": "update", "error": update_result.get("error")}
    
    # 6. Collect all results
    workflow_results = {
        "status": "success",
        "workflow": "enhance",
        "request_id": workspace_context.request_id,
        "story_id": workspace_context.story_id,
        "workspace_id": workspace_context.workspace_id,
        "stages": {
            "triage": triage_result,
            "analysis": analysis_result,
            "update": update_result
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info("Enhance workflow completed successfully")
    return workflow_results

async def test_analysis_workflow():
    """Test the analysis-only workflow (triage -> analysis -> comment)."""
    logger.info("Testing analysis workflow...")
    
    # 1. Create a test story data
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
        "actions": [{
            "action": "update",
            "changes": {
                "labels": {
                    "adds": [{"name": "analyse"}]
                }
            }
        }]
    }
    
    # 2. Set up the workspace context
    workspace_context = WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345",
        request_id=f"test_{int(datetime.now().timestamp())}"
    )
    
    # 3. Process triage
    logger.info("Step 1: Processing triage...")
    triage_result = await process_webhook(story_data, workspace_context)
    
    if triage_result.get("status") == "error":
        logger.error(f"Triage error: {triage_result.get('error')}")
        return {"status": "error", "stage": "triage", "error": triage_result.get("error")}
    
    # Check if the webhook should be processed
    triage_output = triage_result.get("result", {})
    if not triage_output.get("processed", False):
        logger.info(f"Story not processed: {triage_output.get('reason')}")
        return {
            "status": "skipped", 
            "reason": triage_output.get("reason", "Not a relevant story")
        }
    
    # 4. Process analysis
    logger.info("Step 2: Processing analysis...")
    analysis_result = await process_analysis(story_data, workspace_context)
    
    if analysis_result.get("status") == "error":
        logger.error(f"Analysis error: {analysis_result.get('error')}")
        return {"status": "error", "stage": "analysis", "error": analysis_result.get("error")}
    
    # 5. Process update (comment-only)
    logger.info("Step 3: Processing update (comments only)...")
    update_result = await process_update(workspace_context, "analysis", analysis_result.get("result", {}))
    
    if update_result.get("status") == "error":
        logger.error(f"Update error: {update_result.get('error')}")
        return {"status": "error", "stage": "update", "error": update_result.get("error")}
    
    # 6. Collect all results
    workflow_results = {
        "status": "success",
        "workflow": "analyse",
        "request_id": workspace_context.request_id,
        "story_id": workspace_context.story_id,
        "workspace_id": workspace_context.workspace_id,
        "stages": {
            "triage": triage_result,
            "analysis": analysis_result,
            "update": update_result
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info("Analysis workflow completed successfully")
    return workflow_results

async def main():
    """Main entry point."""
    # Setup basic trace context
    trace_id = create_trace_id()
    request_id = f"test_{int(time.time())}"
    
    logger.info("Starting direct agent workflow test...")
    
    # Test both workflows
    enhance_result = await test_enhance_workflow()
    analysis_result = await test_analysis_workflow()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f"workflow_enhance_direct_test_{timestamp}.json", "w") as f:
        json.dump(enhance_result, f, indent=2)
        
    with open(f"workflow_analyse_direct_test_{timestamp}.json", "w") as f:
        json.dump(analysis_result, f, indent=2)
    
    logger.info("Direct agent workflow tests completed")
    
    # Summarize results
    enhance_status = enhance_result.get("status")
    analysis_status = analysis_result.get("status")
    
    logger.info(f"Enhance workflow: {enhance_status}")
    logger.info(f"Analysis workflow: {analysis_status}")
    
    if enhance_status == "success" and analysis_status == "success":
        logger.info("All workflows passed!")
    else:
        logger.warning("Some workflows failed, check the output files for details")

if __name__ == "__main__":
    asyncio.run(main())