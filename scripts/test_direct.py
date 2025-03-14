#!/usr/bin/env python3
"""
Test script for running a full workflow with real APIs.

This script tests the entire enhancement workflow with:
1. Real OpenAI Agent SDK
2. Real Shortcut API

Usage:
    python scripts/test_direct.py --workspace <workspace_id> --story <story_id> --workflow <enhance|analyse>
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Set environment variables for real API usage
os.environ["USE_MOCK_AGENTS"] = "false"  # Use real OpenAI agents
os.environ["USE_REAL_SHORTCUT"] = "true"  # Use real Shortcut API

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from shortcut_agents.triage.triage_agent import process_webhook
from tools.shortcut.shortcut_tools import get_story_details
from utils.logging.logger import configure_global_logging, get_logger

# Set up logging
configure_global_logging(
    log_dir="logs",
    log_filename=f"direct_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    console_level="INFO",
    file_level="DEBUG",
    console_format="text",
    file_format="json"
)

# Get logger
logger = get_logger("direct_test")

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

def _format_analysis_comment(analysis_results: Dict[str, Any], story_id: str) -> str:
    """
    Format analysis results as a Markdown comment.
    
    Args:
        analysis_results: Analysis results dictionary
        story_id: Story ID
        
    Returns:
        Formatted Markdown comment
    """
    # Start building the comment
    comment = f"## 📊 Story Analysis Results\n\n"
    
    # Overall score
    overall_score = analysis_results.get('overall_score', 'N/A')
    comment += f"**Overall Quality Score**: {overall_score}/10\n\n"
    
    # Summary
    summary = analysis_results.get('summary', 'No summary provided')
    comment += f"### Summary\n{summary}\n\n"
    
    # Title analysis
    title_analysis = analysis_results.get('title_analysis', {})
    if title_analysis:
        title_score = title_analysis.get('score', 'N/A')
        comment += f"### Title Analysis\n**Score**: {title_score}/10\n\n"
        
        strengths = title_analysis.get('strengths', [])
        if strengths:
            comment += "**Strengths**:\n"
            for strength in strengths:
                comment += f"- {strength}\n"
            comment += "\n"
            
        weaknesses = title_analysis.get('weaknesses', [])
        if weaknesses:
            comment += "**Weaknesses**:\n"
            for weakness in weaknesses:
                comment += f"- {weakness}\n"
            comment += "\n"
            
        recommendations = title_analysis.get('recommendations', [])
        if recommendations:
            comment += "**Recommendations**:\n"
            for rec in recommendations:
                comment += f"- {rec}\n"
            comment += "\n"
    
    # Description analysis
    desc_analysis = analysis_results.get('description_analysis', {})
    if desc_analysis:
        desc_score = desc_analysis.get('score', 'N/A')
        comment += f"### Description Analysis\n**Score**: {desc_score}/10\n\n"
        
        strengths = desc_analysis.get('strengths', [])
        if strengths:
            comment += "**Strengths**:\n"
            for strength in strengths:
                comment += f"- {strength}\n"
            comment += "\n"
            
        weaknesses = desc_analysis.get('weaknesses', [])
        if weaknesses:
            comment += "**Weaknesses**:\n"
            for weakness in weaknesses:
                comment += f"- {weakness}\n"
            comment += "\n"
            
        recommendations = desc_analysis.get('recommendations', [])
        if recommendations:
            comment += "**Recommendations**:\n"
            for rec in recommendations:
                comment += f"- {rec}\n"
            comment += "\n"
    
    # Acceptance criteria analysis
    ac_analysis = analysis_results.get('acceptance_criteria_analysis', {})
    if ac_analysis:
        ac_score = ac_analysis.get('score', 'N/A')
        comment += f"### Acceptance Criteria Analysis\n**Score**: {ac_score}/10\n\n"
        
        strengths = ac_analysis.get('strengths', [])
        if strengths:
            comment += "**Strengths**:\n"
            for strength in strengths:
                comment += f"- {strength}\n"
            comment += "\n"
            
        weaknesses = ac_analysis.get('weaknesses', [])
        if weaknesses:
            comment += "**Weaknesses**:\n"
            for weakness in weaknesses:
                comment += f"- {weakness}\n"
            comment += "\n"
            
        recommendations = ac_analysis.get('recommendations', [])
        if recommendations:
            comment += "**Recommendations**:\n"
            for rec in recommendations:
                comment += f"- {rec}\n"
            comment += "\n"
    
    # Priority areas
    priority_areas = analysis_results.get('priority_areas', [])
    if priority_areas:
        comment += "### Priority Areas for Improvement\n"
        for area in priority_areas:
            comment += f"- {area}\n"
        comment += "\n"
    
    # Add footer
    comment += "\n---\n"
    comment += "Powered by Shortcut Enhancement System | "
    comment += f"[View Story](https://app.shortcut.com/{workspace_id}/story/{story_id})"
    
    return comment

async def run_direct_test(workspace_id: str, story_id: str, workflow_type: str):
    """
    Run a direct test with real APIs.
    
    Args:
        workspace_id: Workspace ID
        story_id: Story ID
        workflow_type: Workflow type ("enhance" or "analyse")
        
    Returns:
        Tuple of (result, context) with the workflow result and context
    """
    logger.info(f"Running direct test for {workflow_type} on story {story_id}")
    
    # Verify OpenAI API key
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not set, cannot run test with real APIs")
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Get Shortcut API key
    api_key = get_api_key(workspace_id)
    
    # Create workspace context
    context = WorkspaceContext(
        workspace_id=workspace_id,
        api_key=api_key,
        story_id=story_id
    )
    
    # Get story details
    try:
        logger.info(f"Fetching story details for {story_id}")
        story_data = await get_story_details(story_id, api_key)
        if hasattr(story_data, '__await__'):  # Check if it's a coroutine
            story_data = await story_data
        context.set_story_data(story_data)
        logger.info(f"Successfully fetched story: {story_data.get('name', 'Unknown')}")
    except Exception as e:
        logger.error(f"Error fetching story: {str(e)}")
        raise
    
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
    
    try:
        # Process the webhook with the triage agent
        logger.info("Calling triage agent process_webhook")
        triage_result = await process_webhook(webhook_payload, context)
        
        logger.info(f"Triage completed with result: {triage_result}")
        
        # Check triage result for workflow information
        triage_workflow = triage_result.get('result', {}).get('workflow')
        logger.info(f"Triage workflow from result: {triage_workflow}")
        
        # Debug context workflow type
        logger.info(f"Context workflow type before: {context.workflow_type}")
        
        # Manually set workflow type based on triage result if needed
        if triage_workflow == 'analyse' and not context.workflow_type:
            logger.info("Manually setting workflow type to ANALYSE based on triage result")
            context.set_workflow_type(WorkflowType.ANALYSE)
        elif triage_workflow == 'enhance' and not context.workflow_type:
            logger.info("Manually setting workflow type to ENHANCE based on triage result")
            context.set_workflow_type(WorkflowType.ENHANCE)
        
        # Check again
        logger.info(f"Context workflow type after: {context.workflow_type}")
        
        # Check if we need to continue with analysis or enhancement
        if context.workflow_type:
            logger.info(f"Continuing with {context.workflow_type.name} workflow")
            
            # Import necessary agents based on workflow type
            if context.workflow_type.name == "ANALYSE":
                from shortcut_agents.analysis.analysis_agent import create_analysis_agent
                
                # Create and run analysis agent
                logger.info("Creating analysis agent")
                analysis_agent = create_analysis_agent()
                
                # Run analysis on the story data
                logger.info("Running analysis agent")
                analysis_result = await analysis_agent.run(context.story_data, context)
                logger.info(f"Analysis completed with result: {analysis_result}")
                
                # Store analysis results
                analysis_results = analysis_result.get("result", {})
                triage_result["analysis_results"] = analysis_results
                
                # Add analysis as a comment to the story
                logger.info("Adding analysis results as a comment to the story")
                
                # Format the analysis as a markdown comment
                analysis_comment = _format_analysis_comment(analysis_results, story_id)
                
                # Add the comment to the story
                from tools.shortcut.shortcut_tools import add_comment
                comment_result = await add_comment(story_id, api_key, analysis_comment)
                logger.info(f"Comment added with ID: {comment_result.get('id')}")
                
                # Store comment results
                triage_result["comment_results"] = comment_result
                
            elif context.workflow_type.name == "ENHANCE":
                from shortcut_agents.analysis.analysis_agent import create_analysis_agent
                from shortcut_agents.update.update_agent import create_update_agent
                
                # First run analysis
                logger.info("Creating analysis agent")
                analysis_agent = create_analysis_agent()
                
                # Run analysis on the story data
                logger.info("Running analysis agent")
                analysis_result = await analysis_agent.run(context.story_data, context)
                logger.info(f"Analysis completed with result: {analysis_result}")
                
                # Store analysis results
                analysis_results = analysis_result.get("result", {})
                triage_result["analysis_results"] = analysis_results
                
                # Add analysis as a comment to the story
                logger.info("Adding analysis results as a comment to the story")
                
                # Format the analysis as a markdown comment
                analysis_comment = _format_analysis_comment(analysis_results, story_id)
                
                # Add the comment to the story
                from tools.shortcut.shortcut_tools import add_comment
                comment_result = await add_comment(story_id, api_key, analysis_comment)
                logger.info(f"Comment added with ID: {comment_result.get('id')}")
                
                # Store comment results
                triage_result["comment_results"] = comment_result
                
                # Then run update with the analysis results
                logger.info("Creating update agent")
                update_agent = create_update_agent()
                
                # Prepare input for update agent
                update_input = {
                    "story_id": context.story_id,
                    "workspace_id": context.workspace_id,
                    "update_type": "enhancement",
                    "analysis_result": analysis_results
                }
                
                # Run update agent
                logger.info("Running update agent")
                update_result = await update_agent.run(update_input, context)
                logger.info(f"Update completed with result: {update_result}")
                
                # Store update results
                triage_result["update_results"] = update_result.get("result", {})
            
        return triage_result, context
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}")
        raise

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test agents with real APIs")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--workflow", choices=["enhance", "analyse"], default="analyse",
                      help="Workflow type (enhance or analyse)")
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Starting direct test with:")
    logger.info(f"  Workspace: {args.workspace}")
    logger.info(f"  Story: {args.story}")
    logger.info(f"  Workflow: {args.workflow}")
    logger.info(f"  Using real OpenAI and Shortcut APIs")
    
    try:
        result, context = await run_direct_test(args.workspace, args.story, args.workflow)
        
        print("\n" + "=" * 80)
        print(f"DIRECT TEST RESULT: {'✅ SUCCESS' if result.get('status') == 'success' else '❌ FAILED'}")
        print("=" * 80)
        print(f"Workspace ID: {args.workspace}")
        print(f"Story ID:     {args.story}")
        print(f"Workflow:     {args.workflow}")
        
        # Display story details
        if context and context.story_data:
            story = context.story_data
            print("\nSTORY DETAILS:")
            print(f"Name:        {story.get('name', 'Unknown')}")
            
            # Display labels
            labels = story.get('labels', [])
            if labels:
                label_names = [label.get('name', '') for label in labels]
                print(f"Labels:      {', '.join(label_names)}")
            else:
                print("Labels:      None")
                
            # Display type and status if available
            if 'story_type' in story:
                print(f"Type:        {story.get('story_type', 'Unknown')}")
            if 'workflow_state_name' in story:
                print(f"Status:      {story.get('workflow_state_name', 'Unknown')}")
        
        # Display result details
        print("\nRESULT:")
        if result.get('status') == 'success':
            agent_result = result.get('result', {})
            
            # Display workflow determination
            workflow = agent_result.get('workflow')
            processed = agent_result.get('processed', False)
            reason = agent_result.get('reason', '')
            
            print(f"Processed:   {processed}")
            print(f"Workflow:    {workflow if workflow else 'None'}")
            if reason:
                print(f"Reason:      {reason}")
            
            # Display analysis results if present
            if 'analysis_results' in result:
                analysis = result['analysis_results']
                overall_score = analysis.get('overall_score', 'N/A')
                print(f"\nAnalysis Score: {overall_score}/10")
                
                # Print summary if available
                summary = analysis.get('summary')
                if summary:
                    print(f"\nSummary: {summary}")
                
                # Print priority areas
                priority_areas = analysis.get('priority_areas', [])
                if priority_areas:
                    print("\nPriority Areas:")
                    for area in priority_areas:
                        print(f"  - {area}")
            
            # Display comment results if present
            if 'comment_results' in result:
                comment = result['comment_results']
                print(f"\nComment Added: Yes (ID: {comment.get('id')})")
                print(f"View comment at: https://app.shortcut.com/{args.workspace}/story/{args.story}")
                    
            # Display update results if present
            if 'update_results' in result:
                update = result['update_results']
                print(f"\nUpdate Success: {update.get('success', False)}")
                if update.get('fields_updated'):
                    print(f"Fields Updated: {', '.join(update.get('fields_updated', []))}")
                if update.get('tags_added'):
                    print(f"Tags Added:     {', '.join(update.get('tags_added', []))}")
                if update.get('tags_removed'):
                    print(f"Tags Removed:   {', '.join(update.get('tags_removed', []))}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("=" * 80)
        
        return 0 if result.get('status') == 'success' else 1
    except Exception as e:
        logger.exception(f"Error in direct test: {str(e)}")
        
        print("\n" + "=" * 80)
        print(f"DIRECT TEST RESULT: ❌ FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print("=" * 80)
        
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)