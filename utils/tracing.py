"""
Trace context utilities for agent handoffs.

This module provides utilities for preserving and restoring trace context
during agent handoffs to maintain consistent tracing and logging.
"""

import os
import json
import time
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar

from context.workspace.workspace_context import WorkspaceContext
from utils.logging.logger import get_logger, trace_context, get_current_trace_context, set_trace_context

# Create a logger for tracing
logger = get_logger("utils.tracing")

# Context variable for storing handoff context
handoff_context_var: ContextVar[Dict[str, Any]] = ContextVar('handoff_context', default={})

def prepare_handoff_context(workspace_context: WorkspaceContext) -> WorkspaceContext:
    """
    Prepare context for handoff to another agent.
    
    This function captures the current trace context and stores it in the workspace context
    to be restored in the target agent.
    
    Args:
        workspace_context: The workspace context to prepare for handoff
        
    Returns:
        The prepared workspace context
    """
    # Get the current trace context
    current_trace_context = get_current_trace_context()
    
    # Store trace context in the workspace context
    if not hasattr(workspace_context, '_trace_context'):
        setattr(workspace_context, '_trace_context', {})
    
    # Update trace context
    trace_context_dict = getattr(workspace_context, '_trace_context', {})
    trace_context_dict.update(current_trace_context)
    setattr(workspace_context, '_trace_context', trace_context_dict)
    
    # Generate handoff ID if not present
    if 'handoff_id' not in trace_context_dict:
        handoff_id = str(uuid.uuid4())
        trace_context_dict['handoff_id'] = handoff_id
    
    # Log the handoff preparation
    logger.info(
        "Preparing agent handoff context",
        handoff_id=trace_context_dict.get('handoff_id'),
        trace_id=trace_context_dict.get('trace_id'),
        from_agent=trace_context_dict.get('current_agent'),
        workspace_id=workspace_context.workspace_id,
        story_id=workspace_context.story_id
    )
    
    return workspace_context

def restore_handoff_context(workspace_context: WorkspaceContext) -> None:
    """
    Restore trace context after handoff from another agent.
    
    This function restores the trace context that was stored in the workspace context
    by the source agent.
    
    Args:
        workspace_context: The workspace context with stored trace context
    """
    # Get the trace context from the workspace context
    trace_context_dict = getattr(workspace_context, '_trace_context', {})
    
    if not trace_context_dict:
        # No trace context found, create a new one
        logger.warning(
            "No trace context found in workspace context, creating new",
            workspace_id=workspace_context.workspace_id,
            story_id=workspace_context.story_id
        )
        return
    
    # Restore trace context
    set_trace_context(**trace_context_dict)
    
    # Update current agent
    agent_name = trace_context_dict.get('target_agent')
    if agent_name:
        trace_context_dict['current_agent'] = agent_name
        trace_context_dict['target_agent'] = None
    
    # Log the handoff restoration
    logger.info(
        "Restored agent handoff context",
        handoff_id=trace_context_dict.get('handoff_id'),
        trace_id=trace_context_dict.get('trace_id'),
        to_agent=trace_context_dict.get('current_agent'),
        workspace_id=workspace_context.workspace_id,
        story_id=workspace_context.story_id
    )

def create_trace_id() -> str:
    """
    Create a new trace ID.
    
    Returns:
        A unique trace ID string
    """
    return f"trace-{str(uuid.uuid4())}"

def record_handoff(source_agent: str, target_agent: str, 
                 workspace_context: WorkspaceContext, 
                 input_data: Any) -> str:
    """
    Record a handoff between shortcut_agents.
    
    Args:
        source_agent: Name of the source agent
        target_agent: Name of the target agent
        workspace_context: The workspace context
        input_data: The input data being passed to the target agent
        
    Returns:
        Handoff ID string
    """
    # Get or create trace context
    trace_context_dict = getattr(workspace_context, '_trace_context', {})
    if not trace_context_dict:
        trace_context_dict = {}
        setattr(workspace_context, '_trace_context', trace_context_dict)
    
    # Generate handoff ID
    handoff_id = str(uuid.uuid4())
    trace_context_dict['handoff_id'] = handoff_id
    
    # Get or generate trace ID
    trace_id = trace_context_dict.get('trace_id')
    if not trace_id:
        trace_id = create_trace_id()
        trace_context_dict['trace_id'] = trace_id
    
    # Update agent information
    trace_context_dict['current_agent'] = source_agent
    trace_context_dict['target_agent'] = target_agent
    
    # Record timestamp
    timestamp = time.time()
    trace_context_dict['handoff_timestamp'] = timestamp
    
    # Log the handoff
    logger.info(
        f"Agent handoff: {source_agent} -> {target_agent}",
        handoff_id=handoff_id,
        trace_id=trace_id,
        source_agent=source_agent,
        target_agent=target_agent,
        workspace_id=workspace_context.workspace_id,
        story_id=workspace_context.story_id,
        timestamp=timestamp
    )
    
    return handoff_id

def track_handoff_completion(handoff_id: str, success: bool, result: Any = None) -> None:
    """
    Track completion of a handoff.
    
    Args:
        handoff_id: The handoff ID
        success: Whether the handoff completed successfully
        result: Optional result summary
    """
    # Get current trace context
    trace_context_dict = get_current_trace_context()
    
    # Log completion
    logger.info(
        f"Agent handoff completed: {'success' if success else 'failed'}",
        handoff_id=handoff_id,
        trace_id=trace_context_dict.get('trace_id'),
        success=success,
        current_agent=trace_context_dict.get('current_agent'),
        result_summary=str(result)[:100] if result else None
    )