"""
Shortcut API tools for the Shortcut Enhancement System.
"""

from tools.shortcut.shortcut_tools import (
    get_story_details,
    update_story,
    add_comment,
    queue_enhancement_task,
    queue_analysis_task
)

__all__ = [
    "get_story_details",
    "update_story",
    "add_comment",
    "queue_enhancement_task",
    "queue_analysis_task"
]