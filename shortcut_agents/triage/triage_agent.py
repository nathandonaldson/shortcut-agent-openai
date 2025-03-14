"""
Triage Agent for the Shortcut Enhancement System.

This agent examines incoming webhooks and determines appropriate processing actions.
This version is refactored to use the BaseAgent implementation.
"""

import logging
import datetime
import time
from typing import Dict, Any, List, Optional

from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks, FunctionTool
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

The webhook data may contain label information in different formats:
- Directly in a "labels" field with label names
- As label IDs in a "label_ids" field, with label names in a "references" section
- In the story data itself if already fetched

Look carefully at all parts of the webhook, including the "references" section, to find labels
that have been added to the story. Check both the story data and the webhook data for labels.

Ignore all other webhook events that don't involve these labels being added.
"""

# Import Pydantic for model validation
from pydantic import BaseModel, Field

# Define TriageOutput class as a Pydantic model for SDK compatibility
class TriageOutput(BaseModel):
    """Output from the Triage Agent."""
    
    processed: bool
    workflow: Optional[str] = None
    story_id: Optional[str] = None
    workspace_id: Optional[str] = None
    reason: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)


class TriageAgentHooks(BaseAgentHooks[TriageOutput]):
    """Lifecycle hooks for the Triage Agent."""
    
    async def process_result(self, workspace_context: WorkspaceContext, result: TriageOutput) -> None:
        """
        Process the triage result.
        
        Args:
            workspace_context: The workspace context
            result: The triage result
        """
        # Convert result to dictionary - Pydantic model has model_dump() method
        if hasattr(result, "model_dump") and callable(result.model_dump):
            result_dict = result.model_dump()
        elif hasattr(result, "dict") and callable(result.dict):
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
        from shortcut_agents.guardrail import input_guardrail, GuardrailFunctionOutput
        
        @input_guardrail
        async def validate_webhook_input(ctx, agent, input_data):
            """Validate the webhook input data."""
            # Implement validation logic
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Input validation successful"},
                tripwire_triggered=False
            )
        
        # Create tools list using function_tool from the agents package
        # The SDK version requires a different initialization pattern
        # We need to use the function_tool decorator from agents
        
        from agents import function_tool
        
        # Create tools list using function_tool
        tools = [
            function_tool(
                func=get_story_details,
                description_override="Get details about a Shortcut story"
            ),
            function_tool(
                func=queue_enhancement_task,
                description_override="Queue a story for enhancement processing"
            ),
            function_tool(
                func=queue_analysis_task,
                description_override="Queue a story for analysis processing"
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
        
        # First try to get labels from story data in context if available
        label_names = []
        if hasattr(workspace_context, "story_data") and workspace_context.story_data:
            # Get labels from actual story data
            story_labels = workspace_context.story_data.get("labels", [])
            for label in story_labels:
                if isinstance(label, dict) and "name" in label:
                    # Convert to lowercase for case-insensitive comparison
                    label_names.append(label["name"].lower())
                    logger.info(f"Found label in story data: {label['name']}")
        
        # If no labels found in story data, check webhook actions
        if not label_names and "actions" in webhook_data and webhook_data["actions"]:
            for action in webhook_data["actions"]:
                if action.get("action") == "update" and "changes" in action:
                    # Handle label changes
                    changes = action.get("changes", {})
                    
                    # Check for labels in traditional format
                    if "labels" in changes and "adds" in changes["labels"]:
                        for label in changes["labels"]["adds"]:
                            if isinstance(label, dict) and "name" in label:
                                label_names.append(label["name"].lower())
                                logger.info(f"Found label in webhook: {label['name']}")
                    
                    # Check for label_ids format
                    if "label_ids" in changes and "adds" in changes["label_ids"]:
                        # If we have label_ids, we need to check the references section
                        if "references" in webhook_data:
                            for reference in webhook_data["references"]:
                                if (reference.get("entity_type") == "label" and 
                                    reference.get("id") in changes["label_ids"]["adds"]):
                                    label_name = reference.get("name", "").lower()
                                    label_names.append(label_name)
                                    logger.info(f"Found label in references: {reference.get('name')}")
        
        # Log all found labels
        logger.info(f"All labels found (lowercase): {label_names}")
        
        # Determine workflow type - use case-insensitive comparison
        workflow = None
        processed = False
        reason = "No relevant labels found"
        
        if any(label in ["enhance", "enhancement"] for label in label_names):
            workflow = "enhance"
            processed = True
            reason = None
            logger.info("Found 'enhance' label - selecting enhancement workflow")
        elif any(label in ["analyse", "analyze", "analysis"] for label in label_names):
            workflow = "analyse"
            processed = True
            reason = None
            logger.info("Found 'analyse'/'analyze' label - selecting analysis workflow")
        
        # Create result using Pydantic model
        next_steps = []
        if workflow == "enhance":
            next_steps = ["Queue for enhancement"]
        elif workflow == "analyse":
            next_steps = ["Queue for analysis"]
            
        result = TriageOutput(
            processed=processed,
            workflow=workflow,
            story_id=story_id,
            workspace_id=workspace_context.workspace_id,
            reason=reason,
            next_steps=next_steps
        )
        
        # Set workflow type in context
        if result.workflow == "enhance":
            logger.info("Setting workflow type to ENHANCE in context")
            workspace_context.set_workflow_type(WorkflowType.ENHANCE)
        elif result.workflow in ["analyse", "analyze"]:
            logger.info("Setting workflow type to ANALYSE in context")
            workspace_context.set_workflow_type(WorkflowType.ANALYSE)
        
        # Process the result using the base agent's method
        processed_result = self._process_result(result, workspace_context)
        
        # Double-check workflow type after processing
        logger.info(f"Workflow type after processing: {workspace_context.workflow_type}")
        
        return processed_result


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