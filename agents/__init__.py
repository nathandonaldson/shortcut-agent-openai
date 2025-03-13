"""
Agent definitions for the Shortcut Enhancement System.
"""

# Re-export triage agent
from agents.triage import create_triage_agent, process_webhook

__all__ = ["create_triage_agent", "process_webhook"]