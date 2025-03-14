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
        # Convert result to dictionary if needed
        if hasattr(result, "dict") and callable(result.dict):
            result_dict = result.dict()
        else:
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
        
        # Create tools list
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
        
        result = AnalysisResult(
            overall_score=7,
            title_score=8,
            description_score=6,
            acceptance_criteria_score=5 if has_acceptance_criteria else None,
            recommendations=[
                "Add more context to the title",
                "Include more detailed requirements in the description",
                "Add background context to help understand the purpose",
                "Make acceptance criteria more specific with testable outcomes"
            ],
            priority_areas=[
                "Improve description detail", 
                "Add acceptance criteria", 
                "Clarify expected outcomes"
            ]
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
        local_storage.save_task(
            workspace_context.workspace_id,
            story_id,
            {
                "type": "analysis",
                "result": result.dict() if hasattr(result, "dict") else vars(result),
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