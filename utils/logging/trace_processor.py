"""
OpenAI Agent SDK trace processor for the Shortcut Enhancement System.
"""

import os
import json
import time
from typing import Dict, Any, Optional

# Try to import from agents.tracing, but provide fallbacks if not available
try:
    from agents.tracing import add_trace_processor
    # Import classes directly
    try:
        from agents.tracing.processor_interface import ProcessorInterface as TraceProcessor
        from agents.tracing.trace import Trace
        from agents.tracing.span import Span
    except ImportError:
        # Fallback to base classes if available
        from agents.tracing.base import TraceProcessor, Trace, Span
    
    TRACING_AVAILABLE = True
except ImportError:
    # Create dummy classes for when tracing is not available
    print("Warning: OpenAI Agents SDK tracing classes not available, using dummy implementations")
    TRACING_AVAILABLE = False
    
    class Trace:
        """Dummy Trace class when agents.tracing is not available."""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class Span:
        """Dummy Span class when agents.tracing is not available."""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class TraceProcessor:
        """Dummy TraceProcessor class when agents.tracing is not available."""
        async def process_trace(self, trace):
            """Dummy implementation."""
            pass
        
        async def process_span(self, span):
            """Dummy implementation."""
            pass
    
    def add_trace_processor(processor):
        """Dummy implementation of add_trace_processor."""
        print(f"Would add trace processor: {processor.__class__.__name__} (dummy implementation)")

# Import our logger after defining the classes to avoid circular imports
from utils.logging.logger import get_logger

# Configure logger for trace processor
logger = get_logger("trace_processor")

# Log directory for trace outputs
TRACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                        "logs", "traces")
os.makedirs(TRACE_DIR, exist_ok=True)

class EnhancementTraceProcessor(TraceProcessor):
    """
    Trace processor for Shortcut Enhancement agents.
    
    Captures and processes OpenAI Agent SDK traces, extracting key metrics
    and logging them for monitoring and debugging.
    """
    
    def __init__(self, store_full_traces: bool = True, trace_dir: str = TRACE_DIR):
        """
        Initialize the trace processor.
        
        Args:
            store_full_traces: Whether to store full traces to disk
            trace_dir: Directory to store traces
        """
        self.store_full_traces = store_full_traces
        self.trace_dir = trace_dir
        
        # Create trace directory if it doesn't exist
        if self.store_full_traces:
            os.makedirs(self.trace_dir, exist_ok=True)
    
    async def process_trace(self, trace: Trace) -> None:
        """
        Process a completed trace.
        
        Args:
            trace: The trace object
        """
        # Extract trace metadata
        metadata = getattr(trace, "metadata", {}) or {}
        
        # Get workspace_id and story_id from metadata if available
        workspace_id = metadata.get("workspace_id", "unknown")
        story_id = metadata.get("story_id", "unknown")
        
        # Calculate duration
        duration_ms = 0
        try:
            if hasattr(trace, "start_time") and hasattr(trace, "end_time"):
                if trace.start_time and trace.end_time:
                    duration_ms = int((trace.end_time - trace.start_time) * 1000)
        except Exception as e:
            logger.error(f"Error calculating trace duration: {str(e)}")
        
        # Log trace completion
        logger.info(
            f"Trace completed: {trace.workflow_name}",
            trace_id=trace.trace_id,
            group_id=getattr(trace, "group_id", None),
            workspace_id=workspace_id,
            story_id=story_id,
            duration_ms=duration_ms
        )
        
        # Store full trace to disk if enabled
        if self.store_full_traces:
            try:
                # Create a filename with workspace and story IDs if available
                filename = f"{workspace_id}_{story_id}_{trace.trace_id}_{int(time.time())}.json"
                filepath = os.path.join(self.trace_dir, filename)
                
                # Convert trace to a serializable format
                trace_data = self._trace_to_dict(trace)
                
                # Write to file
                with open(filepath, 'w') as f:
                    json.dump(trace_data, f, indent=2)
                
                logger.debug(f"Trace saved to {filepath}")
            except Exception as e:
                logger.error(f"Error saving trace: {str(e)}")
    
    async def process_span(self, span: Span) -> None:
        """
        Process a span from a trace.
        
        Args:
            span: The span object
        """
        # Extract span data
        span_data = getattr(span, "span_data", None)
        if not span_data:
            return
        
        # Extract span type
        span_type = getattr(span_data, "type", "unknown")
        
        # Process based on span type
        if span_type == "agent":
            # Agent span
            agent_name = getattr(span_data, "agent_name", "unknown")
            logger.info(
                f"Agent execution: {agent_name}",
                trace_id=span.trace_id,
                span_id=span.span_id,
                agent_name=agent_name
            )
        elif span_type == "function":
            # Function call span
            function_name = getattr(span_data, "function_name", "unknown")
            function_args = getattr(span_data, "function_args", {})
            
            # Log function call
            logger.info(
                f"Function call: {function_name}",
                trace_id=span.trace_id,
                span_id=span.span_id,
                function_name=function_name,
                # Only log argument names, not values
                arg_names=list(function_args.keys()) if function_args else []
            )
            
            # If function returned, log the result type (not value for privacy)
            if hasattr(span_data, "function_output") and span_data.function_output is not None:
                result_type = type(span_data.function_output).__name__
                logger.info(
                    f"Function returned: {function_name}",
                    trace_id=span.trace_id,
                    span_id=span.span_id,
                    function_name=function_name,
                    result_type=result_type
                )
        elif span_type == "agent_trace":
            # Agent trace span
            span_name = getattr(span_data, "name", "unknown")
            logger.info(
                f"Agent trace: {span_name}",
                trace_id=span.trace_id,
                span_id=span.span_id,
                span_name=span_name
            )
    
    def _trace_to_dict(self, trace: Trace) -> Dict[str, Any]:
        """
        Convert a trace object to a serializable dictionary.
        
        Args:
            trace: The trace object
            
        Returns:
            Dictionary representation of the trace
        """
        try:
            # Get trace attributes
            trace_dict = {
                "trace_id": trace.trace_id,
                "workflow_name": trace.workflow_name,
                "group_id": getattr(trace, "group_id", None),
                "metadata": getattr(trace, "metadata", {}),
                "start_time": getattr(trace, "start_time", None),
                "end_time": getattr(trace, "end_time", None),
            }
            
            # Add spans if available
            if hasattr(trace, "spans") and trace.spans:
                trace_dict["spans"] = [self._span_to_dict(span) for span in trace.spans]
            
            return trace_dict
        except Exception as e:
            logger.error(f"Error converting trace to dict: {str(e)}")
            return {"error": str(e), "trace_id": trace.trace_id}
    
    def _span_to_dict(self, span: Span) -> Dict[str, Any]:
        """
        Convert a span object to a serializable dictionary.
        
        Args:
            span: The span object
            
        Returns:
            Dictionary representation of the span
        """
        try:
            # Get basic span attributes
            span_dict = {
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "parent_id": getattr(span, "parent_id", None),
                "start_time": getattr(span, "start_time", None),
                "end_time": getattr(span, "end_time", None),
            }
            
            # Add span data if available
            span_data = getattr(span, "span_data", None)
            if span_data:
                span_dict["type"] = getattr(span_data, "type", "unknown")
                
                # Handle different span types
                if span_dict["type"] == "agent":
                    span_dict["agent_name"] = getattr(span_data, "agent_name", "unknown")
                elif span_dict["type"] == "function":
                    span_dict["function_name"] = getattr(span_data, "function_name", "unknown")
                    # Don't include function arguments for privacy
                    span_dict["has_args"] = hasattr(span_data, "function_args") and span_data.function_args is not None
                    span_dict["has_output"] = hasattr(span_data, "function_output") and span_data.function_output is not None
                    if span_dict["has_output"]:
                        span_dict["output_type"] = type(span_data.function_output).__name__
            
            return span_dict
        except Exception as e:
            logger.error(f"Error converting span to dict: {str(e)}")
            return {"error": str(e), "span_id": span.span_id}


def setup_trace_processor():
    """
    Set up and register the trace processor with the OpenAI Agent SDK.
    This function should be called during application initialization.
    """
    # Check if tracing is available
    if not TRACING_AVAILABLE:
        logger.warning("OpenAI Agent SDK tracing not available, skipping trace processor setup")
        return
        
    try:
        # Create trace processor instance
        processor = EnhancementTraceProcessor()
        
        # Register the processor with the OpenAI Agent SDK
        add_trace_processor(processor)
        
        logger.info("Registered EnhancementTraceProcessor with OpenAI Agent SDK")
    except Exception as e:
        logger.error(f"Error setting up trace processor: {str(e)}")
        # Don't re-raise to allow the application to continue without tracing
