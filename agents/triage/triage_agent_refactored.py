"""
Triage Agent for the Shortcut Enhancement System.

This agent examines incoming webhooks and determines appropriate processing actions.
This version is refactored to use the BaseAgent implementation.
"""

import logging
import datetime
import time
from typing import Dict, Any, List, Optional

from openai.types.agent import FunctionTool

from agents.base_agent import BaseAgent, BaseAgentHooks
from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from tools.shortcut.shortcut_tools import get_story_details, queue_enhancement_task, queue_analysis_task

# Set up logging
logger = logging.getLogger("triage_agent")

# Triage Agent system message
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

# Define TriageOutput class
class TriageOutput:
    """Output from the Triage Agent."""
    
    def __init__(self, 
                 processed: bool, 
                 workflow: Optional[str] = None,
                 story_id: Optional[str] = None,
                 workspace_id: Optional[str] = None,
                 reason: Optional[str] = None,
                 next_steps: Optional[List[str]] = None):
        self.processed = processed
        self.workflow = workflow
        self.story_id = story_id
        self.workspace_id = workspace_id
        self.reason = reason
        self.next_steps = next_steps or []
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "processed": self.processed,
            "workflow": self.workflow,
            "story_id": self.story_id,
            "workspace_id": self.workspace_id,
            "reason": self.reason,
            "next_steps": self.next_steps
        }


class TriageAgentHooks(BaseAgentHooks[TriageOutput]):
    """Lifecycle hooks for the Triage Agent."""
    
    async def process_result(self, workspace_context: WorkspaceContext, result: TriageOutput) -> None:
        """
        Process the triage result.
        
        Args:
            workspace_context: The workspace context
            result: The triage result
        """
        # Convert result to dictionary if needed
        if hasattr(result, "dict") and callable(result.dict):
            result_dict = result.dict()
        else:
            result_dict = vars(result)
            
        # Store the result in the workspace context
        workspace_context.triage_result = result_dict
        
        # Set workflow type if applicable
        if result.workflow == "enhance":
            workspace_context.set_workflow_type(WorkflowType.ENHANCE)
        elif result.workflow in ["analyse", "analyze"]:
            workspace_context.set_workflow_type(WorkflowType.ANALYSE)
            
        logger.info(f"Stored triage results in workspace context: {result.workflow}")


class TriageAgent(BaseAgent[TriageOutput, Dict[str, Any]]):
    """
    Agent responsible for triaging incoming webhooks from Shortcut.
    """
    
    def __init__(self):
        """Initialize the Triage Agent."""
        
        # Input validation function
        from openai.types.agent.guardrails import input_guardrail, GuardrailFunctionOutput
        
        @input_guardrail
        async def validate_webhook_input(ctx, agent, input_data):
            """Validate the webhook input data."""
            # Implement validation logic
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Input validation successful"},
                tripwire_triggered=False
            )
        
        # Create tools list
        tools = [
            FunctionTool(
                function=get_story_details,
                description="Get details about a Shortcut story"
            ),
            FunctionTool(
                function=queue_enhancement_task,
                description="Queue a story for enhancement processing"
            ),
            FunctionTool(
                function=queue_analysis_task,
                description="Queue a story for analysis processing"
            )
        ]
        
        # Initialize the base agent
        super().__init__(
            agent_type="triage",
            agent_name="Triage Agent",
            system_message=TRIAGE_SYSTEM_MESSAGE,
            output_class=TriageOutput,
            hooks_class=TriageAgentHooks,
            input_guardrails=[validate_webhook_input],
            output_guardrails=[],
            allowed_handoffs=["Analysis Agent", "Update Agent"],
            tools=tools,
            model_override=None
        )
    
    async def run_simplified(self, webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Run a simplified version of the triage agent for development/testing.
        
        Args:
            webhook_data: Webhook data from Shortcut
            workspace_context: Workspace context
            
        Returns:
            Dictionary with execution results
        """
        logger.info("Running simplified triage process")
        
        # Extract story ID from webhook data
        story_id = str(webhook_data.get("id", ""))
        if not story_id and "primary_id" in webhook_data:
            story_id = str(webhook_data.get("primary_id", ""))
        
        # Set story ID in workspace context
        workspace_context.story_id = story_id
        
        # Check for labels in actions
        label_names = []
        if "actions" in webhook_data and webhook_data["actions"]:
            for action in webhook_data["actions"]:
                if action.get("action") == "update" and "changes" in action:
                    # Handle label changes
                    changes = action.get("changes", {})
                    if "labels" in changes and "adds" in changes["labels"]:
                        for label in changes["labels"]["adds"]:
                            if isinstance(label, dict) and "name" in label:
                                label_names.append(label["name"].lower())
        
        # Determine workflow type
        workflow = None
        processed = False
        reason = "No relevant labels found"
        
        if "enhance" in label_names:
            workflow = "enhance"
            processed = True
            reason = None
        elif "analyse" in label_names or "analyze" in label_names:
            workflow = "analyse"
            processed = True
            reason = None
        
        # Create result
        result = TriageOutput(
            processed=processed,
            workflow=workflow,
            story_id=story_id,
            workspace_id=workspace_context.workspace_id,
            reason=reason,
            next_steps=["Queue for enhancement"] if workflow == "enhance" else (
                ["Queue for analysis"] if workflow == "analyse" else []
            )
        )
        
        # Process the result using the base agent's method
        return self._process_result(result, workspace_context)


# Convenience function to create a triage agent
def create_triage_agent() -> TriageAgent:
    """
    Create and configure the Triage Agent.
    
    Returns:
        Configured Triage Agent
    """
    return TriageAgent()


# Function for processing webhooks (main entry point)
async def process_webhook(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook using the Triage Agent.
    
    Args:
        webhook_data: Webhook data from Shortcut
        workspace_context: Workspace context
        
    Returns:
        Triage result dictionary
    """
    # Create and run the agent
    agent = create_triage_agent()
    return await agent.run(webhook_data, workspace_context)