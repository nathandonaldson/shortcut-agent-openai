"""
Unit tests for the refactored triage agent.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from shortcut_agents.triage.triage_agent_refactored import create_triage_agent, process_webhook

@pytest.fixture
def context():
    """Create a test workspace context."""
    return WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345"
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
        "id": 12345,
        "references": []
    }

@pytest.fixture
def mock_story_data():
    """Create mock story data."""
    return {
        "id": 12345,
        "name": "Test Story",
        "description": "This is a test story",
        "labels": [{"name": "enhance"}],
        "workflow_state_id": 500001
    }

@pytest.mark.asyncio
async def test_triage_agent_creation():
    """Test that the triage agent can be created."""
    agent = create_triage_agent()
    assert agent is not None
    assert agent.name == "Triage Agent"

@pytest.mark.asyncio
async def test_process_webhook_enhance(context, webhook_data, mock_story_data):
    """Test processing a webhook with enhance tag."""
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story:
        # Set up mock
        mock_get_story.return_value = mock_story_data
        
        # Set up agent mock
        agent_mock = AsyncMock()
        agent_mock.run.return_value = {
            "workflow": "enhance",
            "tags": ["enhance"],
            "story_id": "12345",
            "workspace_id": "test-workspace"
        }
        
        with patch("shortcut_agents.triage.triage_agent_refactored.create_triage_agent") as mock_create_agent:
            mock_create_agent.return_value = agent_mock
            
            # Process the webhook
            result = await process_webhook(webhook_data, context)
            
            # Verify the result
            assert result["workflow"] == "enhance"
            assert result["story_id"] == "12345"
            assert result["workspace_id"] == "test-workspace"
            
            # Verify that agent.run was called
            agent_mock.run.assert_called_once()

@pytest.mark.asyncio
async def test_process_webhook_analyse(context, mock_story_data):
    """Test processing a webhook with analyse tag."""
    
    # Create webhook data with analyse tag
    webhook_data = {
        "action": "update",
        "changes": {
            "labels": {
                "adds": [{"name": "analyse"}]
            }
        },
        "id": 12345,
        "references": []
    }
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story:
        # Set up mock
        mock_get_story.return_value = mock_story_data
        
        # Set up agent mock
        agent_mock = AsyncMock()
        agent_mock.run.return_value = {
            "workflow": "analyse",
            "tags": ["analyse"],
            "story_id": "12345",
            "workspace_id": "test-workspace"
        }
        
        with patch("shortcut_agents.triage.triage_agent_refactored.create_triage_agent") as mock_create_agent:
            mock_create_agent.return_value = agent_mock
            
            # Process the webhook
            result = await process_webhook(webhook_data, context)
            
            # Verify the result
            assert result["workflow"] == "analyse"
            assert result["story_id"] == "12345"
            assert result["workspace_id"] == "test-workspace"
            
            # Verify that agent.run was called
            agent_mock.run.assert_called_once()

@pytest.mark.asyncio
async def test_process_webhook_no_relevant_tags(context, mock_story_data):
    """Test processing a webhook without relevant tags."""
    
    # Create webhook data with no relevant tags
    webhook_data = {
        "action": "update",
        "changes": {
            "labels": {
                "adds": [{"name": "bug"}]
            }
        },
        "id": 12345,
        "references": []
    }
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story:
        # Set up mock
        mock_get_story.return_value = mock_story_data
        
        # Set up agent mock
        agent_mock = AsyncMock()
        agent_mock.run.return_value = {
            "workflow": "none",
            "reason": "No relevant tags found",
            "story_id": "12345",
            "workspace_id": "test-workspace"
        }
        
        with patch("shortcut_agents.triage.triage_agent_refactored.create_triage_agent") as mock_create_agent:
            mock_create_agent.return_value = agent_mock
            
            # Process the webhook
            result = await process_webhook(webhook_data, context)
            
            # Verify the result
            assert result["workflow"] == "none"
            assert "reason" in result
            assert result["story_id"] == "12345"
            assert result["workspace_id"] == "test-workspace"
            
            # Verify that agent.run was called
            agent_mock.run.assert_called_once()

@pytest.mark.asyncio
async def test_simplified_triage(context, webhook_data, mock_story_data):
    """Test the simplified triage implementation."""
    
    with patch("shortcut_agents.triage.triage_agent_refactored.get_story_details") as mock_get_story, \
         patch("os.environ", {}):  # Simulate no OpenAI API key
        
        # Set up mock
        mock_get_story.return_value = mock_story_data
        
        # Process the webhook
        result = await process_webhook(webhook_data, context)
        
        # Verify the result contains expected keys
        assert "workflow" in result
        assert "story_id" in result
        assert "workspace_id" in result
        
        # Verify the simplified implementation was used
        assert result["simplified"] == True