"""
Triage Agent for the Shortcut Enhancement System.

This agent examines incoming webhooks and determines appropriate processing actions.
This implementation follows OpenAI Agent SDK best practices for handoffs, guardrails, and tracing.
"""

import logging
import datetime
import time
import uuid
import json
import os
from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel, Field

# Import OpenAI Agent SDK components
from agents import (
    Agent, Runner, ModelSettings, function_tool, trace, RunConfig,
    input_guardrail, output_guardrail, GuardrailFunctionOutput
)

# Import base agent components
from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks
from context.workspace.workspace_context import WorkspaceContext, WorkflowType

# Import Shortcut tools
from tools.shortcut.shortcut_tools import get_story_details, queue_enhancement_task, queue_analysis_task

# Import tracing utilities
from utils.tracing import prepare_handoff_context, restore_handoff_context, record_handoff

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

# Define TriageOutput class as a Pydantic model for SDK compatibility
class TriageOutput(BaseModel):
    """Output from the Triage Agent."""
    
    processed: bool = Field(description="Whether the webhook was processed")
    workflow: Optional[str] = Field(None, description="The workflow type (enhance or analyse)")
    story_id: Optional[str] = Field(None, description="The ID of the story")
    workspace_id: Optional[str] = Field(None, description="The ID of the workspace")
    reason: Optional[str] = Field(None, description="Reason for not processing")
    next_steps: List[str] = Field(default_factory=list, description="Next steps to take")


class TriageAgentHooks(BaseAgentHooks[TriageOutput]):
    """Lifecycle hooks for the Triage Agent."""
    
    async def process_result(self, workspace_context: WorkspaceContext, result: TriageOutput) -> None:
        """
        Process the triage result.
        
        Args:
            workspace_context: The workspace context
            result: The triage result
        """
        # Convert result to dictionary
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
            logger.info(f"Setting workflow type to ENHANCE for story {result.story_id}")
        elif result.workflow in ["analyse", "analyze"]:
            workspace_context.set_workflow_type(WorkflowType.ANALYSE)
            logger.info(f"Setting workflow type to ANALYSE for story {result.story_id}")
            
        logger.info(f"Stored triage results in workspace context: {result.workflow}")


# Input validation guardrail
@input_guardrail
async def validate_webhook_input(ctx, agent, input_data: Dict[str, Any]) -> GuardrailFunctionOutput:
    """
    Validate the webhook input data.
    
    Args:
        ctx: The context
        agent: The agent
        input_data: The input data to validate
        
    Returns:
        Guardrail function output
    """
    # Check if input data is a dictionary
    if not isinstance(input_data, dict):
        return GuardrailFunctionOutput(
            output_info={"valid": False},
            tripwire_triggered=True,
            reason="Input data is not a dictionary"
        )
    
    # Check if we have a story ID somewhere in the data
    story_id = None
    
    # Check direct fields
    if "id" in input_data:
        story_id = input_data["id"]
    elif "primary_id" in input_data:
        story_id = input_data["primary_id"]
    
    # Check nested data
    elif "data" in input_data and isinstance(input_data["data"], dict):
        nested_data = input_data["data"]
        if "id" in nested_data:
            story_id = nested_data["id"]
        elif "primary_id" in nested_data:
            story_id = nested_data["primary_id"]
    
    if not story_id:
        return GuardrailFunctionOutput(
            output_info={"valid": False},
            tripwire_triggered=True,
            reason="Could not find story ID in webhook data"
        )
    
    # All checks passed
    return GuardrailFunctionOutput(
        output_info={"valid": True, "story_id": story_id},
        tripwire_triggered=False
    )


# Output validation guardrail
@output_guardrail
async def validate_triage_output(ctx, agent, output_data: TriageOutput) -> GuardrailFunctionOutput:
    """
    Validate the triage output.
    
    Args:
        ctx: The context
        agent: The agent
        output_data: The output data to validate
        
    Returns:
        Guardrail function output
    """
    # Check if output is a TriageOutput instance
    if not isinstance(output_data, TriageOutput):
        return GuardrailFunctionOutput(
            output_info={"valid": False},
            tripwire_triggered=True,
            reason="Output is not a TriageOutput instance"
        )
    
    # If processed is True, workflow and story_id must be set
    if output_data.processed:
        if not output_data.workflow:
            return GuardrailFunctionOutput(
                output_info={"valid": False},
                tripwire_triggered=True,
                reason="Processed is True but workflow is not set"
            )
        
        if not output_data.story_id:
            return GuardrailFunctionOutput(
                output_info={"valid": False},
                tripwire_triggered=True,
                reason="Processed is True but story_id is not set"
            )
        
        # Validate workflow value
        if output_data.workflow not in ["enhance", "analyse", "analyze"]:
            return GuardrailFunctionOutput(
                output_info={"valid": False},
                tripwire_triggered=True,
                reason=f"Invalid workflow value: {output_data.workflow}"
            )
    
    # All checks passed
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    )


class TriageAgent(BaseAgent[TriageOutput, Dict[str, Any]]):
    """
    Agent responsible for triaging incoming webhooks from Shortcut.
    """
    
    def __init__(self):
        """Initialize the Triage Agent."""
        
        # Create tools list using function_tool from the agents package
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
        
        # Import the analysis and update agents for handoffs
        from shortcut_agents.analysis.analysis_agent import AnalysisAgent
        from shortcut_agents.update.update_agent import UpdateAgent
        
        # Initialize the base agent
        super().__init__(
            agent_type="triage",
            agent_name="Triage Agent",
            system_message=TRIAGE_SYSTEM_MESSAGE,
            output_class=TriageOutput,
            hooks_class=TriageAgentHooks,
            input_guardrails=[validate_webhook_input],
            output_guardrails=[validate_triage_output],
            allowed_handoffs=["Analysis Agent", "Update Agent"],
            tools=tools,
            model_override=None
        )
        
        # Store agent classes for handoffs
        self.analysis_agent_class = AnalysisAgent
        self.update_agent_class = UpdateAgent
    
    async def process_and_handoff(self, result: TriageOutput, workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Process the triage result and perform handoff if needed.
        
        Args:
            result: The triage result
            workspace_context: The workspace context
            
        Returns:
            Dictionary with handoff results
        """
        # Process the result
        if hasattr(self.hooks_class, "process_result"):
            await self.hooks_class().process_result(workspace_context, result)
        
        # Determine if handoff is needed
        if result.processed and result.workflow:
            if result.workflow == "enhance":
                logger.info(f"Handing off to Update Agent for enhancement")
                return await self.__class__.handoff_to(
                    self.update_agent_class,
                    context=workspace_context,
                    input_data={
                        "workflow": "enhance",
                        "story_id": result.story_id,
                        "workspace_id": result.workspace_id
                    }
                )
            elif result.workflow in ["analyse", "analyze"]:
                logger.info(f"Handing off to Analysis Agent for analysis")
                return await self.__class__.handoff_to(
                    self.analysis_agent_class,
                    context=workspace_context,
                    input_data={
                        "workflow": "analyse",
                        "story_id": result.story_id,
                        "workspace_id": result.workspace_id
                    }
                )
        
        # No handoff needed
        return {
            "status": "success",
            "result": result,
            "handoff": None
        }
    
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
            
        # Check if webhook_data contains a nested 'data' field (common in webhook logs)
        if not story_id and "data" in webhook_data and isinstance(webhook_data["data"], dict):
            # Extract from the nested data structure
            nested_data = webhook_data["data"]
            story_id = str(nested_data.get("id", ""))
            if not story_id and "primary_id" in nested_data:
                story_id = str(nested_data.get("primary_id", ""))
            
            # If we found the story ID in the nested data, use the nested data for further processing
            if story_id:
                webhook_data = nested_data
        
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
                        adds = changes["labels"]["adds"]
                        if isinstance(adds, list):
                            for label in adds:
                                if isinstance(label, dict) and "name" in label:
                                    label_names.append(label["name"].lower())
                                    logger.info(f"Found label in webhook: {label['name']}")
                    
                    # Check for label_ids format
                    if "label_ids" in changes and "adds" in changes["label_ids"]:
                        adds = changes["label_ids"]["adds"]
                        # If we have label_ids, we need to check the references section
                        if isinstance(adds, list) and "references" in webhook_data:
                            for reference in webhook_data["references"]:
                                if (reference.get("entity_type") == "label" and 
                                    reference.get("id") in adds):
                                    label_name = reference.get("name", "").lower()
                                    label_names.append(label_name)
                                    logger.info(f"Found label in references: {reference.get('name')}")
        
        # Also check directly in the webhook data for references
        if not label_names and "references" in webhook_data:
            for reference in webhook_data["references"]:
                if reference.get("entity_type") == "label":
                    label_name = reference.get("name", "").lower()
                    label_names.append(label_name)
                    logger.info(f"Found label directly in references: {reference.get('name')}")
        
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
        
        # Try to perform handoff if appropriate
        if processed and workflow:
            try:
                handoff_result = await self.process_and_handoff(result, workspace_context)
                if handoff_result and handoff_result.get("status") == "success":
                    logger.info(f"Successfully handed off to {handoff_result.get('handoff', {}).get('target', 'unknown agent')}")
                    # Add handoff info to the result
                    processed_result["handoff"] = handoff_result.get("handoff")
            except Exception as e:
                logger.error(f"Error during handoff: {str(e)}")
                # Continue with the regular result
        
        return processed_result


# Function to get the appropriate model for triage
def get_triage_model() -> str:
    """Get the appropriate model for the triage agent."""
    # Try environment variable first
    model = os.environ.get("MODEL_TRIAGE")
    if model:
        return model
    
    # Fall back to gpt-3.5-turbo for development speed
    return "gpt-3.5-turbo"


def create_triage_agent() -> Agent:
    """
    Create a properly configured triage agent using the OpenAI Agent SDK.
    
    Returns:
        Configured Triage Agent
    """
    logger.info("Creating triage agent using OpenAI Agent SDK")
    
    # Get the appropriate model
    model = get_triage_model()
    
    # Create function tools with proper decoration
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
    
    # Import the analysis and update agents for handoffs
    from shortcut_agents.analysis.analysis_agent import create_analysis_agent
    from shortcut_agents.update.update_agent import create_update_agent
    
    # Create the handoff agents
    analysis_agent = create_analysis_agent()
    update_agent = create_update_agent()
    
    # Create the agent with proper configuration
    agent = Agent(
        name="Triage Agent",
        instructions=TRIAGE_SYSTEM_MESSAGE,
        model=model,
        model_settings=ModelSettings(
            temperature=0.2  # Low temperature for consistent, predictable responses
        ),
        tools=tools,
        output_type=TriageOutput,
        handoffs=[analysis_agent, update_agent]  # Add handoffs to the agent
    )
    
    return agent


async def process_webhook(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook with proper tracing.
    
    Args:
        webhook_data: Webhook data from Shortcut
        workspace_context: Workspace context
        
    Returns:
        Triage result dictionary
    """
    logger.info(f"Processing webhook with triage agent")
    
    # Create trace ID from request ID if available
    trace_id = f"trace_{workspace_context.request_id or uuid.uuid4().hex}"
    
    # Prepare run configuration for tracing
    run_config = RunConfig(
        workflow_name=f"Triage-{workspace_context.workspace_id}-{workspace_context.story_id}",
        trace_id=trace_id
    )
    
    try:
        # Check if OpenAI API key is available
        if os.environ.get("OPENAI_API_KEY") is None:
            logger.warning("OpenAI API key not found, using simplified triage process")
            # Create a new TriageAgent instance
            agent = TriageAgent()
            return await agent.run_simplified(webhook_data, workspace_context)
        
        # Create the triage agent using the SDK
        triage_agent = create_triage_agent()
        
        # Log which implementation we're using
        logger.info("Running triage agent using OpenAI Agent SDK with handoffs")
        
        # Convert webhook data to JSON string if needed
        input_data = webhook_data
        if not isinstance(webhook_data, str):
            input_data = json.dumps(webhook_data)
        
        # Run the agent with tracing using the SDK Runner
        with trace(trace_id=trace_id):
            # Use the full SDK implementation with handoffs
            result = await Runner.run(
                starting_agent=triage_agent,
                input=input_data,
                context=workspace_context,
                run_config=run_config
            )
            
            # Extract the final output from the result
            if hasattr(result, "final_output"):
                # Get the final output from the SDK result
                final_output = result.final_output
                
                # Convert to dictionary if needed
                if hasattr(final_output, "model_dump") and callable(final_output.model_dump):
                    result_dict = final_output.model_dump()
                elif hasattr(final_output, "dict") and callable(final_output.dict):
                    result_dict = final_output.dict()
                else:
                    result_dict = vars(final_output) if hasattr(final_output, "__dict__") else final_output
                
                # Log the triage decision
                workflow = result_dict.get("workflow")
                logger.info(f"Triage decision: {workflow or 'skip processing'}")
                
                return result_dict
            else:
                # Fallback to simplified implementation if we can't extract the result
                logger.warning("Could not extract final output from SDK result, falling back to simplified implementation")
                agent = TriageAgent()
                return await agent.run_simplified(webhook_data, workspace_context)
    except Exception as e:
        logger.error(f"Error in triage: {str(e)}")
        # Print the full traceback for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create a basic result in case of error
        return {
            "processed": False,
            "reason": f"Error in triage: {str(e)}",
            "story_id": workspace_context.story_id,
            "workspace_id": workspace_context.workspace_id
        }