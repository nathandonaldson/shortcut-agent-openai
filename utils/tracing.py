"""
Utility functions for trace context management across agent handoffs.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

# Try to import OpenAI Agent SDK components
try:
    from openai.types.agent.tracing import get_current_trace, trace
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

logger = logging.getLogger("tracing")

# Thread-local storage for trace context
_trace_context = {}

def get_trace_context() -> Dict[str, Any]:
    """
    Get the current trace context.
    
    Returns:
        Dictionary with trace context information
    """
    global _trace_context
    return _trace_context.copy()

def set_trace_context(context: Dict[str, Any]) -> None:
    """
    Set the current trace context.
    
    Args:
        context: Dictionary with trace context information
    """
    global _trace_context
    _trace_context = context.copy()

def clear_trace_context() -> None:
    """Clear the current trace context."""
    global _trace_context
    _trace_context = {}

def capture_current_trace() -> Dict[str, Any]:
    """
    Capture the current OpenAI SDK trace context.
    
    Returns:
        Dictionary with trace information or empty dict if not available
    """
    if not OPENAI_SDK_AVAILABLE:
        return {}
    
    try:
        current_trace = get_current_trace()
        if current_trace:
            return {
                "trace_id": current_trace.trace_id,
                "workflow_name": current_trace.workflow_name,
                "group_id": getattr(current_trace, "group_id", None),
                "metadata": getattr(current_trace, "metadata", {})
            }
    except Exception as e:
        logger.warning(f"Error capturing trace context: {str(e)}")
    
    return {}

@contextmanager
def preserve_trace_context():
    """
    Context manager to preserve trace context during operations.
    
    This ensures trace context is restored after a block of code executes.
    """
    # Capture the current context
    original_context = get_trace_context()
    try:
        yield
    finally:
        # Restore the original context
        set_trace_context(original_context)

def prepare_handoff_context(workspace_context: Any) -> None:
    """
    Prepare context for agent handoff by capturing current trace information.
    
    Args:
        workspace_context: The workspace context to enrich with trace information
    """
    if not hasattr(workspace_context, "trace_context"):
        # Add trace context attribute if it doesn't exist
        workspace_context.trace_context = {}
    
    # Capture current trace context
    trace_info = capture_current_trace()
    
    if trace_info:
        # Update workspace context with trace information
        workspace_context.trace_context.update(trace_info)
        logger.debug(f"Preserved trace context for handoff: {trace_info.get('trace_id')}")

def restore_handoff_context(workspace_context: Any) -> Optional[Any]:
    """
    Restore trace context after agent handoff.
    
    Args:
        workspace_context: The workspace context containing trace information
        
    Returns:
        Trace object if restored successfully, None otherwise
    """
    if not OPENAI_SDK_AVAILABLE:
        return None
    
    if not hasattr(workspace_context, "trace_context"):
        return None
    
    trace_info = workspace_context.trace_context
    if not trace_info:
        return None
    
    try:
        # Create a new trace that continues the previous trace
        parent_trace_id = trace_info.get("trace_id")
        workflow_name = trace_info.get("workflow_name", "Continued Workflow")
        group_id = trace_info.get("group_id")
        metadata = trace_info.get("metadata", {})
        
        if parent_trace_id:
            # Add parent trace information to metadata
            metadata["parent_trace_id"] = parent_trace_id
            logger.debug(f"Restoring trace context from parent: {parent_trace_id}")
            
            # Return a trace context manager (will be used with 'with' statement)
            return trace(
                workflow_name=f"{workflow_name} (continued)",
                group_id=group_id,
                trace_metadata=metadata
            )
    except Exception as e:
        logger.warning(f"Error restoring trace context: {str(e)}")
    
    return None