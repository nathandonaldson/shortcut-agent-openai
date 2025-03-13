"""
Workspace context for managing Shortcut workspace state.
"""

from enum import Enum
from typing import Dict, Any, Optional, List

class WorkflowType(Enum):
    """Enum for different workflow types in the system"""
    ENHANCE = "enhance"  # Full enhancement workflow
    ANALYSE = "analyse"  # Analysis-only workflow

class WorkspaceContext:
    """Context object for Shortcut workspace interactions"""
    
    def __init__(self, workspace_id: str, api_key: str, story_id: Optional[str] = None):
        """
        Initialize the workspace context with basic information.
        
        Args:
            workspace_id: The Shortcut workspace ID
            api_key: The API key for the workspace
            story_id: Optional story ID when working with a specific story
        """
        self.workspace_id = workspace_id
        self.api_key = api_key
        self.story_id = story_id
        
        # Story data will be populated when needed
        self.story_data: Optional[Dict[str, Any]] = None
        
        # Workflow state
        self.workflow_type: Optional[WorkflowType] = None
        
        # Analysis and enhancement results
        self.analysis_results: Optional[Dict[str, Any]] = None
        self.enhancement_results: Optional[Dict[str, Any]] = None
        
    def set_story_data(self, story_data: Dict[str, Any]) -> None:
        """Set the story data for the current context"""
        self.story_data = story_data
        
        # Extract the story ID if not already set
        if not self.story_id and 'id' in story_data:
            self.story_id = str(story_data['id'])
    
    def set_workflow_type(self, workflow_type: WorkflowType) -> None:
        """Set the workflow type based on the story tags"""
        self.workflow_type = workflow_type
    
    def determine_workflow_type(self) -> Optional[WorkflowType]:
        """
        Determine the workflow type based on the story labels.
        Returns None if no relevant labels are found.
        """
        if not self.story_data or 'labels' not in self.story_data:
            return None
        
        # Extract label names
        labels = [label.get('name', '').lower() for label in self.story_data.get('labels', [])]
        
        # Check for workflow-specific labels
        if 'enhance' in labels:
            return WorkflowType.ENHANCE
        elif 'analyse' in labels or 'analyze' in labels:
            return WorkflowType.ANALYSE
            
        return None
    
    def set_analysis_results(self, results: Dict[str, Any]) -> None:
        """Set the analysis results for the current story"""
        self.analysis_results = results
    
    def set_enhancement_results(self, results: Dict[str, Any]) -> None:
        """Set the enhancement results for the current story"""
        self.enhancement_results = results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary for storage"""
        return {
            'workspace_id': self.workspace_id,
            'story_id': self.story_id,
            'workflow_type': self.workflow_type.value if self.workflow_type else None,
            'analysis_results': self.analysis_results,
            'enhancement_results': self.enhancement_results,
            # Don't include the API key for security
            # Don't include the full story data to save space
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], api_key: str, story_data: Optional[Dict[str, Any]] = None) -> 'WorkspaceContext':
        """Create a context instance from a dictionary"""
        context = cls(
            workspace_id=data['workspace_id'],
            api_key=api_key,
            story_id=data.get('story_id')
        )
        
        # Set the workflow type if present
        if data.get('workflow_type'):
            context.workflow_type = WorkflowType(data['workflow_type'])
        
        # Set results if present
        if data.get('analysis_results'):
            context.analysis_results = data['analysis_results']
        
        if data.get('enhancement_results'):
            context.enhancement_results = data['enhancement_results']
        
        # Set story data if provided
        if story_data:
            context.set_story_data(story_data)
            
        return context