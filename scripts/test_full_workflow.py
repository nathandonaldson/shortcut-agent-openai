#!/usr/bin/env python
"""
Test the full workflow integration from webhook to triage to analysis to update.
This script simulates a complete end-to-end flow through all agents.
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
logger = logging.getLogger("test_full_workflow")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force using mock agents for this full integration test
os.environ["USE_MOCK_AGENTS"] = "true"

# Import required modules
try:
    from api.webhook.handler import handle_webhook
    from shortcut_agents.triage.triage_agent import process_webhook
    from shortcut_agents.analysis.analysis_agent import process_analysis
    from shortcut_agents.update.update_agent import process_update
    from context.workspace.workspace_context import WorkspaceContext, WorkflowType
    from utils.tracing import setup_tracing, get_trace_processor
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

async def test_enhance_workflow():
    """Test the full enhancement workflow (triage -> analysis -> update)."""
    logger.info("Testing full enhance workflow...")
    
    # 1. Create a test webhook event
    webhook_payload = {
        "primary_id": "12345",
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
    
    # 3. Process the webhook through the handler
    logger.info("Step 1: Processing webhook...")
    webhook_result = await process_webhook_event(webhook_payload, "test-workspace")
    
    # 4. Extract context and results from triage
    logger.info("Step 2: Processing triage phase...")
    triage_result = await process_webhook(webhook_payload, workspace_context)
    
    if triage_result.get("status") == "error":
        logger.error(f"Triage error: {triage_result.get('error')}")
        return {"status": "error", "stage": "triage", "error": triage_result.get("error")}
    
    # Check if the webhook should be processed
    triage_output = triage_result.get("result", {})
    if not triage_output.get("processed", False):
        logger.info(f"Webhook not processed: {triage_output.get('reason')}")
        return {
            "status": "skipped", 
            "reason": triage_output.get("reason", "Not a relevant webhook")
        }
    
    # 5. Process analysis based on triage results
    logger.info("Step 3: Processing analysis phase...")
    analysis_result = await process_analysis(webhook_payload, workspace_context)
    
    if analysis_result.get("status") == "error":
        logger.error(f"Analysis error: {analysis_result.get('error')}")
        return {"status": "error", "stage": "analysis", "error": analysis_result.get("error")}
    
    # 6. Process update based on analysis results
    logger.info("Step 4: Processing update phase...")
    update_input = {
        "story_id": workspace_context.story_id,
        "workspace_id": workspace_context.workspace_id,
        "update_type": "enhancement",
        "analysis_result": analysis_result.get("result", {})
    }
    
    update_result = await process_update(workspace_context, "enhancement", analysis_result.get("result", {}))
    
    if update_result.get("status") == "error":
        logger.error(f"Update error: {update_result.get('error')}")
        return {"status": "error", "stage": "update", "error": update_result.get("error")}
    
    # 7. Collect all results
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
    
    logger.info("Full workflow completed successfully")
    return workflow_results

async def test_analyse_workflow():
    """Test the analysis-only workflow (triage -> analysis -> comment)."""
    logger.info("Testing analysis-only workflow...")
    
    # 1. Create a test webhook event
    webhook_payload = {
        "primary_id": "12345",
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
    
    # 3. Process the webhook through the handler
    logger.info("Step 1: Processing webhook...")
    webhook_result = await process_webhook_event(webhook_payload, "test-workspace")
    
    # 4. Extract context and results from triage
    logger.info("Step 2: Processing triage phase...")
    triage_result = await process_webhook(webhook_payload, workspace_context)
    
    if triage_result.get("status") == "error":
        logger.error(f"Triage error: {triage_result.get('error')}")
        return {"status": "error", "stage": "triage", "error": triage_result.get("error")}
    
    # Check if the webhook should be processed
    triage_output = triage_result.get("result", {})
    if not triage_output.get("processed", False):
        logger.info(f"Webhook not processed: {triage_output.get('reason')}")
        return {
            "status": "skipped", 
            "reason": triage_output.get("reason", "Not a relevant webhook")
        }
    
    # 5. Process analysis based on triage results
    logger.info("Step 3: Processing analysis phase...")
    analysis_result = await process_analysis(webhook_payload, workspace_context)
    
    if analysis_result.get("status") == "error":
        logger.error(f"Analysis error: {analysis_result.get('error')}")
        return {"status": "error", "stage": "analysis", "error": analysis_result.get("error")}
    
    # 6. Process update (comment-only) based on analysis results
    logger.info("Step 4: Processing update phase (comments only)...")
    update_input = {
        "story_id": workspace_context.story_id,
        "workspace_id": workspace_context.workspace_id,
        "update_type": "analysis",
        "analysis_result": analysis_result.get("result", {})
    }
    
    update_result = await process_update(workspace_context, "analysis", analysis_result.get("result", {}))
    
    if update_result.get("status") == "error":
        logger.error(f"Update error: {update_result.get('error')}")
        return {"status": "error", "stage": "update", "error": update_result.get("error")}
    
    # 7. Collect all results
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
    
    logger.info("Full workflow completed successfully")
    return workflow_results

async def main():
    """Main entry point."""
    # Setup tracing
    setup_tracing("test_full_workflow")
    
    logger.info("Starting full workflow integration test...")
    
    # Test both workflows
    enhance_result = await test_enhance_workflow()
    analyse_result = await test_analyse_workflow()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f"workflow_enhance_test_{timestamp}.json", "w") as f:
        json.dump(enhance_result, f, indent=2)
        
    with open(f"workflow_analyse_test_{timestamp}.json", "w") as f:
        json.dump(analyse_result, f, indent=2)
    
    logger.info("Full workflow integration test completed")
    
    # Summarize results
    enhance_status = enhance_result.get("status")
    analyse_status = analyse_result.get("status")
    
    logger.info(f"Enhance workflow: {enhance_status}")
    logger.info(f"Analyse workflow: {analyse_status}")
    
    if enhance_status == "success" and analyse_status == "success":
        logger.info("All workflows passed!")
    else:
        logger.warning("Some workflows failed, check the output files for details")

if __name__ == "__main__":
    asyncio.run(main())