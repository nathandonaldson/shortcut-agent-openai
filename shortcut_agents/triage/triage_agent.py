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

# Import storage utilities
from utils.storage.local_storage import local_storage

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
            try:
                if result.workflow == "enhance":
                    logger.info(f"Handing off to Update Agent for enhancement")
                    
                    # Import the update agent creator function
                    from shortcut_agents.update.update_agent import create_update_agent
                    
                    # Create the update agent
                    update_agent = create_update_agent()
                    
                    # Prepare input data for the update agent
                    input_data = {
                        "workflow": "enhance",
                        "story_id": result.story_id,
                        "workspace_id": result.workspace_id,
                        "story_data": workspace_context.story_data
                    }
                    
                    # Record the handoff
                    handoff_id = record_handoff(
                        source_agent="Triage Agent",
                        target_agent="Update Agent",
                        workspace_context=workspace_context,
                        input_data=input_data
                    )
                    
                    # Return success with handoff info
                    return {
                        "status": "success",
                        "handoff": {
                            "source": "Triage Agent",
                            "target": "Update Agent",
                            "handoff_id": handoff_id
                        }
                    }
                    
                elif result.workflow in ["analyse", "analyze"]:
                    logger.info(f"Handing off to Analysis Agent for analysis")
                    
                    # Import the analysis agent creator function
                    from shortcut_agents.analysis.analysis_agent import create_analysis_agent
                    
                    # Create the analysis agent
                    analysis_agent = create_analysis_agent()
                    
                    # Prepare input data for the analysis agent
                    input_data = {
                        "workflow": "analyse",
                        "story_id": result.story_id,
                        "workspace_id": result.workspace_id,
                        "story_data": workspace_context.story_data
                    }
                    
                    # Record the handoff
                    handoff_id = record_handoff(
                        source_agent="Triage Agent",
                        target_agent="Analysis Agent",
                        workspace_context=workspace_context,
                        input_data=input_data
                    )
                    
                    # Return success with handoff info
                    return {
                        "status": "success",
                        "handoff": {
                            "source": "Triage Agent",
                            "target": "Analysis Agent",
                            "handoff_id": handoff_id
                        }
                    }
            except Exception as e:
                logger.error(f"Error during handoff: {str(e)}")
                # Continue with no handoff
        
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
        story_id = None
        
        # Check if story data is already in context
        if hasattr(workspace_context, "story_data") and workspace_context.story_data:
            story_data = workspace_context.story_data
            story_id = str(story_data.get("id", ""))
        
        # Process the webhook to determine if it needs processing
        try:
            # Check for labels in the story data
            labels = []
            if hasattr(workspace_context, "story_data") and workspace_context.story_data:
                story_labels = workspace_context.story_data.get("labels", [])
                for label in story_labels:
                    label_name = label.get("name", "").lower()
                    logger.info(f"Found label in story data: {label_name}")
                    labels.append(label_name)
            
            # Log all found labels
            logger.info(f"All labels found (lowercase): {labels}")
            
            # Determine workflow based on labels
            workflow = None
            if "enhance" in labels:
                logger.info("Found 'enhance' label - selecting enhancement workflow")
                workflow = "enhance"
                workspace_context.workflow_type = WorkflowType.ENHANCE
                logger.info("Setting workflow type to ENHANCE in context")
            elif "analyse" in labels or "analyze" in labels:
                logger.info("Found 'analyse' or 'analyze' label - selecting analysis workflow")
                workflow = "analyse"
                workspace_context.workflow_type = WorkflowType.ANALYSE
                logger.info("Setting workflow type to ANALYSE in context")
            
            # Create a result object
            result = TriageOutput(
                processed=workflow is not None,
                workflow=workflow,
                story_id=story_id,
                workspace_id=workspace_context.workspace_id,
                reason=None if workflow else "No relevant labels found",
                next_steps=["Queue for enhancement"] if workflow == "enhance" else 
                           ["Queue for analysis"] if workflow == "analyse" else 
                           ["No action needed"]
            )
            
            # Save the task to local storage
            local_storage.save_task(workspace_context.workspace_id, story_id, {"status": "pending"})
            
            # Process the result and perform handoff if needed
            if result.processed and result.workflow:
                try:
                    handoff_result = await self.process_and_handoff(result, workspace_context)
                    logger.info(f"Handoff successful: {handoff_result}")
                    return handoff_result
                except Exception as e:
                    logger.error(f"Error during handoff: {str(e)}")
                    # Continue with no handoff
            
            # Create a standard response
            return {
                "status": "success",
                "agent": "triage",
                "result": result.dict() if hasattr(result, "dict") else vars(result),
                "metadata": {
                    "agent": "triage",
                    "model": self.get_model(),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "request_id": workspace_context.request_id,
                    "workspace_id": workspace_context.workspace_id,
                    "story_id": story_id
                }
            }
        except Exception as e:
            logger.error(f"Error in simplified triage: {str(e)}")
            return self._create_error_result(str(e), workspace_context)


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
    Create a triage agent using the OpenAI Agent SDK.
    
    Returns:
        Agent instance
    """
    # Import tools here to avoid circular imports
    from tools.shortcut.shortcut_tools import get_story_details
    
    # Create function tools for the agent
    tools = [
        function_tool(
            func=wrapped_get_story_details,
            description_override="Get details of a story from Shortcut"
        ),
        function_tool(
            func=wrapped_queue_analysis_task,
            description_override="Queue a story for analysis"
        ),
        function_tool(
            func=wrapped_queue_enhancement_task,
            description_override="Queue a story for enhancement"
        )
    ]
    
    # Create analysis agent for handoff
    from shortcut_agents.analysis.analysis_agent import create_analysis_agent
    analysis_agent = Agent(
        name="Analysis Agent",
        instructions="You analyze Shortcut stories for quality and provide recommendations.",
        handoff_description="Specialist agent for analyzing story quality"
    )
    
    # Create update agent for handoff
    from shortcut_agents.update.update_agent import create_update_agent
    update_agent = Agent(
        name="Update Agent",
        instructions="You enhance Shortcut stories based on analysis results.",
        handoff_description="Specialist agent for enhancing story content"
    )
    
    # Get the model to use
    model = get_triage_model()
    logger.info(f"Using model {model} for triage agent")
    
    # Create model settings
    model_settings = ModelSettings()
    
    # Only set temperature for models that support it
    # o3-mini and o3 models don't support temperature
    if not any(x in model.lower() for x in ["o3-mini", "o3", "gpt-4o"]):
        model_settings = ModelSettings(
            temperature=0.2  # Low temperature for consistent, predictable responses
        )
    
    # Create the agent with proper configuration
    # IMPORTANT: We're disabling handoffs to prevent duplicate processing
    agent = Agent(
        name="Triage Agent",
        instructions=TRIAGE_SYSTEM_MESSAGE,
        model=model,
        model_settings=model_settings,
        tools=tools,
        output_type=TriageOutput,
        # Disable handoffs to prevent duplicate processing
        handoffs=[]  # Empty list means no handoffs
    )
    
    return agent


# Create a custom wrapper for the queue_analysis_task function to ensure API key is passed correctly
async def wrapped_queue_analysis_task(workspace_id: str, story_id: str, api_key: str = None) -> Dict[str, Any]:
    """
    Wrapper for queue_analysis_task that ensures the API key is passed correctly.
    
    Args:
        workspace_id: Shortcut workspace ID
        story_id: Story ID to analyze
        api_key: Shortcut API key
        
    Returns:
        Task details
    """
    # Log the API key being used (masked for security)
    if api_key:
        api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
        logger.info(f"Using provided API key starting with {api_key_snippet} for workspace {workspace_id}")
    else:
        # If no API key is provided, try to get it from environment variables
        env_var_name = f"SHORTCUT_API_KEY_{workspace_id.upper()}"
        api_key = os.environ.get(env_var_name)
        if not api_key:
            api_key = os.environ.get("SHORTCUT_API_KEY")
        
        if api_key:
            api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
            logger.info(f"Using environment API key starting with {api_key_snippet} for workspace {workspace_id}")
        else:
            logger.warning(f"No API key provided for workspace {workspace_id}")
            raise ValueError(f"No API key provided for workspace {workspace_id}")
    
    # Call the original function with the correct API key
    return await queue_analysis_task(workspace_id, story_id, api_key)


# Create a custom wrapper for the queue_enhancement_task function to ensure API key is passed correctly
async def wrapped_queue_enhancement_task(workspace_id: str, story_id: str, api_key: str = None) -> Dict[str, Any]:
    """
    Wrapper for queue_enhancement_task that ensures the API key is passed correctly.
    
    Args:
        workspace_id: Shortcut workspace ID
        story_id: Story ID to enhance
        api_key: Shortcut API key
        
    Returns:
        Task details
    """
    # Log the API key being used (masked for security)
    if api_key:
        api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
        logger.info(f"Using provided API key starting with {api_key_snippet} for workspace {workspace_id}")
    else:
        # If no API key is provided, try to get it from environment variables
        env_var_name = f"SHORTCUT_API_KEY_{workspace_id.upper()}"
        api_key = os.environ.get(env_var_name)
        if not api_key:
            api_key = os.environ.get("SHORTCUT_API_KEY")
        
        if api_key:
            api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
            logger.info(f"Using environment API key starting with {api_key_snippet} for workspace {workspace_id}")
        else:
            logger.warning(f"No API key provided for workspace {workspace_id}")
            raise ValueError(f"No API key provided for workspace {workspace_id}")
    
    # Call the original function with the correct API key
    return await queue_enhancement_task(workspace_id, story_id, api_key)


# Create a custom wrapper for the get_story_details function to ensure API key is passed correctly
async def wrapped_get_story_details(story_id: str, api_key: str = None) -> Dict[str, Any]:
    """
    Wrapper for get_story_details that ensures the API key is passed correctly.
    
    Args:
        story_id: The ID of the story to retrieve
        api_key: Shortcut API key
        
    Returns:
        Story details
    """
    # Log the API key being used (masked for security)
    if api_key:
        api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
        logger.info(f"Using provided API key starting with {api_key_snippet} for story {story_id}")
    else:
        # If no API key is provided, try to get it from environment variables
        api_key = os.environ.get("SHORTCUT_API_KEY")
        
        if api_key:
            api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
            logger.info(f"Using environment API key starting with {api_key_snippet} for story {story_id}")
        else:
            logger.warning(f"No API key provided for story {story_id}")
            raise ValueError(f"No API key provided for story {story_id}")
    
    # Call the original function with the correct API key
    return await get_story_details(story_id, api_key)


async def process_webhook(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook using the triage agent.
    
    Args:
        webhook_data: Webhook data to process
        workspace_context: Workspace context
        
    Returns:
        Processing result
    """
    logger.info("Processing webhook with triage agent")
    
    try:
        # Create the triage agent
        agent = create_triage_agent()
        
        # Get API key for the workspace
        api_key = workspace_context.api_key
        if api_key:
            api_key_snippet = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***masked***"
            logger.info(f"Using API key starting with {api_key_snippet} for workspace {workspace_context.workspace_id}")
        
        # Create a trace for the triage agent
        trace_id = f"Triage-{workspace_context.workspace_id}-{workspace_context.story_id}"
        
        # Create a context for the agent
        context = {
            "workspace_id": workspace_context.workspace_id,
            "story_id": workspace_context.story_id,
            "api_key": api_key,
            "request_id": workspace_context.request_id
        }
        
        # Determine if we should use handoffs or queue tasks
        # For webhook processing, we'll queue tasks instead of using handoffs
        # to prevent duplicate processing
        use_handoffs = False
        
        if use_handoffs:
            # Run the agent with handoffs enabled
            logger.info("Running triage agent using OpenAI Agent SDK with handoffs")
            result = await Runner.run(agent, webhook_data, context=context, trace_id=trace_id)
            
            # Extract the final output
            if hasattr(result, "final_output") and result.final_output:
                triage_decision = result.final_output
            else:
                triage_decision = {"processed": False, "reason": "No output from triage agent"}
        else:
            # Run the agent without handoffs
            logger.info("Running triage agent using OpenAI Agent SDK without handoffs")
            result = await Runner.run(agent, webhook_data, context=context, trace_id=trace_id)
            
            # Extract the final output
            if hasattr(result, "final_output") and result.final_output:
                triage_decision = result.final_output
                
                # Log the triage decision
                logger.info(f"Triage decision: {triage_decision.get('workflow', 'skip processing')}")
            else:
                triage_decision = {"processed": False, "reason": "No output from triage agent"}
        
        return {
            "result": triage_decision,
            "trace_id": trace_id
        }
    except Exception as e:
        logger.error(f"Error processing webhook with triage agent: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a simple result for error cases
        return {
            "result": {
                "processed": False,
                "reason": f"Error: {str(e)}"
            }
        }