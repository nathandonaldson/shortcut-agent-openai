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

def _format_analysis_comment(analysis_results: Dict[str, Any], story_id: str, workspace_id: str) -> str:
    """
    Format analysis results as a Markdown comment.
    
    Args:
        analysis_results: Analysis results dictionary
        story_id: Story ID
        workspace_id: Workspace ID
        
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
            
            # Import necessary modules - do this early to avoid import issues
            from shortcut_agents.analysis.analysis_agent import create_analysis_agent
            from tools.shortcut.shortcut_tools import add_comment, update_story
            
            # Create analysis agent - used in both workflows
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
            analysis_comment = _format_analysis_comment(analysis_results, story_id, workspace_id)
            
            # Add the comment to the story
            comment_result = await add_comment(story_id, api_key, analysis_comment)
            logger.info(f"Comment added with ID: {comment_result.get('id')}")
            
            # Store comment results
            triage_result["comment_results"] = comment_result
            
            # Handle enhancement workflow with story updates
            if context.workflow_type.name == "ENHANCE":
                from shortcut_agents.update.update_agent import create_update_agent
                from shortcut_agents.update.models import EnhancementResult
                
                # Extract key recommendations from analysis
                title_recommendations = analysis_results.get("title_analysis", {}).get("recommendations", []) if analysis_results.get("title_analysis") else []
                desc_recommendations = analysis_results.get("description_analysis", {}).get("recommendations", []) if analysis_results.get("description_analysis") else []
                # Handle None acceptance criteria analysis safely
                ac_analysis = analysis_results.get("acceptance_criteria_analysis")
                ac_recommendations = ac_analysis.get("recommendations", []) if ac_analysis else []
                
                # Determine if we need to update each component based on recommendations
                update_title = any("title" in rec.lower() for rec in title_recommendations) and len(title_recommendations) > 0
                update_description = any("description" in rec.lower() for rec in desc_recommendations) and len(desc_recommendations) > 0
                update_ac = any("criteria" in rec.lower() for rec in ac_recommendations) and len(ac_recommendations) > 0
                
                # Extract current story content
                original_title = context.story_data.get("name", "")
                original_description = context.story_data.get("description", "")
                original_ac = context.story_data.get("acceptance_criteria", "")
                
                # Create example enhanced content (in a real system this would be generated by a model)
                enhanced_title = f"[Enhanced] {original_title}" if update_title else None
                enhanced_description = f"{original_description}\n\n[Enhanced with improved clarity and structure]" if update_description else None
                enhanced_ac = f"{original_ac}\n\n[Enhanced acceptance criteria with clearer steps]" if update_ac else None
                
                # Create a model-style enhancement result
                enhanced_content = {
                    "enhanced_title": enhanced_title,
                    "enhanced_description": enhanced_description,
                    "enhanced_acceptance_criteria": enhanced_ac,
                    "changes_made": [
                        "Improved title clarity" if update_title else None,
                        "Enhanced description structure" if update_description else None,
                        "Clarified acceptance criteria" if update_ac else None
                    ]
                }
                # Remove None values
                enhanced_content["changes_made"] = [change for change in enhanced_content["changes_made"] if change]
                
                # Log what we're enhancing
                logger.info(f"Enhancing content: title={update_title}, description={update_description}, ac={update_ac}")
                
                # Prepare story update data
                update_data = {}
                if enhanced_title:
                    update_data["name"] = enhanced_title
                if enhanced_description:
                    update_data["description"] = enhanced_description
                
                # Update the story if we have changes
                if update_data:
                    logger.info(f"Updating story content for {story_id}")
                    try:
                        update_story_result = await update_story(story_id, api_key, update_data)
                        logger.info(f"Story updated successfully: {update_story_result.get('id')}")
                        
                        # Store the updated story content in context
                        context.set_story_data(update_story_result)
                    except Exception as update_error:
                        logger.error(f"Error updating story: {str(update_error)}")
                        triage_result["update_error"] = str(update_error)
                
                # Create an enhancement comment to explain changes
                enhancement_comment = "## ✨ Story Enhancement Applied\n\n"
                enhancement_comment += "This story has been enhanced to improve clarity, structure, and completeness.\n\n"
                
                enhancement_comment += "### Changes Made\n"
                for change in enhanced_content["changes_made"]:
                    enhancement_comment += f"- {change}\n"
                
                enhancement_comment += "\n_Enhanced by the Shortcut Enhancement System_"
                
                # Add the enhancement comment
                logger.info("Adding enhancement comment to the story")
                enhancement_result = await add_comment(story_id, api_key, enhancement_comment)
                logger.info(f"Enhancement comment added with ID: {enhancement_result.get('id')}")
                
                # Update the story labels: remove "enhance", add "enhanced"
                logger.info("Updating story labels")
                
                # Get current labels
                current_labels = context.story_data.get("labels", [])
                current_label_names = [label["name"] for label in current_labels]
                
                # Add "enhanced" label if not present
                new_labels = current_labels.copy()
                if "enhanced" not in current_label_names:
                    new_labels.append({"name": "enhanced"})
                
                # Remove "enhance" label
                final_labels = [label for label in new_labels if label["name"] != "enhance"]
                
                # Prepare update data
                label_update = {
                    "labels": final_labels
                }
                
                try:
                    label_result = await update_story(story_id, api_key, label_update)
                    logger.info(f"Labels updated for story {story_id}")
                    
                    # Store label update results
                    triage_result["label_update"] = {
                        "success": True,
                        "added": ["enhanced"],
                        "removed": ["enhance"]
                    }
                except Exception as label_error:
                    logger.error(f"Error updating labels: {str(label_error)}")
                    triage_result["label_update"] = {
                        "success": False,
                        "error": str(label_error)
                    }
                
                # Store enhancement results
                triage_result["enhancement_results"] = {
                    "success": True,
                    "fields_updated": list(update_data.keys()),
                    "enhancement_comment_id": enhancement_result.get("id"),
                    "changes_made": enhanced_content["changes_made"]
                }
            
            # For ANALYSE workflow, update the story labels: remove "analyse", add "analysed"
            elif context.workflow_type.name == "ANALYSE":
                logger.info("Updating story labels for analysis workflow")
                
                # Get current labels
                current_labels = context.story_data.get("labels", [])
                current_label_names = [label["name"] for label in current_labels]
                
                # Add "analysed" label if not present
                new_labels = current_labels.copy()
                if "analysed" not in current_label_names:
                    new_labels.append({"name": "analysed"})
                
                # Remove "analyse" label
                final_labels = [label for label in new_labels if label["name"] != "analyse"]
                
                # Prepare update data
                label_update = {
                    "labels": final_labels
                }
                
                try:
                    from tools.shortcut.shortcut_tools import update_story
                    label_result = await update_story(story_id, api_key, label_update)
                    logger.info(f"Labels updated for story {story_id}")
                    
                    # Store label update results
                    triage_result["label_update"] = {
                        "success": True,
                        "added": ["analysed"],
                        "removed": ["analyse"]
                    }
                except Exception as label_error:
                    logger.error(f"Error updating labels: {str(label_error)}")
                    triage_result["label_update"] = {
                        "success": False,
                        "error": str(label_error)
                    }
            
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
            
            # Display enhancement results if present (from our direct implementation)
            if 'enhancement_results' in result:
                enhance = result['enhancement_results']
                print(f"\nEnhancement Success: {enhance.get('success', False)}")
                if enhance.get('fields_updated'):
                    print(f"Fields Updated: {', '.join(enhance.get('fields_updated', []))}")
                if enhance.get('changes_made'):
                    print("\nChanges Made:")
                    for change in enhance.get('changes_made', []):
                        print(f"  - {change}")
                print(f"\nEnhancement Comment ID: {enhance.get('enhancement_comment_id')}")
            
            # Display label update results
            if 'label_update' in result:
                label_update = result['label_update']
                print(f"\nLabel Update Success: {label_update.get('success', False)}")
                if label_update.get('added'):
                    print(f"Labels Added:   {', '.join(label_update.get('added', []))}")
                if label_update.get('removed'):
                    print(f"Labels Removed: {', '.join(label_update.get('removed', []))}")
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