"""
Data models for the Update Agent.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Union, Any


# Import the Analysis model from the analysis module instead of duplicating it
from agents.analysis.models import AnalysisResult


class EnhancementResult(BaseModel):
    """Enhancement results from the Enhancement Agent."""
    
    enhanced_title: Optional[str] = Field(None, description="Enhanced story title")
    enhanced_description: Optional[str] = Field(None, description="Enhanced story description")
    enhanced_acceptance_criteria: Optional[str] = Field(None, description="Enhanced acceptance criteria")
    changes_made: List[str] = Field(..., description="List of changes made during enhancement")


class UpdateInput(BaseModel):
    """Input for the Update Agent."""
    
    story_id: str = Field(..., description="ID of the story to update")
    workspace_id: str = Field(..., description="ID of the workspace containing the story")
    update_type: Literal["analysis", "enhancement"] = Field(..., description="Type of update to perform")
    analysis_result: Optional[AnalysisResult] = Field(None, description="Analysis results if update_type is 'analysis'")
    enhancement_result: Optional[EnhancementResult] = Field(None, description="Enhancement results if update_type is 'enhancement'")


class UpdateResult(BaseModel):
    """Output from the Update Agent."""
    
    success: bool = Field(..., description="Whether the update was successful")
    story_id: str = Field(..., description="ID of the updated story")
    workspace_id: str = Field(..., description="ID of the workspace containing the story")
    update_type: Literal["analysis", "enhancement"] = Field(..., description="Type of update performed")
    fields_updated: List[str] = Field(..., description="List of fields that were updated")
    tags_added: List[str] = Field(..., description="Tags added to the story")
    tags_removed: List[str] = Field(..., description="Tags removed from the story")
    comment_added: bool = Field(..., description="Whether a comment was added")
    error_message: Optional[str] = Field(None, description="Error message if the update failed")