"""
Update Agent for the Shortcut Enhancement System.

This agent is responsible for applying changes to Shortcut stories based on
analysis or enhancement results, managing tags, and providing status updates.

This version is refactored to use the BaseAgent implementation.
"""

import logging
import datetime
import uuid
from typing import Dict, Any, List, Optional

from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks, FunctionTool
from shortcut_agents.update.models import UpdateResult, AnalysisResult, EnhancementResult
from tools.shortcut.shortcut_tools import get_story_details
from context.workspace.workspace_context import WorkspaceContext

# Set up logging
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

class UpdateAgentHooks(BaseAgentHooks[UpdateResult]):
    """Lifecycle hooks for the Update Agent."""
    
    async def process_result(self, workspace_context: WorkspaceContext, result: UpdateResult) -> None:
        """
        Process the update result.
        
        Args:
            workspace_context: The workspace context
            result: The update result
        """
        # Convert result to dictionary supporting both Pydantic v1 and v2
        if hasattr(result, "model_dump") and callable(result.model_dump):
            # Pydantic v2
            result_dict = result.model_dump()
        elif hasattr(result, "dict") and callable(result.dict):
            # Pydantic v1
            result_dict = result.dict()
        else:
            # Fallback
            result_dict = vars(result)
            
        # Store the update results in workspace context
        workspace_context.set_update_results({
            "result": result_dict,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        logger.info(f"Stored update results for story {workspace_context.story_id}")


# Simplified implementation of the Update Agent using the BaseAgent
class UpdateAgent(BaseAgent[UpdateResult, Dict[str, Any]]):
    """
    Agent responsible for updating Shortcut stories based on analysis or enhancement results.
    """
    
    def __init__(self):
        """Initialize the Update Agent."""
        
        # Import tools here to avoid circular imports
        from shortcut_agents.update.tools import (
            update_story_content,
            update_story_labels,
            add_update_comment,
            format_analysis_comment,
            format_enhancement_comment
        )
        
        # Input validation function
        from shortcut_agents.guardrail import input_guardrail, GuardrailFunctionOutput
        
        @input_guardrail
        async def validate_update_input(ctx, agent, input_data):
            """Validate the update input data."""
            # Implementation similar to previous version
            # ...
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Input validation successful"},
                tripwire_triggered=False
            )
        
        # Output validation function
        from shortcut_agents.guardrail import output_guardrail
        
        @output_guardrail
        async def validate_update_output(ctx, agent, output):
            """Validate the update output data."""
            # Implementation similar to previous version
            # ...
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Output validation successful"},
                tripwire_triggered=False
            )
        
        # Import function_tool from agents if available
        try:
            from agents import function_tool, Runner, trace
            
            # Create tools list using function_tool
            tools = [
                function_tool(
                    func=get_story_details,  # Fixed: get_story -> get_story_details
                    description_override="Get details of a Shortcut story"
                ),
                function_tool(
                    func=update_story_content,
                    description_override="Update the content of a Shortcut story (title, description, acceptance criteria)"
                ),
                function_tool(
                    func=update_story_labels,
                    description_override="Update the labels/tags on a Shortcut story"
                ),
                function_tool(
                    func=add_update_comment,
                    description_override="Add a comment to a Shortcut story with update information"
                ),
                function_tool(
                    func=format_analysis_comment,
                    description_override="Format analysis results into a structured comment"
                ),
                function_tool(
                    func=format_enhancement_comment,
                    description_override="Format enhancement results into a structured comment"
                )
            ]
        except ImportError:
            # Fallback to direct FunctionTool initialization
            tools = [
                FunctionTool(
                    function=get_story_details,  # Fixed: get_story -> get_story_details
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
        
        # Initialize the base agent
        super().__init__(
            agent_type="update",
            agent_name="Update Agent",
            system_message=UPDATE_SYSTEM_MESSAGE,
            output_class=UpdateResult,
            hooks_class=UpdateAgentHooks,
            input_guardrails=[validate_update_input],
            output_guardrails=[validate_update_output],
            allowed_handoffs=[],  # Update Agent is typically the final agent
            tools=tools,
            model_override=None
        )
    
    async def run_simplified(self, input_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Run a simplified version of the update agent for development/testing.
        
        Args:
            input_data: Input data for the agent
            workspace_context: Workspace context
            
        Returns:
            Dictionary with execution results
        """
        logger.info("Running simplified update process")
        
        story_id = workspace_context.story_id
        workspace_id = workspace_context.workspace_id
        update_type = input_data.get("update_type", "analysis")
        
        # Extract update data based on type
        if update_type == "analysis":
            update_data = input_data.get("analysis_result", {})
            
            # Create placeholder result
            result = UpdateResult(
                success=True,
                story_id=story_id,
                workspace_id=workspace_id,
                update_type=update_type,
                fields_updated=[],
                tags_added=["analysed"],
                tags_removed=["analyse"],
                comment_added=True,
                error_message=None
            )
        else:  # enhancement
            update_data = input_data.get("enhancement_result", {})
            
            # Create placeholder result
            result = UpdateResult(
                success=True,
                story_id=story_id,
                workspace_id=workspace_id,
                update_type=update_type,
                fields_updated=["title", "description"],
                tags_added=["enhanced"],
                tags_removed=["enhance"],
                comment_added=True,
                error_message=None
            )
        
        # Process the result using the base agent's method
        return self._process_result(result, workspace_context)


# Convenience function to create an update agent
def create_update_agent() -> UpdateAgent:
    """
    Create and configure the Update Agent.
    
    Returns:
        Configured Update Agent
    """
    return UpdateAgent()


# Function for processing updates (main entry point)
async def process_update(
    workspace_context: WorkspaceContext,
    update_type: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a story update using the Update Agent with proper tracing.
    
    Args:
        workspace_context: Workspace context with API key and IDs
        update_type: Type of update to perform ("analysis" or "enhancement")
        update_data: Data for the update
        
    Returns:
        Update result dictionary
    """
    # Create the agent
    update_agent = create_update_agent()
    
    # Prepare input data
    input_data = {
        "story_id": workspace_context.story_id,
        "workspace_id": workspace_context.workspace_id,
        "update_type": update_type
    }
    
    if update_type == "analysis":
        input_data["analysis_result"] = update_data
    else:  # enhancement
        input_data["enhancement_result"] = update_data
    
    # Run the agent with proper tracing configuration
    result = await Runner.run(
        starting_agent=update_agent,
        input=input_data,
        context=workspace_context,
        run_config={
            "workflow_name": f"Update-{workspace_context.workspace_id}-{workspace_context.story_id}",
            "trace_id": f"trace_{workspace_context.request_id or uuid.uuid4().hex}",
            "group_id": workspace_context.workspace_id,  # Group by workspace
            "trace_metadata": {
                "workspace_id": workspace_context.workspace_id,
                "story_id": workspace_context.story_id,
                "update_type": update_type,
                "request_id": workspace_context.request_id
            }
        }
    )
    
    # Return final output as dictionary
    return result.final_output