"""
Function tools for the Analysis Agent.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import OpenAI
# Import RunContextWrapper directly from base_agent
from shortcut_agents.base_agent import RunContextWrapper

from context.workspace.workspace_context import WorkspaceContext
from shortcut_agents.analysis.models import ComponentScore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analysis_tools")


async def analyze_title(ctx: RunContextWrapper[WorkspaceContext], title: str) -> ComponentScore:
    """
    Analyze the effectiveness and clarity of a story title.
    
    Args:
        ctx: Run context with workspace context
        title: The story title to analyze
        
    Returns:
        ComponentScore object with title analysis
    """
    logger.info(f"Analyzing title: {title}")
    
    # In a real implementation, this could use more sophisticated analysis
    # For demonstration purposes, we'll use a simplified approach
    
    strengths = []
    weaknesses = []
    recommendations = []
    
    # Basic title analysis
    if len(title) < 5:
        weaknesses.append("Title is too short")
        recommendations.append("Expand the title to be more descriptive")
    else:
        strengths.append("Title has adequate length")
    
    if len(title) > 80:
        weaknesses.append("Title is excessively long")
        recommendations.append("Shorten the title to be more concise (aim for 50-80 characters)")
    
    # Check for clarity indicators
    if any(term in title.lower() for term in ["add", "create", "implement", "fix", "update", "enhance"]):
        strengths.append("Title includes a clear action verb")
    else:
        weaknesses.append("Title lacks a clear action verb")
        recommendations.append("Start the title with a clear action verb (e.g., Add, Create, Fix)")
    
    # Check for specificity
    if all(term not in title.lower() for term in ["thing", "stuff", "etc", "issue", "bug", "problem", "feature"]):
        strengths.append("Title avoids vague terms")
    else:
        weaknesses.append("Title contains vague or generic terms")
        recommendations.append("Replace vague terms with specific descriptions of what's being changed")
    
    # Calculate score based on strengths/weaknesses
    base_score = 7  # Starting point
    score = base_score + len(strengths) - len(weaknesses)
    
    # Ensure score is within bounds
    score = max(1, min(10, score))
    
    # Ensure we have some recommendations
    if not recommendations and score < 9:
        recommendations.append("Consider adding more context to the title")
    
    return ComponentScore(
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations
    )


async def analyze_description(ctx: RunContextWrapper[WorkspaceContext], description: str) -> ComponentScore:
    """
    Analyze the completeness and quality of a story description.
    
    Args:
        ctx: Run context with workspace context
        description: The story description to analyze
        
    Returns:
        ComponentScore object with description analysis
    """
    logger.info("Analyzing story description")
    
    strengths = []
    weaknesses = []
    recommendations = []
    
    # Basic length analysis
    word_count = len(description.split())
    if word_count < 10:
        weaknesses.append("Description is too brief")
        recommendations.append("Expand the description to provide more context and detail")
    elif word_count < 50:
        weaknesses.append("Description is somewhat brief")
        recommendations.append("Consider adding more detail to the description")
    else:
        strengths.append("Description has good length")
    
    # Check for structure elements
    if "## Background" in description or "## Context" in description:
        strengths.append("Description includes context/background section")
    else:
        weaknesses.append("Description lacks explicit context/background section")
        recommendations.append("Add a '## Background' or '## Context' section to provide necessary background")
    
    if "## Requirements" in description or "## Acceptance Criteria" in description:
        strengths.append("Description includes requirements or acceptance criteria section")
    else:
        weaknesses.append("Description lacks explicit requirements section")
        recommendations.append("Add a '## Requirements' or '## Acceptance Criteria' section")
    
    # Check for clarity elements
    if "screenshot" in description.lower() or "image" in description.lower() or "![" in description:
        strengths.append("Description includes visual elements (screenshots/images)")
    else:
        # Not always necessary, so just a suggestion
        recommendations.append("Consider adding screenshots or diagrams if applicable")
    
    if any(link in description for link in ["http://", "https://", "www."]):
        strengths.append("Description includes relevant links")
    
    # Calculate score based on strengths/weaknesses
    base_score = 6  # Starting point
    score = base_score + len(strengths) - len(weaknesses)
    
    # Ensure score is within bounds
    score = max(1, min(10, score))
    
    return ComponentScore(
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations
    )


async def analyze_acceptance_criteria(
    ctx: RunContextWrapper[WorkspaceContext], 
    description: str
) -> Optional[ComponentScore]:
    """
    Analyze the acceptance criteria if present in the story.
    
    Args:
        ctx: Run context with workspace context
        description: The story description to extract and analyze acceptance criteria
        
    Returns:
        ComponentScore object with acceptance criteria analysis or None if not present
    """
    logger.info("Analyzing acceptance criteria")
    
    # Check if acceptance criteria exists in the description
    ac_indicators = ["## Acceptance Criteria", "## AC", "## Criteria", "## Requirements"]
    
    has_ac = False
    ac_content = ""
    
    for indicator in ac_indicators:
        if indicator in description:
            has_ac = True
            parts = description.split(indicator, 1)
            if len(parts) > 1:
                # Get the content after the AC header up to the next header (if any)
                ac_section = parts[1]
                next_header = next((i for i in range(len(ac_section)) if i > 0 and ac_section[i-1:i+1] == "\n#"), None)
                if next_header:
                    ac_content = ac_section[:next_header].strip()
                else:
                    ac_content = ac_section.strip()
                break
    
    if not has_ac:
        return None
    
    # Now analyze the acceptance criteria
    strengths = []
    weaknesses = []
    recommendations = []
    
    # Check formatting (bullets/numbers)
    if any(line.strip().startswith(("-", "*", "1.", "2.")) for line in ac_content.split("\n")):
        strengths.append("Acceptance criteria uses clear bullet or numbered points")
    else:
        weaknesses.append("Acceptance criteria lacks clear bullet or numbered points")
        recommendations.append("Format acceptance criteria as bullet points or numbered list for clarity")
    
    # Check for testable outcomes
    testable_phrases = ["should", "must", "will", "can", "displays", "shows", "validates", "accepts", "rejects"]
    if any(phrase in ac_content.lower() for phrase in testable_phrases):
        strengths.append("Acceptance criteria includes testable outcomes")
    else:
        weaknesses.append("Acceptance criteria lacks clearly defined testable outcomes")
        recommendations.append("Include specific, testable outcomes in each acceptance criterion")
    
    # Check for completeness
    ac_lines = [line for line in ac_content.split("\n") if line.strip() and not line.strip().startswith("#")]
    if len(ac_lines) < 2:
        weaknesses.append("Acceptance criteria seems incomplete with only one criterion")
        recommendations.append("Consider adding more acceptance criteria to fully define done")
    else:
        strengths.append(f"Acceptance criteria has {len(ac_lines)} defined items")
    
    # Calculate score
    base_score = 6
    score = base_score + len(strengths) - len(weaknesses)
    score = max(1, min(10, score))
    
    return ComponentScore(
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations
    )


async def external_llm_analysis(
    ctx: RunContextWrapper[WorkspaceContext], 
    content: str, 
    analysis_type: str,
    model_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use an external LLM API for more sophisticated analysis.
    
    Args:
        ctx: Run context with workspace context
        content: The content to analyze
        analysis_type: The type of analysis to perform (e.g., "completeness", "clarity")
        model_override: Optional model to use instead of the default
        
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"Performing external LLM analysis for {analysis_type}")
    
    # In development mode, we'll use a mock response
    from config import is_development
    if is_development():
        logger.info("Using mock LLM response in development mode")
        time.sleep(0.5)  # Simulate API delay
        
        # Return mock response based on analysis type
        if analysis_type == "completeness":
            return {
                "score": 7,
                "findings": [
                    "Content covers the main requirements",
                    "Missing specific implementation details",
                    "Would benefit from more examples"
                ],
                "recommendations": [
                    "Add implementation details",
                    "Include examples of expected behavior"
                ]
            }
        elif analysis_type == "clarity":
            return {
                "score": 8,
                "findings": [
                    "Content is generally clear and well-structured",
                    "Some technical terms used without explanation",
                    "Good use of formatting to separate concerns"
                ],
                "recommendations": [
                    "Define technical terms on first use",
                    "Consider adding a glossary section for complex terms"
                ]
            }
        else:
            return {
                "score": 6,
                "findings": [
                    "Basic analysis completed",
                    "Content needs improvement"
                ],
                "recommendations": [
                    "Review and enhance the content"
                ]
            }
    
    # In production, we'd use the actual OpenAI API
    try:
        # Get the API key from the context
        api_key = ctx.context.api_key if hasattr(ctx, 'context') and hasattr(ctx.context, 'api_key') else None
        
        # Use environment OpenAI API key if not found in context
        client = OpenAI()
        
        # Select model based on configuration or override
        from config import get_config
        config = get_config()
        default_model = config.get("models", {}).get("analysis", "gpt-3.5-turbo")
        model = model_override or default_model
        
        # Create the analysis prompt based on analysis type
        if analysis_type == "completeness":
            prompt = f"""
            Analyze the following content for completeness:
            
            {content}
            
            Provide an analysis with:
            1. A score from 1-10 on completeness
            2. Key findings about what's present and what's missing
            3. Specific recommendations for improving completeness
            
            Format your response as a JSON object with 'score', 'findings', and 'recommendations' keys.
            """
        elif analysis_type == "clarity":
            prompt = f"""
            Analyze the following content for clarity and readability:
            
            {content}
            
            Provide an analysis with:
            1. A score from 1-10 on clarity
            2. Key findings about clarity strengths and weaknesses
            3. Specific recommendations for improving clarity
            
            Format your response as a JSON object with 'score', 'findings', and 'recommendations' keys.
            """
        else:
            prompt = f"""
            Analyze the following content:
            
            {content}
            
            Provide a general analysis with:
            1. A quality score from 1-10
            2. Key findings
            3. Specific recommendations for improvement
            
            Format your response as a JSON object with 'score', 'findings', and 'recommendations' keys.
            """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert content analyzer who provides structured feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Ensure expected keys exist
        if "score" not in result:
            result["score"] = 5
        if "findings" not in result:
            result["findings"] = ["Analysis completed"]
        if "recommendations" not in result:
            result["recommendations"] = ["Review the content"]
            
        return result
        
    except Exception as e:
        logger.error(f"Error in external LLM analysis: {str(e)}")
        # Return a fallback result
        return {
            "score": 5,
            "findings": [f"Error in analysis: {str(e)}"],
            "recommendations": ["Try again later or contact support"]
        }