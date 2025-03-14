"""
Agent logging utilities for the Shortcut Enhancement System.
"""

import os
import json
from typing import Dict, Any, Optional, List, Callable

from utils.logging.logger import get_logger, trace_context

# Create loggers for different agent types
triage_logger = get_logger("triage.agent")
analysis_logger = get_logger("analysis.agent")
generation_logger = get_logger("generation.agent")
update_logger = get_logger("update.agent")
comment_logger = get_logger("comment.agent")
notification_logger = get_logger("notification.agent")

def log_agent_start(agent_type: str,
                   agent_name: str,
                   request_id: str,
                   workspace_id: str,
                   story_id: str,
                   model: Optional[str] = None,
                   agent_version: Optional[str] = None) -> None:
    """
    Log the start of an agent's execution.
    
    Args:
        agent_type: Type of agent (triage, analysis, etc.)
        agent_name: Name of the agent
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        model: Model being used (if applicable)
        agent_version: Agent version (if applicable)
    """
    # Get the appropriate logger
    logger = get_logger(f"{agent_type}.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log agent start
        logger.info(
            f"Starting agent: {agent_name}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            agent_type=agent_type,
            agent_name=agent_name,
            model=model,
            agent_version=agent_version,
            event="agent_start"
        )

def log_agent_completion(agent_type: str,
                        agent_name: str,
                        request_id: str,
                        workspace_id: str,
                        story_id: str,
                        duration_ms: int,
                        result_summary: Optional[Dict[str, Any]] = None,
                        error: Optional[str] = None) -> None:
    """
    Log the completion of an agent's execution.
    
    Args:
        agent_type: Type of agent (triage, analysis, etc.)
        agent_name: Name of the agent
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        duration_ms: Execution duration in milliseconds
        result_summary: Summary of agent result (if applicable)
        error: Error message if execution failed
    """
    # Get the appropriate logger
    logger = get_logger(f"{agent_type}.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        if error:
            # Log agent failure
            logger.error(
                f"Agent failed: {agent_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=agent_type,
                agent_name=agent_name,
                duration_ms=duration_ms,
                error=error,
                event="agent_error"
            )
        else:
            # Log agent success
            logger.info(
                f"Agent completed: {agent_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=agent_type,
                agent_name=agent_name,
                duration_ms=duration_ms,
                result_summary=result_summary,
                event="agent_complete"
            )

def log_agent_handoff(from_agent_type: str,
                     from_agent_name: str,
                     to_agent_type: str,
                     to_agent_name: str,
                     request_id: str,
                     workspace_id: str,
                     story_id: str,
                     handoff_reason: Optional[str] = None) -> None:
    """
    Log a handoff between agents.
    
    Args:
        from_agent_type: Type of the source agent
        from_agent_name: Name of the source agent
        to_agent_type: Type of the target agent
        to_agent_name: Name of the target agent
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        handoff_reason: Reason for the handoff (if available)
    """
    # Get the logger for the source agent
    logger = get_logger(f"{from_agent_type}.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log the handoff
        logger.info(
            f"Handoff from {from_agent_name} to {to_agent_name}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            from_agent_type=from_agent_type,
            from_agent_name=from_agent_name,
            to_agent_type=to_agent_type,
            to_agent_name=to_agent_name,
            handoff_reason=handoff_reason,
            event="agent_handoff"
        )

def log_tool_use(agent_type: str,
                agent_name: str,
                tool_name: str,
                request_id: str,
                workspace_id: str,
                story_id: str,
                parameters: Optional[Dict[str, Any]] = None) -> None:
    """
    Log the use of a tool by an agent.
    
    Args:
        agent_type: Type of agent (triage, analysis, etc.)
        agent_name: Name of the agent
        tool_name: Name of the tool
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        parameters: Tool parameters (excluding sensitive data)
    """
    # Get the appropriate logger
    logger = get_logger(f"{agent_type}.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Ensure we're not logging sensitive data
        safe_params = parameters.copy() if parameters else {}
        for sensitive_param in ["api_key", "token", "password", "secret"]:
            if sensitive_param in safe_params:
                safe_params[sensitive_param] = "[REDACTED]"
        
        # Log tool use
        logger.info(
            f"Using tool: {tool_name}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            agent_type=agent_type,
            agent_name=agent_name,
            tool_name=tool_name,
            parameters=safe_params,
            event="tool_use"
        )

def log_tool_result(agent_type: str,
                   agent_name: str,
                   tool_name: str,
                   request_id: str,
                   workspace_id: str,
                   story_id: str,
                   duration_ms: int,
                   success: bool,
                   result_summary: Optional[str] = None,
                   error: Optional[str] = None) -> None:
    """
    Log the result of a tool execution.
    
    Args:
        agent_type: Type of agent (triage, analysis, etc.)
        agent_name: Name of the agent
        tool_name: Name of the tool
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        duration_ms: Tool execution duration in milliseconds
        success: Whether the tool execution was successful
        result_summary: Summary of the tool result (if applicable)
        error: Error message if tool execution failed
    """
    # Get the appropriate logger
    logger = get_logger(f"{agent_type}.agent")
    
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        if not success:
            # Log tool failure
            logger.error(
                f"Tool failed: {tool_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=agent_type,
                agent_name=agent_name,
                tool_name=tool_name,
                duration_ms=duration_ms,
                error=error,
                event="tool_error"
            )
        else:
            # Log tool success
            logger.info(
                f"Tool completed: {tool_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=agent_type,
                agent_name=agent_name,
                tool_name=tool_name,
                duration_ms=duration_ms,
                result_summary=result_summary,
                event="tool_complete"
            )

def log_analysis_result(request_id: str,
                       workspace_id: str,
                       story_id: str,
                       overall_score: int,
                       title_score: Optional[int] = None,
                       description_score: Optional[int] = None,
                       acceptance_criteria_score: Optional[int] = None,
                       priority_areas: Optional[List[str]] = None) -> None:
    """
    Log the results of a story analysis.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        overall_score: Overall story quality score
        title_score: Title quality score (if available)
        description_score: Description quality score (if available)
        acceptance_criteria_score: Acceptance criteria quality score (if available)
        priority_areas: Priority areas for improvement (if available)
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        # Log overall result
        analysis_logger.info(
            f"Analysis complete: Overall score {overall_score}/10",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            overall_score=overall_score,
            title_score=title_score,
            description_score=description_score,
            acceptance_criteria_score=acceptance_criteria_score,
            event="analysis_complete"
        )
        
        # Log priority areas if available
        if priority_areas:
            analysis_logger.info(
                "Priority improvement areas identified",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                priority_areas=priority_areas,
                event="analysis_priorities"
            )

def log_content_generation(request_id: str,
                          workspace_id: str,
                          story_id: str,
                          generation_type: str,
                          model: str,
                          tokens_used: Optional[int] = None) -> None:
    """
    Log content generation by the system.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        generation_type: Type of content generated (e.g., "title", "description")
        model: Model used for generation
        tokens_used: Number of tokens used (if available)
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        generation_logger.info(
            f"Generated content: {generation_type}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            generation_type=generation_type,
            model=model,
            tokens_used=tokens_used,
            event="content_generation"
        )

def log_story_update(request_id: str,
                    workspace_id: str,
                    story_id: str,
                    update_type: str,
                    fields_updated: List[str]) -> None:
    """
    Log an update to a Shortcut story.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        update_type: Type of update (e.g., "enhancement", "analysis", "comment")
        fields_updated: Fields that were updated
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        update_logger.info(
            f"Story updated: {update_type}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            update_type=update_type,
            fields_updated=fields_updated,
            event="story_update"
        )

def log_comment_added(request_id: str,
                     workspace_id: str,
                     story_id: str,
                     comment_type: str,
                     comment_length: int) -> None:
    """
    Log a comment being added to a Shortcut story.
    
    Args:
        request_id: Request ID for correlation
        workspace_id: Workspace ID
        story_id: Story ID
        comment_type: Type of comment (e.g., "analysis", "enhancement")
        comment_length: Length of the comment in characters
    """
    with trace_context(
        request_id=request_id,
        workspace_id=workspace_id,
        story_id=story_id
    ):
        comment_logger.info(
            f"Comment added: {comment_type}",
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id,
            comment_type=comment_type,
            comment_length=comment_length,
            event="comment_added"
        )