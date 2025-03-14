"""
Integration tests for the agent workflow.

These tests verify that the refactored agents properly integrate
and work together through the complete workflow.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from shortcut_agents.triage.triage_agent_refactored import process_webhook
from shortcut_agents.analysis.analysis_agent_refactored import process_analysis
from shortcut_agents.update.update_agent_refactored import process_update
from utils.tracing import create_trace_id, trace_context

# Test data
TEST_WORKSPACE_ID = "test-workspace"
TEST_API_KEY = "test-api-key"
TEST_STORY_ID = "12345"

@pytest.fixture
def context():
    """Create a test workspace context."""
    return WorkspaceContext(
        workspace_id=TEST_WORKSPACE_ID,
        api_key=TEST_API_KEY,
        story_id=TEST_STORY_ID
    )

@pytest.fixture
def webhook_data():
    """Create a test webhook payload."""
    return {
        "action": "update",
        "changes": {
            "labels": {
                "adds": [{"name": "enhance"}]
            }
        },
        "id": int(TEST_STORY_ID),
        "references": []
    }

@pytest.fixture
def mock_story_data():
    """Create mock story data."""
    return {
        "id": int(TEST_STORY_ID),
        "name": "Test Story",
        "description": "This is a test story that needs enhancement.",
        "labels": [{"name": "enhance"}],
        "workflow_state_id": 500001
    }

@pytest.fixture
def mock_analysis_results():
    """Create mock analysis results."""
    return {
        "quality_score": 65,
        "analysis": {
            "clarity": {
                "score": 60,
                "feedback": "The story lacks clear acceptance criteria."
            },
            "completeness": {
                "score": 70,
                "feedback": "The description is missing implementation details."
            }
        },
        "recommendations": [
            "Add specific acceptance criteria",
            "Include implementation approach"
        ]
    }

@pytest.fixture
def mock_update_data():
    """Create mock update data."""
    return {
        "description": "This is an enhanced test story with clear criteria.\n\n## Acceptance Criteria\n- Criteria 1\n- Criteria 2\n\n## Implementation Approach\nWe will implement this using...",
        "labels": [{"name": "enhanced"}]
    }

@pytest.mark.asyncio
async def test_full_enhance_workflow(context, webhook_data, mock_story_data, 
                                   mock_analysis_results, mock_update_data):
    """Test the full enhance workflow with all agent handoffs."""
    
    # Set up trace context for the test
    trace_id = create_trace_id()
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story, \
         patch("shortcut_agents.triage.triage_agent_refactored.TriageAgent.run") as mock_triage_run, \
         patch("shortcut_agents.analysis.analysis_agent_refactored.AnalysisAgent.run") as mock_analysis_run, \
         patch("shortcut_agents.update.update_agent_refactored.UpdateAgent.run") as mock_update_run, \
         patch("shortcut_agents.update.update_agent_refactored.update_story") as mock_update_story, \
         trace_context(trace_id=trace_id, request_id="test-request"):
        
        # Set up mocks
        mock_get_story.return_value = mock_story_data
        
        # Triage agent returns enhance workflow
        mock_triage_run.return_value = {
            "workflow": WorkflowType.ENHANCE,
            "tags": ["enhance"],
            "story_id": TEST_STORY_ID,
            "workspace_id": TEST_WORKSPACE_ID
        }
        
        # Analysis agent returns analysis results
        mock_analysis_run.return_value = mock_analysis_results
        
        # Update agent returns update results
        mock_update_run.return_value = {
            "success": True,
            "story_id": TEST_STORY_ID,
            "workspace_id": TEST_WORKSPACE_ID,
            "update_type": "enhance",
            "fields_updated": ["description", "labels"],
            "tags_added": ["enhanced"],
            "tags_removed": ["enhance"]
        }
        
        # Mock update_story to return successfully
        mock_update_story.return_value = {**mock_story_data, **mock_update_data}
        
        # Process the webhook to start the workflow
        result = await process_webhook(webhook_data, context)
        
        # Verify the result
        assert result["workflow"] == WorkflowType.ENHANCE
        assert result["story_id"] == TEST_STORY_ID
        assert result["workspace_id"] == TEST_WORKSPACE_ID
        
        # Verify that the triage agent was run
        mock_triage_run.assert_called_once()
        
        # Verify trace context was preserved in the context
        assert hasattr(context, '_trace_context')
        trace_context_dict = getattr(context, '_trace_context', {})
        assert 'trace_id' in trace_context_dict
        assert trace_context_dict['trace_id'] == trace_id

@pytest.mark.asyncio
async def test_analyse_workflow(context, mock_story_data, mock_analysis_results):
    """Test the analyse workflow."""
    
    # Create webhook data with analyse tag
    webhook_data = {
        "action": "update",
        "changes": {
            "labels": {
                "adds": [{"name": "analyse"}]
            }
        },
        "id": int(TEST_STORY_ID),
        "references": []
    }
    
    # Set up trace context for the test
    trace_id = create_trace_id()
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story, \
         patch("shortcut_agents.triage.triage_agent_refactored.TriageAgent.run") as mock_triage_run, \
         patch("shortcut_agents.analysis.analysis_agent_refactored.AnalysisAgent.run") as mock_analysis_run, \
         patch("shortcut_agents.update.update_agent_refactored.add_comment") as mock_add_comment, \
         trace_context(trace_id=trace_id, request_id="test-request"):
        
        # Set up mocks
        mock_get_story.return_value = mock_story_data
        
        # Triage agent returns analyse workflow
        mock_triage_run.return_value = {
            "workflow": WorkflowType.ANALYSE,
            "tags": ["analyse"],
            "story_id": TEST_STORY_ID,
            "workspace_id": TEST_WORKSPACE_ID
        }
        
        # Analysis agent returns analysis results
        mock_analysis_run.return_value = mock_analysis_results
        
        # Mock add_comment to return successfully
        mock_add_comment.return_value = {
            "id": 999,
            "text": "Analysis results...",
            "author_id": "system",
            "created_at": "2023-01-01T00:00:00Z"
        }
        
        # Process the webhook to start the workflow
        result = await process_webhook(webhook_data, context)
        
        # Verify the result
        assert result["workflow"] == WorkflowType.ANALYSE
        assert result["story_id"] == TEST_STORY_ID
        assert result["workspace_id"] == TEST_WORKSPACE_ID
        
        # Verify that the triage agent was run
        mock_triage_run.assert_called_once()
        
        # Verify trace context was preserved in the context
        assert hasattr(context, '_trace_context')
        trace_context_dict = getattr(context, '_trace_context', {})
        assert 'trace_id' in trace_context_dict
        assert trace_context_dict['trace_id'] == trace_id

@pytest.mark.asyncio
async def test_simplified_workflow_fallback(context, webhook_data, mock_story_data):
    """Test fallback to simplified workflow when OpenAI API key is not available."""
    
    # Remove OpenAI API key from environment
    with patch("os.environ", {}), \
         patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story:
         
        # Set up mocks
        mock_get_story.return_value = mock_story_data
        
        # Process the webhook
        result = await process_webhook(webhook_data, context)
        
        # Verify the result contains expected keys
        assert "workflow" in result
        assert "story_id" in result
        assert "workspace_id" in result
        
        # Verify the simplified implementation was used
        assert result["simplified"] == True