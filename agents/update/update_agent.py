"""
Update Agent for the Shortcut Enhancement System.

This agent is responsible for applying changes to Shortcut stories based on
analysis or enhancement results, managing tags, and providing status updates.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Import OpenAI Agent SDK components
import openai
from openai import OpenAI
from openai.types.agent import AgentChatResponse, Agent, AgentHooks, GuardrailFunctionOutput
from openai.types.agent import RunContextWrapper, FunctionTool, Tool, Handoffs
from openai.types.agent.function_tools import FunctionDefinition
from openai.types.agent.hooks import FunctionOutputPair, FunctionInputPair, RunStep
from openai.types.shared_params import ModelSettings
from openai.types.agent.utils import OutputType
from openai.types.agent.guardrails import input_guardrail, output_guardrail
from openai.types.agent.tracing import Trace, Span, get_current_trace, trace

# Import the Runner for executing agents
from openai.agent.runner import Runner

# Local imports
from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from agents.update.models import UpdateInput, UpdateResult
from agents.update.tools import (
    update_story_content,
    update_story_labels,
    add_update_comment,
    format_analysis_comment,
    format_enhancement_comment
)
from tools.shortcut.shortcut_tools import get_story
from utils.storage.local_storage import local_storage
from config import get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("update_agent")

# Update Agent system message
UPDATE_SYSTEM_MESSAGE = """
You are the Update Agent for the Shortcut Enhancement System. Your role is to apply changes to stories
based on analysis or enhancement results, update tags, and provide status updates.

You handle two types of updates:
1. Analysis updates: Add a comment with analysis results and update tags (analyse → analysed)
2. Enhancement updates: Update story content, add a comment explaining changes, and update tags (enhance → enhanced)

For each update request:
1. Verify the story exists in Shortcut
2. Apply the appropriate updates based on the update type
3. Update the story tags (labels)
4. Add an informative comment
5. Return a detailed result with all changes made

Always ensure all updates are properly formatted and maintain the story's integrity. Your goal is to 
improve story quality while preserving the original context and intent.
"""

# Input validation guardrail
@input_guardrail
async def validate_update_input(
    ctx: RunContextWrapper[WorkspaceContext], 
    agent: Agent, 
    input_data: str
) -> GuardrailFunctionOutput:
    """
    Validate the update input before processing.
    """
    logger.info("Validating update input")
    
    try:
        # Parse the input data
        data = json.loads(input_data) if isinstance(input_data, str) else input_data
        
        # Validate required fields
        required_fields = ["story_id", "workspace_id", "update_type"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        # Validate update_type
        valid_update_types = ["analysis", "enhancement"]
        if data.get("update_type") not in valid_update_types:
            error_message = f"Invalid update_type: {data.get('update_type')}, must be one of {valid_update_types}"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        # Validate that required result data is present based on update_type
        if data.get("update_type") == "analysis" and not data.get("analysis_result"):
            error_message = "Missing analysis_result for analysis update"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        if data.get("update_type") == "enhancement" and not data.get("enhancement_result"):
            error_message = "Missing enhancement_result for enhancement update"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        logger.info("Update input validation successful")
        return GuardrailFunctionOutput(
            output_info={"valid": True, "message": "Input validation successful"},
            tripwire_triggered=False
        )
    
    except json.JSONDecodeError:
        error_message = "Invalid JSON in input data"
        logger.error(error_message)
        return GuardrailFunctionOutput(
            output_info={"valid": False, "message": error_message},
            tripwire_triggered=True
        )
    except Exception as e:
        error_message = f"Validation error: {str(e)}"
        logger.error(error_message)
        return GuardrailFunctionOutput(
            output_info={"valid": False, "message": error_message},
            tripwire_triggered=True
        )


# Output validation guardrail
@output_guardrail
async def validate_update_output(
    ctx: RunContextWrapper[WorkspaceContext],
    agent: Agent,
    output: Any
) -> GuardrailFunctionOutput:
    """
    Validate the update output before returning it.
    """
    logger.info("Validating update output")
    
    try:
        # Validate output is an UpdateResult instance
        if not isinstance(output, UpdateResult):
            error_message = "Output must be an UpdateResult object"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        # Validate required fields
        if not output.story_id:
            error_message = "Missing story_id in output"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        if not output.workspace_id:
            error_message = "Missing workspace_id in output"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        # Validate update_type
        valid_update_types = ["analysis", "enhancement"]
        if output.update_type not in valid_update_types:
            error_message = f"Invalid update_type in output: {output.update_type}"
            logger.error(error_message)
            return GuardrailFunctionOutput(
                output_info={"valid": False, "message": error_message},
                tripwire_triggered=True
            )
        
        # If success is True, make sure we have some updated fields or tags
        if output.success:
            if not output.fields_updated and not output.tags_added and not output.comment_added:
                error_message = "Success reported but no fields updated, tags added, or comments added"
                logger.error(error_message)
                return GuardrailFunctionOutput(
                    output_info={"valid": False, "message": error_message},
                    tripwire_triggered=True
                )
        else:
            # If failure, make sure we have an error message
            if not output.error_message:
                error_message = "Failure reported but no error message provided"
                logger.error(error_message)
                return GuardrailFunctionOutput(
                    output_info={"valid": False, "message": error_message},
                    tripwire_triggered=True
                )
        
        logger.info("Update output validation successful")
        return GuardrailFunctionOutput(
            output_info={"valid": True, "message": "Output validation successful"},
            tripwire_triggered=False
        )
    
    except Exception as e:
        error_message = f"Output validation error: {str(e)}"
        logger.error(error_message)
        return GuardrailFunctionOutput(
            output_info={"valid": False, "message": error_message},
            tripwire_triggered=True
        )


class UpdateAgentHooks(AgentHooks):
    """Lifecycle hooks for the Update Agent."""
    
    async def pre_generation(self, context, agent, input_items):
        """Hook that runs before the agent generates a response."""
        logger.info("Starting Update Agent processing")
        
        if hasattr(context, "context") and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            logger.info(f"Processing update for story {workspace_context.story_id} in workspace {workspace_context.workspace_id}")
            
            # Restore trace context if it exists
            from utils.tracing import restore_handoff_context
            trace_ctx = restore_handoff_context(workspace_context)
            if trace_ctx:
                logger.info(f"Restored trace context from previous agent")
        
        return input_items
    
    async def post_generation(self, context, agent, response):
        """Hook that runs after the agent generates a response."""
        logger.info("Completed Update Agent processing")
        
        # Extract and store update results if available
        result = None
        for item in response.items:
            if item.type == "output_type" and hasattr(item, "value"):
                result = item.value
                break
        
        if result and hasattr(context, "context") and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            
            # Convert result to dict if it's not already
            result_dict = result if isinstance(result, dict) else (
                result.dict() if hasattr(result, "dict") else vars(result)
            )
            
            # Store the update results
            workspace_context.set_update_results({
                "result": result_dict,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store in local storage for persistence
            local_storage.save_task(
                workspace_context.workspace_id,
                workspace_context.story_id,
                {
                    "type": "update",
                    "result": result_dict,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Stored update results for story {workspace_context.story_id}")
            
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
            extra={"parameters": safe_params, "agent": "update"}
        )
        return function_call
    
    async def post_function_call(self, context, function_output):
        """Hook that runs after a function is called."""
        function_name = getattr(function_output, 'name', 'unknown')
        
        # Log without including potentially sensitive output
        output_type = type(getattr(function_output, 'output', None)).__name__
        logger.info(
            f"Function completed: {function_name}",
            extra={"output_type": output_type, "agent": "update"}
        )
        return function_output


def get_update_model() -> str:
    """Get the model to use for the Update Agent from configuration."""
    config = get_config()
    model_name = config.get("models", {}).get("update", "gpt-3.5-turbo")
    
    # Allow environment variable override
    return os.environ.get("MODEL_UPDATE", model_name)


def create_update_agent() -> Agent:
    """
    Create the Update Agent with the appropriate configuration.
    
    Returns:
        Configured Update Agent
    """
    model = get_update_model()
    logger.info(f"Creating Update Agent with model: {model}")
    
    # Create function tools for the agent
    function_tools = [
        FunctionTool(
            function=get_story,
            description="Get details of a Shortcut story"
        ),
        FunctionTool(
            function=update_story_content,
            description="Update the content of a Shortcut story (title, description, acceptance criteria)"
        ),
        FunctionTool(
            function=update_story_labels,
            description="Update the labels/tags on a Shortcut story"
        ),
        FunctionTool(
            function=add_update_comment,
            description="Add a comment to a Shortcut story with update information"
        ),
        FunctionTool(
            function=format_analysis_comment,
            description="Format analysis results into a structured comment"
        ),
        FunctionTool(
            function=format_enhancement_comment,
            description="Format enhancement results into a structured comment"
        )
    ]
    
    # Create the agent with proper OpenAI Agent SDK configuration
    agent = Agent(
        name="Update Agent",
        instructions=UPDATE_SYSTEM_MESSAGE,
        model=model,
        model_settings=ModelSettings(
            temperature=0.2,  # Low temperature for consistent, predictable responses
            response_format={"type": "json_object"}  # Ensure JSON output format
        ),
        tools=function_tools,
        hooks=UpdateAgentHooks(),
        guardrails=[
            {"tag": "validate_update_input", "function": validate_update_input},
            {"tag": "validate_update_output", "function": validate_update_output}
        ],
        output_type=OutputType(result_type=UpdateResult),
        handoffs=Handoffs(
            enabled=True,
            allow_all=False  # Update Agent is typically the final agent in the workflow
        )
    )
    
    return agent


async def process_update(
    workspace_context: WorkspaceContext,
    update_type: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a story update using the Update Agent.
    
    Args:
        workspace_context: Workspace context containing API key and IDs
        update_type: Type of update to perform ("analysis" or "enhancement")
        update_data: Data for the update (analysis or enhancement results)
        
    Returns:
        Update result dictionary
    """
    story_id = workspace_context.story_id
    workspace_id = workspace_context.workspace_id
    api_key = workspace_context.api_key
    request_id = workspace_context.request_id or str(uuid.uuid4())
    
    logger.info(f"Processing {update_type} update for story {story_id} in workspace {workspace_id}")
    
    try:
        # Verify the story exists
        story = await get_story(story_id, api_key)
        if not story:
            logger.error(f"Story {story_id} not found in workspace {workspace_id}")
            return {
                "success": False,
                "error_message": f"Story {story_id} not found",
                "story_id": story_id,
                "workspace_id": workspace_id,
                "update_type": update_type,
                "fields_updated": [],
                "tags_added": [],
                "tags_removed": [],
                "comment_added": False
            }
        
        # Prepare input for the Update Agent
        input_data = {
            "story_id": story_id,
            "workspace_id": workspace_id,
            "update_type": update_type
        }
        
        if update_type == "analysis":
            input_data["analysis_result"] = update_data
        else:  # enhancement
            input_data["enhancement_result"] = update_data
        
        # Create trace for the update process
        with trace(
            workflow_name="Story Update",
            group_id=f"{workspace_id}:{story_id}",
            trace_metadata={
                "request_id": request_id,
                "workspace_id": workspace_id,
                "story_id": story_id,
                "update_type": update_type
            }
        ):
            # Create the agent
            update_agent = create_update_agent()
            
            # For local development without the agent API,
            # fall back to the simplified implementation
            if os.environ.get("OPENAI_API_KEY") is None:
                logger.warning("OpenAI API key not found, using simplified update process")
                return await process_update_development(
                    story_id, workspace_id, api_key, update_type, update_data
                )
            
            # Run the agent with the OpenAI Agent SDK
            logger.info("Running Update Agent with OpenAI Agent SDK")
            
            try:
                # Convert input data to JSON string
                input_json = json.dumps(input_data)
                
                # Run the agent
                result = await Runner.run(
                    agent=update_agent,
                    input=input_json,
                    context=workspace_context
                )
                
                # Extract the result from the agent response
                update_result = None
                for item in result.items:
                    if item.type == "output_type" and hasattr(item, "value"):
                        update_result = item.value
                        break
                
                if update_result and isinstance(update_result, UpdateResult):
                    # Convert Pydantic model to dictionary
                    result_dict = update_result.dict()
                    
                    # Store results
                    workspace_context.set_update_results({
                        "result": result_dict,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Store in local storage
                    local_storage.save_task(
                        workspace_context.workspace_id,
                        workspace_context.story_id,
                        {
                            "type": "update",
                            "result": result_dict,
                            "timestamp": datetime.now().isoformat(),
                            "update_type": update_type
                        }
                    )
                    
                    logger.info(f"Update complete for story {story_id}")
                    return result_dict
                else:
                    # Fallback if we couldn't extract a proper result
                    logger.warning("Could not extract proper result from agent response")
                    return {
                        "success": True,
                        "story_id": story_id,
                        "workspace_id": workspace_id,
                        "update_type": update_type,
                        "fields_updated": [],
                        "tags_added": ["enhanced" if update_type == "enhancement" else "analysed"],
                        "tags_removed": ["enhance" if update_type == "enhancement" else "analyse"],
                        "comment_added": True,
                        "error_message": None
                    }
            except Exception as agent_error:
                logger.error(f"Error running Update Agent: {str(agent_error)}")
                # Fall back to simplified implementation
                logger.info("Falling back to simplified update process")
                return await process_update_development(
                    story_id, workspace_id, api_key, update_type, update_data
                )
    
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        return {
            "success": False,
            "error_message": str(e),
            "story_id": story_id,
            "workspace_id": workspace_id,
            "update_type": update_type,
            "fields_updated": [],
            "tags_added": [],
            "tags_removed": [],
            "comment_added": False
        }


async def process_update_development(
    story_id: str,
    workspace_id: str,
    api_key: str,
    update_type: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a story update in development mode (simplified implementation).
    
    Args:
        story_id: ID of the story to update
        workspace_id: ID of the workspace containing the story
        api_key: Shortcut API key
        update_type: Type of update to perform ("analysis" or "enhancement")
        update_data: Data for the update (analysis or enhancement results)
        
    Returns:
        Update result dictionary
    """
    logger.info(f"Processing {update_type} update in development mode")
    fields_updated = []
    
    try:
        # Different processing based on update type
        if update_type == "analysis":
            # For analysis updates, we just add a comment with the analysis results
            formatted_comment = await format_analysis_comment(update_data)
            comment_result = await add_update_comment(
                story_id, api_key, "analysis", formatted_comment
            )
            
            # Update tags - remove "analyse" and add "analysed"
            label_result = await update_story_labels(
                story_id, api_key, 
                labels_to_add=["analysed"],
                labels_to_remove=["analyse"]
            )
            
            return {
                "success": comment_result.get("success", False) and label_result.get("success", False),
                "story_id": story_id,
                "workspace_id": workspace_id,
                "update_type": "analysis",
                "fields_updated": [],
                "tags_added": label_result.get("added_labels", []),
                "tags_removed": label_result.get("removed_labels", []),
                "comment_added": comment_result.get("success", False),
                "error_message": None
            }
        
        else:  # enhancement
            # For enhancement updates, we update the story content and add a comment
            content_updates = {}
            
            # Apply content updates if available
            if update_data.get("enhanced_title"):
                content_updates["title"] = update_data["enhanced_title"]
                fields_updated.append("title")
            
            if update_data.get("enhanced_description"):
                content_updates["description"] = update_data["enhanced_description"]
                fields_updated.append("description")
            
            if update_data.get("enhanced_acceptance_criteria"):
                content_updates["acceptance_criteria"] = update_data["enhanced_acceptance_criteria"]
                fields_updated.append("acceptance_criteria")
            
            # Update the story content
            content_result = await update_story_content(
                story_id, api_key,
                title=content_updates.get("title"),
                description=content_updates.get("description"),
                acceptance_criteria=content_updates.get("acceptance_criteria")
            )
            
            # Format and add enhancement comment
            formatted_comment = await format_enhancement_comment(update_data)
            comment_result = await add_update_comment(
                story_id, api_key, "enhancement", formatted_comment
            )
            
            # Update tags - remove "enhance" and add "enhanced"
            label_result = await update_story_labels(
                story_id, api_key, 
                labels_to_add=["enhanced"],
                labels_to_remove=["enhance"]
            )
            
            return {
                "success": content_result.get("success", False) and comment_result.get("success", False) and label_result.get("success", False),
                "story_id": story_id,
                "workspace_id": workspace_id,
                "update_type": "enhancement",
                "fields_updated": content_result.get("fields_updated", []),
                "tags_added": label_result.get("added_labels", []),
                "tags_removed": label_result.get("removed_labels", []),
                "comment_added": comment_result.get("success", False),
                "error_message": None
            }
    
    except Exception as e:
        logger.error(f"Error in development update process: {str(e)}")
        return {
            "success": False,
            "error_message": str(e),
            "story_id": story_id,
            "workspace_id": workspace_id,
            "update_type": update_type,
            "fields_updated": [],
            "tags_added": [],
            "tags_removed": [],
            "comment_added": False
        }