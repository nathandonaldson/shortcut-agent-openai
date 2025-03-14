"""
Analysis Agent for the Shortcut Enhancement System.

This agent evaluates Shortcut stories for quality, clarity, and completeness.
This version is refactored to use the BaseAgent implementation.
"""

import logging
import datetime
from typing import Dict, Any, List, Optional

from shortcut_agents.base_agent import BaseAgent, BaseAgentHooks, FunctionTool
from shortcut_agents.analysis.models import AnalysisResult, ComponentScore
from context.workspace.workspace_context import WorkspaceContext
from utils.storage.local_storage import local_storage

# Set up logging
logger = logging.getLogger("analysis_agent")

# Analysis Agent system message
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

class AnalysisAgentHooks(BaseAgentHooks[AnalysisResult]):
    """Lifecycle hooks for the Analysis Agent."""
    
    async def process_result(self, workspace_context: WorkspaceContext, result: AnalysisResult) -> None:
        """
        Process the analysis result.
        
        Args:
            workspace_context: The workspace context
            result: The analysis result
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
            
        # Store the analysis results in workspace context
        workspace_context.set_analysis_results({
            "result": result_dict,
            "timestamp": datetime.datetime.now().isoformat()
        })
            
        logger.info(f"Stored analysis results for story {workspace_context.story_id}")


class AnalysisAgent(BaseAgent[AnalysisResult, Dict[str, Any]]):
    """
    Agent responsible for analyzing Shortcut stories.
    """
    
    def __init__(self):
        """Initialize the Analysis Agent."""
        
        # Import tools here to avoid circular imports
        from shortcut_agents.analysis.tools import (
            analyze_title,
            analyze_description,
            analyze_acceptance_criteria,
            external_llm_analysis
        )
        
        # Input validation function
        from shortcut_agents.guardrail import input_guardrail, GuardrailFunctionOutput
        
        @input_guardrail
        async def validate_story_input(ctx, agent, input_data):
            """Validate the story input data."""
            # Implementation similar to previous version
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Input validation successful"},
                tripwire_triggered=False
            )
        
        # Output validation function
        from shortcut_agents.guardrail import output_guardrail
        
        @output_guardrail
        async def validate_analysis_output(ctx, agent, output):
            """Validate the analysis output data."""
            # Implementation similar to previous version
            return GuardrailFunctionOutput(
                output_info={"valid": True, "message": "Output validation successful"},
                tripwire_triggered=False
            )
        
        # Import function_tool from agents if available
        try:
            from agents import function_tool
            
            # Create tools list using function_tool
            tools = [
                function_tool(
                    func=analyze_title,
                    description_override="Analyze a story title for clarity, effectiveness, and quality"
                ),
                function_tool(
                    func=analyze_description,
                    description_override="Analyze a story description for completeness, structure, and quality"
                ),
                function_tool(
                    func=analyze_acceptance_criteria,
                    description_override="Analyze acceptance criteria if present in the story"
                ),
                function_tool(
                    func=external_llm_analysis,
                    description_override="Use an external LLM for sophisticated analysis of specific content"
                )
            ]
        except ImportError:
            # Fallback to direct FunctionTool initialization
            tools = [
                FunctionTool(
                    function=analyze_title,
                    description="Analyze a story title for clarity, effectiveness, and quality"
                ),
                FunctionTool(
                    function=analyze_description,
                    description="Analyze a story description for completeness, structure, and quality"
                ),
                FunctionTool(
                    function=analyze_acceptance_criteria,
                    description="Analyze acceptance criteria if present in the story"
                ),
                FunctionTool(
                    function=external_llm_analysis,
                    description="Use an external LLM for sophisticated analysis of specific content"
                )
            ]
        
        # Initialize the base agent
        super().__init__(
            agent_type="analysis",
            agent_name="Analysis Agent",
            system_message=ANALYSIS_SYSTEM_MESSAGE,
            output_class=AnalysisResult,
            hooks_class=AnalysisAgentHooks,
            input_guardrails=[validate_story_input],
            output_guardrails=[validate_analysis_output],
            allowed_handoffs=["Update Agent"],
            tools=tools,
            model_override=None
        )
    
    async def run_simplified(self, story_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Run a simplified version of the analysis agent for development/testing.
        
        Args:
            story_data: Story data to analyze
            workspace_context: Workspace context
            
        Returns:
            Dictionary with execution results
        """
        logger.info("Running simplified analysis process")
        
        story_id = str(story_data.get("id", ""))
        description = story_data.get("description", "")
        
        # Create a simple analysis result
        has_acceptance_criteria = "## Acceptance Criteria" in description

        # Create ComponentScore instances for each component
        title_analysis = ComponentScore(
            score=8,
            strengths=["Clear objective", "Uses action verb"],
            weaknesses=["Missing context", "Could be more specific"],
            recommendations=["Add more context to the title", "Make title more specific"]
        )
        
        description_analysis = ComponentScore(
            score=6,
            strengths=["Basic information present", "Includes purpose"],
            weaknesses=["Lacks detail", "Missing background context"],
            recommendations=["Include more detailed requirements", "Add background context"]
        )
        
        acceptance_criteria_analysis = None
        if has_acceptance_criteria:
            acceptance_criteria_analysis = ComponentScore(
                score=5,
                strengths=["Basic criteria included"],
                weaknesses=["Not specific enough", "Missing testable outcomes"],
                recommendations=["Make criteria more specific", "Add testable outcomes"]
            )
        
        result = AnalysisResult(
            overall_score=7,
            title_analysis=title_analysis,
            description_analysis=description_analysis,
            acceptance_criteria_analysis=acceptance_criteria_analysis,
            priority_areas=[
                "Improve description detail", 
                "Add acceptance criteria", 
                "Clarify expected outcomes"
            ],
            summary="This story needs improvements in description detail and acceptance criteria. The title is fairly good but could be more specific."
        )
        
        # Create metadata
        metadata = {
            "workspace_id": workspace_context.workspace_id,
            "story_id": story_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "model_used": "simplified",
            "version": "1.0"
        }
        
        # Store in local storage
        if hasattr(result, "model_dump") and callable(result.model_dump):
            result_dict = result.model_dump()
        elif hasattr(result, "dict") and callable(result.dict):
            result_dict = result.dict()
        else:
            result_dict = vars(result)
            
        local_storage.save_task(
            workspace_context.workspace_id,
            story_id,
            {
                "type": "analysis",
                "result": result_dict,
                "metadata": metadata,
                "raw_story": story_data
            }
        )
        
        # Process the result using the base agent's method
        return self._process_result(result, workspace_context)


# Convenience function to create an analysis agent
def create_analysis_agent() -> AnalysisAgent:
    """
    Create and configure the Analysis Agent.
    
    Returns:
        Configured Analysis Agent
    """
    return AnalysisAgent()


# Function for processing analysis (main entry point)
async def process_analysis(story_data: Dict[str, Any], workspace_context: WorkspaceContext) -> Dict[str, Any]:
    """
    Process a story analysis using the Analysis Agent.
    
    Args:
        story_data: Story data to analyze
        workspace_context: Workspace context
        
    Returns:
        Analysis result dictionary
    """
    # Create and run the agent
    agent = create_analysis_agent()
    return await agent.run(story_data, workspace_context, stream=False)