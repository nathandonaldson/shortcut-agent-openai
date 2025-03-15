"""
Tools for the Update Agent.
"""

import logging
from typing import List, Dict, Any, Optional
import json

from tools.shortcut.shortcut_tools import update_story, add_comment, get_story_details

# Set up logging
logger = logging.getLogger("update_agent.tools")


async def update_story_content(
    story_id: str,
    api_key: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    acceptance_criteria: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the content of a Shortcut story.
    
    Args:
        story_id: ID of the story to update
        api_key: Shortcut API key
        title: New title for the story (optional)
        description: New description for the story (optional)
        acceptance_criteria: New acceptance criteria for the story (optional)
        
    Returns:
        Updated story data
    """
    update_data = {}
    fields_updated = []
    
    # Only include fields that are provided
    if title is not None:
        update_data["name"] = title
        fields_updated.append("title")
        
    if description is not None:
        update_data["description"] = description
        fields_updated.append("description")
        
    if acceptance_criteria is not None:
        # In Shortcut, acceptance criteria might be part of description or custom fields
        # For simplicity, we're assuming it's a custom field or section
        update_data["custom_field_acceptance_criteria"] = acceptance_criteria
        fields_updated.append("acceptance_criteria")
    
    if not update_data:
        logger.warning(f"No content updates provided for story {story_id}")
        return {"message": "No updates provided", "fields_updated": []}
    
    try:
        # Update the story
        updated_story = await update_story(story_id, api_key, update_data)
        
        logger.info(f"Updated story {story_id} with fields: {', '.join(fields_updated)}")
        
        return {
            "story": updated_story,
            "fields_updated": fields_updated,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error updating story content: {str(e)}")
        return {
            "error": str(e),
            "fields_updated": [],
            "success": False
        }


async def update_story_labels(
    story_id: str,
    api_key: str,
    labels_to_add: List[str],
    labels_to_remove: List[str]
) -> Dict[str, Any]:
    """
    Update the labels on a Shortcut story.
    
    Args:
        story_id: ID of the story to update
        api_key: Shortcut API key
        labels_to_add: List of label names to add
        labels_to_remove: List of label names to remove
        
    Returns:
        Updated story data with label changes
    """
    # For better UX, use the term "tag" in logs instead of "label"
    logger.info(f"Updating tags for story {story_id}: adding {labels_to_add}, removing {labels_to_remove}")
    
    try:
        # First, get the current story to get existing labels
        story_data = await get_story_details(story_id, api_key)
        current_labels = story_data.get("labels", [])
        current_label_names = [label["name"] for label in current_labels]
        
        # Add new labels that aren't already present
        new_labels = current_labels.copy()
        for label_to_add in labels_to_add:
            if label_to_add not in current_label_names:
                new_labels.append({"name": label_to_add})
        
        # Remove labels that should be removed
        final_labels = [label for label in new_labels 
                       if label["name"] not in labels_to_remove]
        
        # Prepare the update data
        update_data = {
            "labels": final_labels
        }
        
        # Log the update data for debugging
        logger.info(f"Label update data: {json.dumps(update_data)}")
        
        # Update the story
        updated_story = await update_story(story_id, api_key, update_data)
        
        return {
            "story": updated_story,
            "added_labels": labels_to_add,
            "removed_labels": labels_to_remove,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error updating story labels: {str(e)}")
        return {
            "error": str(e),
            "added_labels": [],
            "removed_labels": [],
            "success": False
        }


async def add_update_comment(
    story_id: str,
    api_key: str,
    update_type: str,
    comment_text: str
) -> Dict[str, Any]:
    """
    Add a comment to a Shortcut story with update information.
    
    Args:
        story_id: ID of the story to comment on
        api_key: Shortcut API key
        update_type: Type of update ("analysis" or "enhancement")
        comment_text: Text of the comment to add
        
    Returns:
        Comment result
    """
    try:
        # Format the comment based on update type
        if update_type == "analysis":
            formatted_comment = f"📊 **Analysis Results**\n\n{comment_text}"
        else:  # enhancement
            formatted_comment = f"✨ **Enhancement Completed**\n\n{comment_text}"
        
        # Add the comment
        comment_result = await add_comment(story_id, api_key, formatted_comment)
        
        logger.info(f"Added {update_type} comment to story {story_id}")
        
        return {
            "comment": comment_result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error adding comment to story: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }


async def format_analysis_comment(analysis_result: Dict[str, Any]) -> str:
    """
    Format analysis results into a structured comment.
    
    Args:
        analysis_result: Analysis results from the Analysis Agent
        
    Returns:
        Formatted comment text
    """
    # Extract scores and recommendations
    overall_score = analysis_result.get("overall_score", "N/A")
    title_score = analysis_result.get("title_score", "N/A")
    description_score = analysis_result.get("description_score", "N/A")
    acceptance_criteria_score = analysis_result.get("acceptance_criteria_score", "N/A")
    recommendations = analysis_result.get("recommendations", [])
    priority_areas = analysis_result.get("priority_areas", [])
    
    # Format the comment
    comment = f"""## Story Analysis Results

### Quality Scores
- **Overall**: {overall_score}/10
- **Title**: {title_score}/10
- **Description**: {description_score}/10
"""
    
    if acceptance_criteria_score != "N/A":
        comment += f"- **Acceptance Criteria**: {acceptance_criteria_score}/10\n"
    
    comment += "\n### Recommendations\n"
    for rec in recommendations:
        comment += f"- {rec}\n"
    
    if priority_areas:
        comment += "\n### Priority Improvement Areas\n"
        for area in priority_areas:
            comment += f"- {area}\n"
    
    comment += "\n_Analysis performed by the Shortcut Enhancement System_"
    
    return comment


async def format_enhancement_comment(enhancement_result: Dict[str, Any]) -> str:
    """
    Format enhancement results into a structured comment.
    
    Args:
        enhancement_result: Enhancement results from the Enhancement Agent
        
    Returns:
        Formatted comment text
    """
    # Extract changes made
    changes_made = enhancement_result.get("changes_made", [])
    
    # Format the comment
    comment = """## Enhancement Completed

This story has been enhanced to improve clarity, structure, and completeness.

### Changes Made
"""
    
    for change in changes_made:
        comment += f"- {change}\n"
    
    comment += "\n_Enhanced by the Shortcut Enhancement System_"
    
    return comment