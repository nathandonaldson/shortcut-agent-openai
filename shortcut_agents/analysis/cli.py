#!/usr/bin/env python3
"""
Command-line interface for testing the Analysis Agent.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext
from tools.shortcut.shortcut_tools import get_story_details
from shortcut_agents.analysis.analysis_agent_refactored import process_analysis

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("analysis_cli")


def load_api_key(workspace_id: str) -> Optional[str]:
    """
    Load the API key for a workspace from environment variables.
    
    Args:
        workspace_id: The workspace ID
        
    Returns:
        The API key or None if not found
    """
    # Try workspace-specific key first
    api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id.upper()}")
    
    # Fall back to generic key
    if not api_key:
        api_key = os.environ.get("SHORTCUT_API_KEY")
    
    return api_key


def load_test_story(file_path: str) -> Dict[str, Any]:
    """
    Load a test story from a JSON file.
    
    Args:
        file_path: Path to the test story JSON file
        
    Returns:
        Dictionary with story data
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading test story: {str(e)}")
        sys.exit(1)


async def analyze_story_by_id(workspace_id: str, story_id: str, api_key: str) -> Dict[str, Any]:
    """
    Analyze a story by its ID.
    
    Args:
        workspace_id: The workspace ID
        story_id: The story ID
        api_key: The API key
        
    Returns:
        Analysis results
    """
    logger.info(f"Analyzing story {story_id} in workspace {workspace_id}")
    
    # Create workspace context
    context = WorkspaceContext(
        workspace_id=workspace_id,
        api_key=api_key,
        story_id=story_id
    )
    
    # Get story details
    story_data = await get_story_details(story_id, api_key)
    context.set_story_data(story_data)
    
    # Process the analysis
    result = await process_analysis(story_data, context)
    return result


async def analyze_test_story(workspace_id: str, story_data: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Analyze a test story.
    
    Args:
        workspace_id: The workspace ID
        story_data: The test story data
        api_key: The API key
        
    Returns:
        Analysis results
    """
    logger.info(f"Analyzing test story with ID {story_data.get('id', 'unknown')}")
    
    # Create workspace context
    context = WorkspaceContext(
        workspace_id=workspace_id,
        api_key=api_key,
        story_id=str(story_data.get('id', ''))
    )
    context.set_story_data(story_data)
    
    # Process the analysis
    result = await process_analysis(story_data, context)
    return result


def print_analysis_results(results: Dict[str, Any]) -> None:
    """
    Print analysis results in a readable format.
    
    Args:
        results: Analysis results
    """
    print("\n=== ANALYSIS RESULTS ===\n")
    
    if results.get("status") != "success":
        print(f"❌ Error: {results.get('message', 'Unknown error')}")
        return
    
    analysis = results.get("analysis", {}).get("result", {})
    
    # Print overall score and summary
    overall_score = analysis.get("overall_score", 0)
    print(f"Overall Score: {overall_score}/10")
    print(f"Summary: {analysis.get('summary', 'No summary provided')}")
    print("\n--- Component Analysis ---\n")
    
    # Print title analysis
    title_analysis = analysis.get("title_analysis", {})
    print(f"Title: {title_analysis.get('score', 0)}/10")
    print("  Strengths:")
    for strength in title_analysis.get("strengths", []):
        print(f"  ✓ {strength}")
    print("  Weaknesses:")
    for weakness in title_analysis.get("weaknesses", []):
        print(f"  ✗ {weakness}")
    print("  Recommendations:")
    for rec in title_analysis.get("recommendations", []):
        print(f"  → {rec}")
    print("")
    
    # Print description analysis
    desc_analysis = analysis.get("description_analysis", {})
    print(f"Description: {desc_analysis.get('score', 0)}/10")
    print("  Strengths:")
    for strength in desc_analysis.get("strengths", []):
        print(f"  ✓ {strength}")
    print("  Weaknesses:")
    for weakness in desc_analysis.get("weaknesses", []):
        print(f"  ✗ {weakness}")
    print("  Recommendations:")
    for rec in desc_analysis.get("recommendations", []):
        print(f"  → {rec}")
    print("")
    
    # Print acceptance criteria analysis if available
    ac_analysis = analysis.get("acceptance_criteria_analysis")
    if ac_analysis:
        print(f"Acceptance Criteria: {ac_analysis.get('score', 0)}/10")
        print("  Strengths:")
        for strength in ac_analysis.get("strengths", []):
            print(f"  ✓ {strength}")
        print("  Weaknesses:")
        for weakness in ac_analysis.get("weaknesses", []):
            print(f"  ✗ {weakness}")
        print("  Recommendations:")
        for rec in ac_analysis.get("recommendations", []):
            print(f"  → {rec}")
        print("")
    
    # Print priority areas
    print("Priority Areas for Improvement:")
    for i, area in enumerate(analysis.get("priority_areas", []), 1):
        print(f"  {i}. {area}")
    
    print("\n--- Metadata ---\n")
    metadata = results.get("analysis", {}).get("metadata", {})
    print(f"Story ID: {metadata.get('story_id', 'Unknown')}")
    print(f"Workspace ID: {metadata.get('workspace_id', 'Unknown')}")
    print(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
    print(f"Model Used: {metadata.get('model_used', 'Unknown')}")
    print(f"Version: {metadata.get('version', 'Unknown')}")


async def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Analysis Agent CLI for Shortcut stories")
    
    # Common arguments
    parser.add_argument("--workspace", "-w", required=True, help="Shortcut workspace ID")
    parser.add_argument("--output", "-o", help="Output file for analysis results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # 'analyze' command for analyzing a story by ID
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a story by ID")
    analyze_parser.add_argument("story_id", help="Shortcut story ID to analyze")
    
    # 'test' command for using a test story file
    test_parser = subparsers.add_parser("test", help="Analyze a test story from a file")
    test_parser.add_argument("file", help="Path to test story JSON file")
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get the API key
    api_key = load_api_key(args.workspace)
    if not api_key:
        logger.error(f"No API key found for workspace {args.workspace}")
        sys.exit(1)
    
    # Execute the command
    if args.command == "analyze":
        results = await analyze_story_by_id(args.workspace, args.story_id, api_key)
    elif args.command == "test":
        story_data = load_test_story(args.file)
        results = await analyze_test_story(args.workspace, story_data, api_key)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Print results
    print_analysis_results(results)
    
    # Save results to file if specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())