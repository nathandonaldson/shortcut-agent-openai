"""
Shortcut Enhancement System agent module.

This module provides the agent implementations for the Shortcut Enhancement System.
The agents are implemented using the OpenAI Agent SDK and follow a consistent
pattern based on the BaseAgent class.
"""

# Export agent factory functions
from shortcut_agents.triage.triage_agent_refactored import create_triage_agent, process_webhook
from shortcut_agents.analysis.analysis_agent_refactored import create_analysis_agent, process_analysis
from shortcut_agents.update.update_agent_refactored import create_update_agent, process_update

# Export base agent
from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks

__all__ = [
    'BaseAgent',
    'BaseAgentHooks',
    'create_triage_agent',
    'process_webhook',
    'create_analysis_agent',
    'process_analysis',
    'create_update_agent',
    'process_update'
]