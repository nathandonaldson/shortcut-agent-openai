"""
Analysis Agent for evaluating Shortcut stories.
"""

import os
import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

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
from tools.shortcut.shortcut_tools import get_story_details, add_comment
from shortcut_agents.analysis.models import (
    ComponentScore, 
    AnalysisResult, 
    AnalysisMetadata, 
    StoryAnalysisOutput
)
from shortcut_agents.analysis.tools import (
    analyze_title,
    analyze_description,
    analyze_acceptance_criteria,
    external_llm_analysis
)
from utils.storage.local_storage import local_storage
from config import get_config, is_development, is_production

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analysis_agent")

# Analysis agent system message
ANALYSIS_SYSTEM_MESSAGE = """
You are the Analysis Agent for a Shortcut story enhancement system. Your job is to:

1. Thoroughly evaluate Shortcut stories for quality, clarity, and completeness
2. Produce structured analysis with scores and specific recommendations
3. Identify priority areas for improvement

You have access to specialized analysis tools to help you evaluate different components:
- analyze_title: Evaluates the clarity and effectiveness of a story title
- analyze_description: Evaluates the completeness and quality of a story description
- analyze_acceptance_criteria: Assesses acceptance criteria if present
- external_llm_analysis: Uses external LLM for sophisticated analysis of specific content

When analyzing a story, follow these steps:
1. First, examine the overall story structure and content
2. Use the appropriate tools to analyze each component (title, description, acceptance criteria)
3. Prioritize the areas that need the most improvement
4. Provide specific, actionable recommendations for each area
5. Synthesize your findings into an overall analysis with numerical scores

Your analysis should be balanced, highlighting both strengths and weaknesses. Focus on providing constructive feedback that will help improve the story quality. Aim to be thorough but concise in your recommendations.

For scoring:
- 9-10: Exceptional quality, minimal improvements needed
- 7-8: Good quality, some minor improvements suggested
- 5-6: Acceptable quality, several improvements needed
- 3-4: Below average, significant improvements required
- 1-2: Poor quality, major revision recommended

After you complete your analysis, you should format your output as a structured AnalysisResult object.
"""

# Hook class for the Analysis Agent
class AnalysisAgentHooks(AgentHooks):
    """Hooks for the Analysis Agent lifecycle."""
    
    async def pre_generation(self, context, agent, input_items):
        """Hook that runs before the agent generates a response."""
        logger.info("Starting analysis process")
        
        if hasattr(context, "context") and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            
            # Restore trace context if it exists
            from utils.tracing import restore_handoff_context
            trace_ctx = restore_handoff_context(workspace_context)
            if trace_ctx:
                logger.info(f"Restored trace context from previous agent")
        
        return input_items
    
    async def post_generation(self, context, agent, response):
        """Hook that runs after the agent generates a response."""
        logger.info("Analysis completed")
        
        # Check if we have workspace context and analysis results
        if hasattr(context, 'context') and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            
            # Extract the analysis results if available
            analysis_result = None
            for item in response.items:
                if item.type == "output_type" and hasattr(item, "value"):
                    analysis_result = item.value
                    break
            
            # Store the results in the workspace context
            if analysis_result and isinstance(analysis_result, AnalysisResult):
                workspace_context.set_analysis_results({
                    "result": analysis_result.dict(),
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info(f"Stored analysis results for story {workspace_context.story_id}")
                
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
            extra={"parameters": safe_params, "agent": "analysis"}
        )
        return function_call
    
    async def post_function_call(self, context, function_output):
        """Hook that runs after a function is called."""
        function_name = getattr(function_output, 'name', 'unknown')
        
        # Log without including potentially sensitive output
        output_type = type(getattr(function_output, 'output', None)).__name__
        logger.info(
            f"Function completed: {function_name}",
            extra={"output_type": output_type, "agent": "analysis"}
        )
        return function_output


# Input validation guardrail
@input_guardrail
async def validate_story_input(ctx, agent, input):
    """Validate the story data before processing."""
    if not isinstance(input, dict):
        return GuardrailFunctionOutput(
            output_info="Input must be a dictionary containing story data",
            tripwire_triggered=True
        )
    
    # Check for required fields
    required_fields = ["id", "name", "description"]
    missing_fields = [field for field in required_fields if field not in input]
    
    if missing_fields:
        return GuardrailFunctionOutput(
            output_info=f"Story data missing required fields: {', '.join(missing_fields)}",
            tripwire_triggered=True
        )
    
    # Additional validation can be added here
    
    return GuardrailFunctionOutput(
        output_info="Story data validated successfully",
        tripwire_triggered=False
    )

# Output validation guardrail
@output_guardrail
async def validate_analysis_output(ctx, agent, output):
    """Validate the analysis output before returning it."""
    # Ensure we have a valid output
    if not isinstance(output, AnalysisResult):
        return GuardrailFunctionOutput(
            output_info="Output must be an AnalysisResult object",
            tripwire_triggered=True
        )
    
    # Validate score ranges
    if not (1 <= output.overall_score <= 10):
        return GuardrailFunctionOutput(
            output_info="Overall score must be between 1 and 10",
            tripwire_triggered=True
        )
    
    if not (1 <= output.title_score <= 10):
        return GuardrailFunctionOutput(
            output_info="Title score must be between 1 and 10",
            tripwire_triggered=True
        )
    
    if not (1 <= output.description_score <= 10):
        return GuardrailFunctionOutput(
            output_info="Description score must be between 1 and 10",
            tripwire_triggered=True
        )
    
    # Validate acceptance criteria score if provided
    if output.acceptance_criteria_score is not None and not (1 <= output.acceptance_criteria_score <= 10):
        return GuardrailFunctionOutput(
            output_info="Acceptance criteria score must be between 1 and 10",
            tripwire_triggered=True
        )
    
    # Validate recommendations and priority areas
    if not output.recommendations:
        return GuardrailFunctionOutput(
            output_info="At least one recommendation must be provided",
            tripwire_triggered=True
        )
    
    if not output.priority_areas:
        return GuardrailFunctionOutput(
            output_info="At least one priority area must be provided",
            tripwire_triggered=True
        )
    
    return GuardrailFunctionOutput(
        output_info="Analysis output validated successfully",
        tripwire_triggered=False
    )


def get_analysis_model() -> str:
    """Get the model to use for the analysis agent based on configuration."""
    config = get_config()
    model_name = config.get("models", {}).get("analysis", "gpt-3.5-turbo")
    
    # Allow environment variable override
    return os.environ.get("MODEL_ANALYSIS", model_name)


def create_analysis_agent():
    """Create and configure the Analysis Agent."""
    model = get_analysis_model()
    logger.info(f"Creating analysis agent with model: {model}")
    
    # Create function tools
    function_tools = [
        FunctionTool(
            function=analyze_title,
            description="Analyze a story title for clarity, effectiveness, and quality",
        ),
        FunctionTool(
            function=analyze_description,
            description="Analyze a story description for completeness, structure, and quality",
        ),
        FunctionTool(
            function=analyze_acceptance_criteria,
            description="Analyze acceptance criteria if present in the story",
        ),
        FunctionTool(
            function=external_llm_analysis,
            description="Use an external LLM for sophisticated analysis of specific content",
        ),
    ]
    
    # Agent configuration
    agent = Agent(
        name="Analysis Agent",
        instructions=ANALYSIS_SYSTEM_MESSAGE,
        model=model,
        model_settings=ModelSettings(
            temperature=0.3,  # Low temperature for consistent analysis
            response_format={"type": "json_object"}  # Ensure JSON output format
        ),
        tools=function_tools,
        hooks=AnalysisAgentHooks(),
        guardrails=[
            {"tag": "validate_story_input", "function": validate_story_input},
            {"tag": "validate_analysis_output", "function": validate_analysis_output}
        ],
        output_type={'result_type': AnalysisResult},
        # Define handoffs to specific agents only
        handoffs=Handoff(
            enabled=True,
            allow=["Update Agent"]  # Only allow handoff to Update Agent
        )
    )
    
    return agent


async def process_analysis(story_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a story for analysis.
    
    Args:
        story_data: The story data to analyze
        workspace_context: The workspace context
        
    Returns:
        Analysis results
    """
    story_id = str(story_data.get('id', ''))
    workspace_id = workspace_context.workspace_id
    request_id = workspace_context.request_id or f"analysis_{int(time.time())}"
    
    logger.info(f"Analyzing story {story_id} for workspace {workspace_id}")
    
    # Create trace for the analysis process
    with trace(
        workflow_name="Story Analysis",
        group_id=f"{workspace_id}:{story_id}",
        trace_metadata={
            "request_id": request_id,
            "workspace_id": workspace_id,
            "story_id": story_id
        }
    ):
        # Create the analysis agent
        analysis_agent = create_analysis_agent()
        
        # For environments without OpenAI API key, use simplified logic
        if os.environ.get("OPENAI_API_KEY") is None or is_development():
            logger.info("Using simplified analysis for development")
            return await process_analysis_simplified(story_data, workspace_context)
        
        try:
            # Prepare input for the Analysis Agent
            logger.info("Running Analysis Agent with OpenAI Agent SDK")
            
            # Convert story data to JSON string
            input_json = json.dumps(story_data)
            
            # Run the agent with the OpenAI Agent SDK
            result = await Runner.run(
                agent=analysis_agent,
                input=input_json,
                context=workspace_context
            )
            
            # Extract the analysis result
            analysis_result = None
            for item in result.items:
                if item.type == "output_type" and hasattr(item, "value"):
                    analysis_result = item.value
                    break
            
            if analysis_result and isinstance(analysis_result, AnalysisResult):
                # Convert to dictionary
                result_dict = analysis_result.dict()
                
                # Store the analysis results in the workspace context
                workspace_context.set_analysis_results({
                    "result": result_dict,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Create metadata
                metadata = {
                    "workspace_id": workspace_id,
                    "story_id": story_id,
                    "timestamp": datetime.now().isoformat(),
                    "model_used": get_analysis_model(),
                    "version": "1.0"
                }
                
                # Store in local storage
                local_storage.save_task(
                    workspace_id,
                    story_id,
                    {
                        "type": "analysis",
                        "result": result_dict,
                        "metadata": metadata,
                        "raw_story": story_data
                    }
                )
                
                logger.info(f"Analysis complete for story {story_id}")
                
                # Return the analysis results
                return {
                    "status": "success",
                    "workflow": "analysis",
                    "story_id": story_id,
                    "workspace_id": workspace_id,
                    "analysis": {
                        "result": result_dict,
                        "metadata": metadata
                    }
                }
            else:
                # Fallback to simplified implementation
                logger.warning("Could not extract analysis result, falling back to simplified implementation")
                return await process_analysis_simplified(story_data, workspace_context)
        
        except Exception as e:
            logger.error(f"Error running Analysis Agent: {str(e)}")
            return await process_analysis_simplified(story_data, workspace_context)


async def process_analysis_simplified(story_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a story for analysis using simplified logic.
    
    Args:
        story_data: The story data to analyze
        workspace_context: The workspace context
        
    Returns:
        Analysis results
    """
    story_id = str(story_data.get('id', ''))
    workspace_id = workspace_context.workspace_id
    
    logger.info(f"Using simplified analysis for story {story_id}")
    
    # Create a simple analysis result
    analysis_result = {
        "overall_score": 7,
        "title_score": 8,
        "description_score": 6,
        "acceptance_criteria_score": 5 if "## Acceptance Criteria" in story_data.get("description", "") else None,
        "recommendations": [
            "Add more context to the title",
            "Include more detailed requirements in the description",
            "Add background context to help understand the purpose",
            "Make acceptance criteria more specific with testable outcomes"
        ],
        "priority_areas": [
            "Improve description detail", 
            "Add acceptance criteria", 
            "Clarify expected outcomes"
        ]
    }
    
    # Store the analysis results in the workspace context
    workspace_context.set_analysis_results({
        "result": analysis_result,
        "timestamp": datetime.now().isoformat(),
    })
    
    # Create metadata
    metadata = {
        "workspace_id": workspace_id,
        "story_id": story_id,
        "timestamp": datetime.now().isoformat(),
        "model_used": "simplified",
        "version": "1.0"
    }
    
    # Store in local storage
    local_storage.save_task(
        workspace_id,
        story_id,
        {
            "type": "analysis",
            "result": analysis_result,
            "metadata": metadata,
            "raw_story": story_data
        }
    )
    
    logger.info(f"Simplified analysis complete for story {story_id}")
    
    # Return the analysis results
    return {
        "status": "success",
        "workflow": "analysis",
        "story_id": story_id,
        "workspace_id": workspace_id,
        "analysis": {
            "result": analysis_result,
            "metadata": metadata
        }
    }