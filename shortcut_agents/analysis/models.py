"""
Pydantic models for Analysis Agent structured outputs.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ComponentScore(BaseModel):
    """Component-specific score and recommendations."""
    score: int = Field(..., ge=1, le=10, description="Component score from 1-10")
    strengths: List[str] = Field(..., description="List of component strengths")
    weaknesses: List[str] = Field(..., description="List of component weaknesses")
    recommendations: List[str] = Field(..., description="List of specific recommendations for improvement")


class AnalysisResult(BaseModel):
    """Structured result of a story analysis."""
    overall_score: int = Field(..., ge=1, le=10, description="Overall story quality score from 1-10")
    title_analysis: ComponentScore = Field(..., description="Title analysis results")
    description_analysis: ComponentScore = Field(..., description="Description analysis results")
    acceptance_criteria_analysis: Optional[ComponentScore] = Field(None, description="Acceptance criteria analysis results (if present)")
    priority_areas: List[str] = Field(..., description="Prioritized list of areas to improve")
    summary: str = Field(..., description="Summary of the analysis findings")
    
    @validator('overall_score')
    def check_score_range(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Score must be between 1 and 10')
        return v


class AnalysisMetadata(BaseModel):
    """Metadata for an analysis."""
    workspace_id: str = Field(..., description="Shortcut workspace ID")
    story_id: str = Field(..., description="Shortcut story ID")
    timestamp: str = Field(..., description="ISO timestamp of the analysis")
    model_used: str = Field(..., description="Model used for analysis")
    version: str = Field("1.0", description="Version of the analysis agent")


class StoryAnalysisOutput(BaseModel):
    """Complete analysis output with results and metadata."""
    result: AnalysisResult = Field(..., description="Analysis results")
    metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    raw_story: Dict[str, Any] = Field(..., description="Original story data")