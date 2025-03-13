"""
Triage Agent for determining how to process Shortcut stories.
"""

import os
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from openai.types.beta import Assistant
from openai_agents import Agent, FunctionTool, HandoffTool

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from tools.shortcut.shortcut_tools import (
    get_story_details, 
    queue_enhancement_task, 
    queue_analysis_task
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("triage_agent")

# Triage agent system message
TRIAGE_SYSTEM_MESSAGE = """
You are the Triage Agent for a Shortcut story enhancement system. Your job is to:

1. Analyze the incoming webhook data to determine if it requires processing
2. Determine the appropriate workflow based on the story labels
3. Queue the appropriate task (enhancement or analysis)

You should only process story updates with specific labels:
- Stories with the "enhance" label should be queued for enhancement
- Stories with the "analyse" or "analyze" label should be queued for analysis only

Ignore all other webhook events that don't involve these labels being added.
"""

def get_triage_model() -> str:
    """Get the model to use for the triage agent"""
    # Use environment variable with default fallback
    return os.environ.get("MODEL_TRIAGE", "gpt-3.5-turbo")

def create_triage_agent() -> Agent:
    """Create and configure the triage agent"""
    
    model = get_triage_model()
    logger.info(f"Creating triage agent with model: {model}")
    
    # Create function tools
    tools = [
        FunctionTool(
            function=get_story_details,
            description="Get details of a Shortcut story by ID",
        ),
        FunctionTool(
            function=queue_enhancement_task,
            description="Queue a story for full enhancement processing",
        ),
        FunctionTool(
            function=queue_analysis_task,
            description="Queue a story for analysis only (no modifications)",
        )
    ]
    
    # Create the agent
    agent = Agent(
        instructions=TRIAGE_SYSTEM_MESSAGE,
        tools=tools,
        model=model
    )
    
    return agent

async def process_webhook(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook event and determine the appropriate action.
    
    Args:
        webhook_data: The raw webhook data from Shortcut
        workspace_context: The workspace context
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing webhook for workspace: {workspace_context.workspace_id}")
    
    # Create the triage agent
    triage_agent = create_triage_agent()
    
    # Pass the webhook data to the agent
    result = await triage_agent.run(
        webhook_data,
        context=workspace_context
    )
    
    return {
        "processed": True,
        "result": result,
        "workspace_id": workspace_context.workspace_id,
        "story_id": workspace_context.story_id
    }