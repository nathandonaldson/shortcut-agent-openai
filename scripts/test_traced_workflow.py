#!/usr/bin/env python3
"""
Test script for agent workflows with trace context visualization.

This script allows testing the full agent workflow with trace context
visualization. It simulates a webhook event and follows the trace
through all agent handoffs.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from shortcut_agents.triage.triage_agent import process_webhook
from utils.logging.logger import configure_global_logging, get_logger
from utils.tracing import create_trace_id, trace_context
from tools.shortcut.shortcut_tools import get_story_details

# Set up logging
configure_global_logging(
    log_dir="logs",
    log_filename=f"traced_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    console_level="INFO",
    file_level="DEBUG",
    console_format="text",
    file_format="json"
)

# Get logger
logger = get_logger("traced_workflow")

def get_api_key(workspace_id: str) -> str:
    """
    Get the API key for a specific workspace.
    
    Args:
        workspace_id: The ID of the workspace
        
    Returns:
        The API key for the workspace
    """
    # Look for workspace-specific API key in environment variables
    env_var_name = f"SHORTCUT_API_KEY_{workspace_id.upper()}"
    api_key = os.environ.get(env_var_name)
    
    if not api_key:
        # Fall back to generic API key
        api_key = os.environ.get("SHORTCUT_API_KEY")
        
    if not api_key:
        logger.error(f"No API key found for workspace: {workspace_id}")
        raise ValueError(f"No API key found for workspace: {workspace_id}")
        
    return api_key

async def run_traced_workflow(workspace_id: str, story_id: str, workflow_type: str) -> Dict[str, Any]:
    """
    Run a workflow with trace context and visualization.
    
    Args:
        workspace_id: Workspace ID
        story_id: Story ID
        workflow_type: Workflow type ("enhance" or "analyse")
        
    Returns:
        The result of the workflow
    """
    start_time = time.time()
    logger.info(f"Running traced workflow for {workflow_type} on story {story_id}")
    
    # Create a trace ID for this workflow
    trace_id = create_trace_id()
    
    # Create a request ID
    request_id = f"request-{int(time.time())}"
    
    try:
        # Get API key for the workspace
        api_key = get_api_key(workspace_id)
        
        # Create workspace context
        context = WorkspaceContext(
            workspace_id=workspace_id,
            api_key=api_key,
            story_id=story_id
        )
        
        # Set up trace context
        with trace_context(trace_id=trace_id, request_id=request_id):
            # Log trace start
            logger.info(
                f"Starting traced workflow {workflow_type}",
                trace_id=trace_id,
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                workflow_type=workflow_type
            )
            
            # Get story details
            story_data = await get_story_details(story_id, api_key)
            context.set_story_data(story_data)
            
            # Create a simulated webhook payload
            # This simulates a label being added to the story
            webhook_payload = {
                "action": "update",
                "id": int(story_id),
                "changes": {
                    "labels": {
                        "adds": [{"name": workflow_type}]
                    }
                },
                "primary_id": int(story_id),
                "references": []
            }
            
            # Process the webhook with the triage agent
            logger.info("Calling triage agent process_webhook")
            result = await process_webhook(webhook_payload, context)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(
                f"Traced workflow completed in {processing_time:.2f} seconds",
                trace_id=trace_id,
                request_id=request_id,
                duration_seconds=processing_time,
                result_status=result.get("status", "unknown")
            )
            
            return {
                "status": "success",
                "workspace_id": workspace_id,
                "story_id": story_id,
                "workflow_type": workflow_type,
                "processing_time": f"{processing_time:.2f}s",
                "trace_id": trace_id,
                "request_id": request_id,
                "result": result
            }
            
    except Exception as e:
        # Log the error
        logger.exception(
            f"Error in traced workflow: {str(e)}",
            trace_id=trace_id,
            request_id=request_id,
            error=str(e)
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return {
            "status": "error",
            "workspace_id": workspace_id,
            "story_id": story_id,
            "workflow_type": workflow_type,
            "error": str(e),
            "processing_time": f"{processing_time:.2f}s",
            "trace_id": trace_id,
            "request_id": request_id
        }

def print_trace_summary(result: Dict[str, Any]) -> None:
    """
    Print a summary of the trace.
    
    Args:
        result: The workflow result
    """
    log_filename = f"traced_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    print("\n" + "=" * 80)
    print(f"TRACED WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"Workspace ID: {result['workspace_id']}")
    print(f"Story ID:     {result['story_id']}")
    print(f"Workflow:     {result['workflow_type']}")
    print(f"Status:       {result['status']}")
    print(f"Duration:     {result['processing_time']}")
    print(f"Trace ID:     {result['trace_id']}")
    print(f"Request ID:   {result['request_id']}")
    print("-" * 80)
    
    if result['status'] == "success":
        workflow_result = result.get('result', {})
        print(f"Workflow Type: {workflow_result.get('workflow', 'unknown')}")
        
        if 'analysis_results' in workflow_result:
            analysis = workflow_result['analysis_results']
            print(f"Analysis Score: {analysis.get('quality_score', 'N/A')}")
            print("Recommendations:")
            for rec in analysis.get('recommendations', []):
                print(f"  - {rec}")
                
        if 'update_results' in workflow_result:
            update = workflow_result['update_results']
            print(f"Update Success: {update.get('success', False)}")
            print(f"Fields Updated: {', '.join(update.get('fields_updated', []))}")
            print(f"Tags Added:     {', '.join(update.get('tags_added', []))}")
            print(f"Tags Removed:   {', '.join(update.get('tags_removed', []))}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print(f"TRACE VALIDATION STATUS: {'✅ PASSED' if result['status'] == 'success' else '❌ FAILED'}")
    print("-" * 80)
    print(f"Log file: logs/{log_filename}")
    
    if result['status'] == 'success':
        print("\nNext steps:")
        print("1. Review the log file for trace context preservation")
        print("2. Test with additional stories to verify stability")
        print("3. Deploy to production for final validation")
    else:
        print("\nTroubleshooting steps:")
        print("1. Check the log file for error details")
        print("2. Run unit tests to verify component functionality:")
        print("   pytest tests/unit/agents/test_base_agent.py")
        print("   pytest tests/unit/agents/triage/test_triage_agent.py")
        print("3. Fix issues and retry the workflow test")
    
    print("=" * 80 + "\n")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test agent workflows with trace context")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--workflow", choices=["enhance", "analyse"], default="enhance",
                      help="Workflow type (enhance or analyse)")
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    print(f"Running {args.workflow} workflow for story {args.story} in workspace {args.workspace}")
    print("This will simulate adding the tag to the story and tracing the full agent workflow.\n")
    
    # Run the workflow
    result = await run_traced_workflow(args.workspace, args.story, args.workflow)
    
    # Print summary
    print_trace_summary(result)
    
    # Return success or failure
    return 0 if result['status'] == 'success' else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)