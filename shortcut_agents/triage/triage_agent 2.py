"""
Triage Agent for determining how to process Shortcut stories.
"""

import os
import logging
import json
import time
from typing import Dict, Any, List, Optional

import openai
from openai import OpenAI
from shortcut_agents import AgentChatResponse, Agent, AgentHooks, GuardrailFunctionOutput
from shortcut_agents import RunContextWrapper, FunctionTool, Tool, Handoffs
from shortcut_agents.tool import FunctionDefinition
from shortcut_agents.lifecycle import FunctionOutputPair, FunctionInputPair, RunStep
from shortcut_agents import ModelSettings
from shortcut_agents import AgentOutputSchema as OutputType
from shortcut_agents.guardrail import input_guardrail, output_guardrail
from shortcut_agents.tracing import Trace, Span, get_current_trace, trace
from shortcut_agents import Runner

from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from tools.shortcut.shortcut_tools import (
    get_story_details, 
    queue_enhancement_task, 
    queue_analysis_task
)
from shortcut_agents.update.update_agent import create_update_agent, process_update

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

# Define a Pydantic model for Triage output
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

# Triage Agent Hooks
class TriageAgentHooks(AgentHooks):
    """Hooks for the Triage Agent lifecycle."""
    
    async def pre_generation(self, context, agent, input_items):
        """Hook that runs before the agent generates a response."""
        logger.info("Starting triage process")
        return input_items
    
    async def post_generation(self, context, agent, response):
        """Hook that runs after the agent generates a response."""
        logger.info("Triage completed")
        
        # Check if we have workspace context and triage results
        if hasattr(context, 'context') and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            
            # Extract the triage results if available
            triage_result = None
            for item in response.items:
                if item.type == "output_type" and hasattr(item, "value"):
                    triage_result = item.value
                    break
            
            # Store the results in the workspace context
            if triage_result:
                result_dict = triage_result.dict() if hasattr(triage_result, "dict") else vars(triage_result)
                workspace_context.triage_result = result_dict
                logger.info("Stored triage results in workspace context")
                
                # Preserve trace context for potential handoffs
                from utils.tracing import prepare_handoff_context
                prepare_handoff_context(workspace_context)
        
        return response
    
    async def pre_function_call(self, context, function_call):
        """Hook that runs before a function is called."""
        function_name = getattr(function_call, 'name', 'unknown')
        
        # Redact sensitive parameters in logs
        safe_params = {}
        if hasattr(function_call, 'parameters'):
            for key, value in function_call.parameters.items():
                if key.lower() in ["api_key", "token", "password", "secret"]:
                    safe_params[key] = "[REDACTED]"
                else:
                    safe_params[key] = value
        
        logger.info(
            f"Calling function: {function_name}",
            extra={"parameters": safe_params, "agent": "triage"}
        )
        return function_call
    
    async def post_function_call(self, context, function_output):
        """Hook that runs after a function is called."""
        function_name = getattr(function_output, 'name', 'unknown')
        
        # Log without including potentially sensitive output
        output_type = type(getattr(function_output, 'output', None)).__name__
        logger.info(
            f"Function completed: {function_name}",
            extra={"output_type": output_type, "agent": "triage"}
        )
        return function_output

def create_triage_agent() -> Agent:
    """Create and configure the triage agent with OpenAI Agent SDK."""
    
    model = get_triage_model()
    logger.info(f"Creating triage agent with model: {model}")
    
    # Create function tools for extracting information from webhooks
    function_tools = [
        FunctionTool(
            function=get_story_details,
            description="Get details of a Shortcut story by ID",
        )
    ]
    
    # Create the agent with proper OpenAI Agent SDK configuration
    agent = Agent(
        name="Triage Agent",
        instructions=TRIAGE_SYSTEM_MESSAGE,
        model=model,
        model_settings=ModelSettings(
            temperature=0.1,  # Low temperature for consistent, predictable responses
            response_format={"type": "json_object"}  # Ensure JSON output format
        ),
        tools=function_tools,
        hooks=TriageAgentHooks(),
        output_type={'result_type': TriageOutput},
        handoffs=Handoff(
            enabled=True,
            allow=["Analysis Agent", "Update Agent"]  # Allow handoff to these agents
        )
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
    
    # Set request ID if not already set
    if not workspace_context.request_id:
        workspace_context.request_id = f"webhook_{int(time.time())}"
    
    # Create trace for the triage process
    with trace(
        workflow_name="Webhook Triage",
        group_id=f"{workspace_context.workspace_id}",
        trace_metadata={
            "request_id": workspace_context.request_id,
            "workspace_id": workspace_context.workspace_id,
            "webhook_type": webhook_data.get("action", "unknown")
        }
    ):
        # Create the triage agent
        triage_agent = create_triage_agent()
        logger.info(f"Using triage agent: {triage_agent.name} with model {triage_agent.model}")
        
        # For environments without OPENAI_API_KEY, use simplified logic
        if os.environ.get("OPENAI_API_KEY") is None:
            logger.warning("OpenAI API key not found, using simplified triage process")
            return await process_webhook_simplified(webhook_data, workspace_context)
        
        try:
            # Convert webhook data to JSON string
            input_json = json.dumps(webhook_data)
            
            # Run the agent with the OpenAI Agent SDK
            logger.info("Running Triage Agent with OpenAI Agent SDK")
            result = await Runner.run(
                agent=triage_agent,
                input=input_json,
                context=workspace_context
            )
            
            # Extract the triage result
            triage_result = None
            for item in result.items:
                if item.type == "output_type" and hasattr(item, "value"):
                    triage_result = item.value
                    break
            
            if triage_result:
                # Convert to dictionary
                result_dict = triage_result.dict() if hasattr(triage_result, "dict") else vars(triage_result)
                logger.info(f"Triage result: {result_dict}")
                return result_dict
            else:
                # Fallback to simplified implementation
                logger.warning("Could not extract triage result, falling back to simplified implementation")
                return await process_webhook_simplified(webhook_data, workspace_context)
        except Exception as e:
            logger.error(f"Error running Triage Agent: {str(e)}")
            return await process_webhook_simplified(webhook_data, workspace_context)


async def process_webhook_simplified(webhook_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a webhook using simplified logic without OpenAI Agent SDK.
    
    Args:
        webhook_data: The raw webhook data from Shortcut
        workspace_context: The workspace context
        
    Returns:
        Dictionary with processing results
    """
    logger.info("Using simplified webhook processing logic")
    
    # Extract the story ID from the webhook data
    story_id = str(webhook_data.get("id", ""))
    if not story_id and "primary_id" in webhook_data:
        story_id = str(webhook_data.get("primary_id", ""))
    
    logger.info(f"Processing story ID: {story_id}")
    
    # Get label changes
    label_adds = []
    
    # Check direct changes (old format)
    changes = webhook_data.get("changes", {})
    if "labels" in changes and "adds" in changes.get("labels", {}):
        label_adds.extend(changes["labels"]["adds"])
    
    # Check actions[].changes (new format)
    if "actions" in webhook_data and webhook_data["actions"]:
        for action in webhook_data["actions"]:
            action_changes = action.get("changes", {})
            
            # Check for label_ids
            if "label_ids" in action_changes and "adds" in action_changes.get("label_ids", {}):
                # In this format, we get label IDs
                label_id_adds = action_changes["label_ids"]["adds"]
                
                # If references are provided, map IDs to names
                if "references" in webhook_data:
                    for label_ref in webhook_data.get("references", []):
                        if label_ref.get("entity_type") == "label":
                            for label_id_obj in label_id_adds:
                                if isinstance(label_id_obj, dict) and label_id_obj.get("id") == label_ref.get("id"):
                                    label_adds.append({"name": label_ref.get("name")})
                                elif isinstance(label_id_obj, int) and label_id_obj == label_ref.get("id"):
                                    label_adds.append({"name": label_ref.get("name")})
                else:
                    # Just add the IDs as is
                    for label_id_obj in label_id_adds:
                        if isinstance(label_id_obj, dict) and "name" in label_id_obj:
                            label_adds.append({"name": label_id_obj.get("name")})
            
            # Also check direct labels field
            if "labels" in action_changes and "adds" in action_changes.get("labels", {}):
                label_adds.extend(action_changes["labels"]["adds"])
    
    # Check if we found any label additions
    if not label_adds:
        logger.info("No label additions found in webhook data")
        return {
            "processed": False,
            "reason": "No label additions found",
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id
        }
    
    # Check for specific labels
    label_names = [label.get("name", "").lower() for label in label_adds]
    logger.info(f"Labels added: {label_names}")
    
    # Determine workflow type based on labels
    if "enhance" in label_names:
        logger.info("Enhancement workflow triggered")
        # Queue for enhancement
        task_info = await queue_enhancement_task(
            workspace_context.workspace_id,
            story_id,
            workspace_context.api_key
        )
        
        # Set the workflow type in the context
        workspace_context.set_workflow_type(WorkflowType.ENHANCE)
        
        return {
            "processed": True,
            "workflow": "enhance",
            "task_info": task_info,
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id,
            "next_agent": "Update Agent",  # Indicate the next agent in flow
            "update_type": "enhancement"  # Specify the update type for the Update Agent
        }
        
    elif "analyse" in label_names or "analyze" in label_names:
        logger.info("Analysis workflow triggered")
        # Queue for analysis
        task_info = await queue_analysis_task(
            workspace_context.workspace_id,
            story_id,
            workspace_context.api_key
        )
        
        # Set the workflow type in the context
        workspace_context.set_workflow_type(WorkflowType.ANALYSE)
        
        return {
            "processed": True,
            "workflow": "analyse",
            "task_info": task_info,
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id,
            "next_agent": "Update Agent",  # Indicate the next agent in flow
            "update_type": "analysis"  # Specify the update type for the Update Agent
        }
    
    logger.info("No relevant labels found")
    return {
        "processed": False,
        "reason": "No relevant labels found",
        "labels": label_names,
        "workspace_id": workspace_context.workspace_id,
        "story_id": story_id
    }