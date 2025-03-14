"""
Unit tests for the BaseAgent class.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional

from context.workspace.workspace_context import WorkspaceContext
from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks

class TestAgentHooks(BaseAgentHooks):
    """Test implementation of agent hooks for testing."""
    
    def __init__(self):
        super().__init__(agent_type="test", agent_name="Test Agent")
        self.processed_result = None
        self.pre_run_called = False
        self.post_run_called = False
        
        
    def pre_run(self, input_data, context):
        self.pre_run_called = True
        return input_data
        
    def post_run(self, result, context):
        self.post_run_called = True
        return result
        
    def process_result(self, result):
        self.processed_result = result
        return {"processed": True, **result}

class TestAgent(BaseAgent):
    """Test implementation of BaseAgent for testing."""
    
    def __init__(self, hooks=None, simplified=False):
        super().__init__(
            agent_type="test",
            agent_name="Test Agent",
            system_message="Test system message",
            output_class=dict  # Using dict as a simple output class
        )
        self.tools = []
        self.hooks = hooks or TestAgentHooks()
        self.simplified = simplified
        
    def run_simplified(self, input_data, context):
        return {"simplified": True, "input": input_data}

@pytest.fixture
def agent():
    """Create a test agent instance."""
    return TestAgent()

@pytest.fixture
def context():
    """Create a test workspace context."""
    return WorkspaceContext(
        workspace_id="test-workspace",
        api_key="test-api-key",
        story_id="12345"
    )

@pytest.mark.asyncio
async def test_run_standard_mode(agent, context):
    """Test the standard run mode of the BaseAgent."""
    
    with patch("openai.OpenAI") as mock_openai, \
         patch("shortcut_agents.base_agent.Runner") as mock_runner:
        
        # Set up mocks
        mock_run = AsyncMock()
        mock_run.return_value = {"result": "success"}
        mock_runner.run = mock_run
        
        # Run the agent
        result = await agent.run({"input": "test"}, context)
        
        # Verify the runner was called
        mock_run.assert_called_once()
        
        # Verify hooks were called
        assert agent.hooks.pre_run_called
        assert agent.hooks.post_run_called
        assert agent.hooks.processed_result == {"result": "success"}
        
        # Verify result processing
        assert result == {"processed": True, "result": "success"}

@pytest.mark.asyncio
async def test_run_simplified_mode(context):
    """Test the simplified run mode of the BaseAgent."""
    
    # Create agent with simplified mode
    agent = TestAgent(simplified=True)
    
    # Run the agent
    result = await agent.run({"input": "test"}, context)
    
    # Verify the simplified implementation was used
    assert result == {"processed": True, "simplified": True, "input": {"input": "test"}}
    
    # Verify hooks were called
    assert agent.hooks.pre_run_called
    assert agent.hooks.post_run_called

@pytest.mark.asyncio
async def test_run_with_openai_error(agent, context):
    """Test error handling when OpenAI client fails."""
    
    with patch("openai.OpenAI") as mock_openai, \
         patch("shortcut_agents.base_agent.Runner") as mock_runner:
        
        # Set up mocks to raise an exception
        mock_run = AsyncMock()
        mock_run.side_effect = Exception("OpenAI error")
        mock_runner.run = mock_run
        
        # Run the agent
        result = await agent.run({"input": "test"}, context)
        
        # Verify result contains error information
        assert result["success"] == False
        assert "error" in result
        assert "OpenAI error" in result["error"]

@pytest.mark.asyncio
async def test_handoff_to(agent, context):
    """Test the handoff_to method."""
    
    with patch("shortcut_agents.base_agent.prepare_handoff_context") as mock_prepare, \
         patch("shortcut_agents.base_agent.restore_handoff_context") as mock_restore:
        
        # Set up mocks
        mock_prepare.return_value = context
        mock_restore.return_value = None
        
        # Create a mock target agent
        mock_target_agent = AsyncMock()
        mock_target_agent.run.return_value = {"handoff_result": "success"}
        
        # Execute the handoff
        result = await agent.hooks.handoff_to(
            target_agent=mock_target_agent,
            input_data={"handoff_input": "test"},
            context=context
        )
        
        # Verify the handoff was executed correctly
        mock_prepare.assert_called_once_with(context)
        mock_target_agent.run.assert_called_once_with(
            {"handoff_input": "test"}, 
            context
        )
        mock_restore.assert_called_once_with(context)
        
        # Verify the result
        assert result == {"handoff_result": "success"}


@pytest.mark.asyncio
async def test_choose_model():
    """Test the model selection logic."""
    
    # Test with development config
    with patch("os.environ", {"OPENAI_API_KEY": "test"}), \
         patch("shortcut_agents.base_agent.get_config") as mock_get_config:
        
        mock_get_config.return_value = {
            "models": {
                "test": "gpt-3.5-turbo-dev"
            }
        }
        
        agent = TestAgent()
        model = agent._choose_model("test")
        assert model == "gpt-3.5-turbo-dev"
    
    # Test with production config
    with patch("os.environ", {"OPENAI_API_KEY": "test", "VERCEL_ENV": "production"}), \
         patch("shortcut_agents.base_agent.get_config") as mock_get_config:
        
        mock_get_config.return_value = {
            "models": {
                "test": "gpt-4-prod"
            }
        }
        
        agent = TestAgent()
        model = agent._choose_model("test")
        assert model == "gpt-4-prod"
    
    # Test with fallback
    with patch("os.environ", {"OPENAI_API_KEY": "test"}), \
         patch("shortcut_agents.base_agent.get_config") as mock_get_config:
        
        mock_get_config.return_value = {
            "models": {}
        }
        
        agent = TestAgent()
        model = agent._choose_model("test", fallback="gpt-3.5-turbo")
        assert model == "gpt-3.5-turbo"