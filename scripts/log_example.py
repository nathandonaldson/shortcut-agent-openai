#!/usr/bin/env python3
"""
Example script demonstrating the logging system for a typical Shortcut story analysis.
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import logging system
from utils.logging.logger import get_logger, configure_global_logging, trace_context
from utils.logging.webhook import log_webhook_receipt, log_webhook_processing_start
from utils.logging.agent import (
    log_agent_start, 
    log_agent_completion, 
    log_tool_use, 
    log_tool_result, 
    log_analysis_result
)

# Configure global logging
configure_global_logging(
    log_dir="logs",
    log_filename="example.log",
    console_level="INFO",
    file_level="DEBUG"
)

# Get loggers for different components
webhook_logger = get_logger("webhook.handler")
triage_logger = get_logger("triage.agent")
analysis_logger = get_logger("analysis.agent")

def simulate_webhook_processing():
    """Simulate processing a webhook from Shortcut."""
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    workspace_id = "workspace1"
    story_id = "12345"
    
    print(f"Simulating webhook processing for story {story_id} in workspace {workspace_id}")
    print(f"Request ID: {request_id}")
    print("-" * 80)
    
    # Simulate webhook data
    webhook_data = {
        "id": story_id,
        "primary_id": story_id,
        "actions": [
            {
                "id": story_id,
                "entity_type": "story",
                "action": "update",
                "changes": {
                    "label_ids": {
                        "adds": [
                            {"id": 123, "name": "enhance"}
                        ]
                    }
                }
            }
        ]
    }
    
    # Log webhook receipt
    log_webhook_receipt(
        workspace_id=workspace_id,
        path=f"/api/webhook/{workspace_id}",
        client_ip="127.0.0.1",
        headers={"Content-Type": "application/json"},
        data=webhook_data
    )
    
    # Set up trace context for the entire operation
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log processing start
        log_webhook_processing_start(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        )
        
        # Simulate triage agent
        simulate_triage_agent(request_id, workspace_id, story_id)
        
        # Simulate analysis agent (based on triage decision)
        simulate_analysis_agent(request_id, workspace_id, story_id)
        
        # Log webhook processing complete
        webhook_logger.info(
            "Webhook processing complete",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            duration_ms=2500
        )
    
    print("\nSimulation complete. Check logs/example.log for details.")
    print("You can also run: python scripts/follow_logs.py -f logs/example.log")

def simulate_triage_agent(request_id, workspace_id, story_id):
    """Simulate the triage agent processing."""
    # Log agent start
    log_agent_start(
        agent_type="triage",
        agent_name="Triage Agent",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        model="gpt-3.5-turbo"
    )
    
    # Log getting story details
    log_tool_use(
        agent_type="triage",
        agent_name="Triage Agent",
        tool_name="get_story_details",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        parameters={"story_id": story_id}
    )
    
    # Simulate delay
    time.sleep(0.5)
    
    # Log tool result
    log_tool_result(
        agent_type="triage",
        agent_name="Triage Agent",
        tool_name="get_story_details",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=500,
        success=True,
        result_summary="Story details retrieved successfully"
    )
    
    # Log triage decision
    triage_logger.info(
        "Triage decision: enhance",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        decision="enhance",
        workflow_type="enhance",
        event="triage_decision"
    )
    
    # Log agent completion
    log_agent_completion(
        agent_type="triage",
        agent_name="Triage Agent",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=800,
        result_summary={"processed": True, "workflow": "enhance"}
    )
    
    # Log agent handoff
    triage_logger.info(
        "Handing off to Analysis Agent",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        from_agent="Triage Agent",
        to_agent="Analysis Agent",
        event="agent_handoff"
    )

def simulate_analysis_agent(request_id, workspace_id, story_id):
    """Simulate the analysis agent processing."""
    # Log agent start
    log_agent_start(
        agent_type="analysis",
        agent_name="Analysis Agent",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        model="gpt-4o"
    )
    
    # Simulate analyzing title
    log_tool_use(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_title",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        parameters={"title": "Add user profile settings page"}
    )
    
    # Simulate delay
    time.sleep(0.3)
    
    # Log tool result
    log_tool_result(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_title",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=300,
        success=True,
        result_summary="Title score: 8/10"
    )
    
    # Simulate analyzing description
    log_tool_use(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_description",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        parameters={"description": "We need to add a user profile settings page..."}
    )
    
    # Simulate delay
    time.sleep(0.5)
    
    # Log tool result
    log_tool_result(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_description",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=500,
        success=True,
        result_summary="Description score: 6/10"
    )
    
    # Simulate analyzing acceptance criteria
    log_tool_use(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_acceptance_criteria",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        parameters={"description": "We need to add a user profile settings page...\n\n## Acceptance Criteria\n- User can update profile\n- ..."}
    )
    
    # Simulate delay
    time.sleep(0.4)
    
    # Log tool result
    log_tool_result(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="analyze_acceptance_criteria",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=400,
        success=True,
        result_summary="Acceptance criteria score: 7/10"
    )
    
    # Log analysis result
    log_analysis_result(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        overall_score=7,
        title_score=8,
        description_score=6,
        acceptance_criteria_score=7,
        priority_areas=[
            "Improve description detail", 
            "Add acceptance criteria for edge cases", 
            "Clarify expected outcomes"
        ]
    )
    
    # Log adding comment
    log_tool_use(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="add_comment",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        parameters={"story_id": story_id, "text": "## Analysis Results\n\nOverall Score: 7/10\n..."}
    )
    
    # Simulate delay
    time.sleep(0.3)
    
    # Log tool result
    log_tool_result(
        agent_type="analysis",
        agent_name="Analysis Agent",
        tool_name="add_comment",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=300,
        success=True,
        result_summary="Comment added successfully"
    )
    
    # Log agent completion
    log_agent_completion(
        agent_type="analysis",
        agent_name="Analysis Agent",
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id,
        duration_ms=1500,
        result_summary={"overall_score": 7, "priority_areas": 3}
    )

if __name__ == "__main__":
    simulate_webhook_processing()