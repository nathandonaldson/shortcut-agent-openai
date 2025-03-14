"""
Command-line interface for testing the Update Agent.
"""

import os
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

from shortcut_agents.update.update_agent import process_update
from context.workspace.workspace_context import WorkspaceContext
from tools.shortcut.shortcut_tools import get_story


async def load_test_data(file_path: str) -> Dict[str, Any]:
    """Load test data from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


async def generate_mock_data(update_type: str) -> Dict[str, Any]:
    """Generate mock data for testing."""
    if update_type == "analysis":
        return {
            "overall_score": 7,
            "title_score": 8,
            "description_score": 6,
            "acceptance_criteria_score": 7,
            "recommendations": [
                "Add more details to the description",
                "Include specific acceptance criteria",
                "Use clearer language in the title"
            ],
            "priority_areas": ["description", "acceptance_criteria"]
        }
    else:  # enhancement
        return {
            "enhanced_title": "Enhanced Story Title with Better Clarity",
            "enhanced_description": (
                "Enhanced description with improved structure and details.\n\n"
                "## Background\n"
                "This section provides essential context for the story.\n\n"
                "## Requirements\n"
                "This section outlines the specific requirements for implementation."
            ),
            "enhanced_acceptance_criteria": (
                "## Acceptance Criteria\n\n"
                "- [ ] Criterion 1: The system should...\n"
                "- [ ] Criterion 2: Users should be able to...\n"
                "- [ ] Criterion 3: When an error occurs, the system should..."
            ),
            "changes_made": [
                "Improved title clarity",
                "Added structured sections to description",
                "Created formatted acceptance criteria",
                "Enhanced overall readability"
            ]
        }


async def test_update_agent(
    workspace_id: str,
    story_id: str,
    update_type: str,
    api_key: Optional[str] = None,
    test_data_file: Optional[str] = None
):
    """
    Test the Update Agent with a specific story.
    
    Args:
        workspace_id: Workspace ID
        story_id: Story ID
        update_type: Type of update ("analysis" or "enhancement")
        api_key: Shortcut API key (optional)
        test_data_file: Path to test data file (optional)
    """
    # Resolve API key
    if not api_key:
        # Try to get from environment variables
        api_key = os.environ.get(f"SHORTCUT_API_KEY_{workspace_id.upper()}")
        if not api_key:
            raise ValueError(f"No API key provided for workspace {workspace_id}")
    
    # Create workspace context
    workspace_context = WorkspaceContext(
        workspace_id=workspace_id,
        story_id=story_id,
        api_key=api_key,
        request_id=f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    
    # Get story data to verify it exists
    print(f"Verifying story {story_id} in workspace {workspace_id}...")
    story = await get_story(story_id, api_key)
    if not story:
        print(f"Error: Story {story_id} not found in workspace {workspace_id}")
        return
    
    print(f"Found story: '{story.get('name', 'Untitled')}'")
    
    # Load update data
    if test_data_file:
        print(f"Loading test data from {test_data_file}...")
        update_data = await load_test_data(test_data_file)
    else:
        print(f"Generating mock {update_type} data...")
        update_data = await generate_mock_data(update_type)
    
    # Process the update
    print(f"Processing {update_type} update...")
    try:
        result = await process_update(
            workspace_context=workspace_context,
            update_type=update_type,
            update_data=update_data
        )
        
        # Print the results
        print("\nUpdate Results:")
        print(f"Success: {'✅' if result.get('success') else '❌'}")
        print(f"Story ID: {result.get('story_id')}")
        print(f"Update Type: {result.get('update_type')}")
        
        if result.get('fields_updated'):
            print(f"Fields Updated: {', '.join(result.get('fields_updated'))}")
        else:
            print("Fields Updated: None")
        
        print(f"Tags Added: {', '.join(result.get('tags_added'))}")
        print(f"Tags Removed: {', '.join(result.get('tags_removed'))}")
        print(f"Comment Added: {'Yes' if result.get('comment_added') else 'No'}")
        
        if not result.get('success'):
            print(f"Error: {result.get('error_message')}")
        
        return result
    
    except Exception as e:
        print(f"Error running update: {str(e)}")
        raise


def main():
    """Command-line interface entry point."""
    parser = argparse.ArgumentParser(description="Test the Update Agent")
    parser.add_argument("--workspace", required=True, help="Workspace ID")
    parser.add_argument("--story", required=True, help="Story ID")
    parser.add_argument("--type", choices=["analysis", "enhancement"], required=True, 
                        help="Type of update to perform")
    parser.add_argument("--api-key", help="Shortcut API key (if not provided, will look for environment variable)")
    parser.add_argument("--data-file", help="Path to JSON file with test data")
    
    args = parser.parse_args()
    
    asyncio.run(test_update_agent(
        workspace_id=args.workspace,
        story_id=args.story,
        update_type=args.type,
        api_key=args.api_key,
        test_data_file=args.data_file
    ))


if __name__ == "__main__":
    main()