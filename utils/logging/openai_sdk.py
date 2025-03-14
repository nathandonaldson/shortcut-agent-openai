"""
OpenAI Agent SDK integration for the Shortcut Enhancement System.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Callable

# Try to import OpenAI Agent SDK components
try:
    from openai import OpenAI
    from shortcut_agents import AgentCompletionParameters, AgentHooks
    from shortcut_agents import RunContextWrapper, AgentResponseInfo, AgentResponse, AgentChatResponse
    from shortcut_agents import FunctionCall, Tool, FunctionTool
    from shortcut_agents.lifecycle import FunctionInputPair, FunctionOutputPair, RunStep
    from shortcut_agents.tracing import Trace, Span, TraceProcessor, get_current_trace, add_trace_processor
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints
    class AgentCompletionParameters:
        pass
    
    class AgentHooks:
        pass
    
    class RunContextWrapper:
        pass
    
    class AgentResponse:
        pass
    
    OPENAI_SDK_AVAILABLE = False

# Import our logging components
from utils.logging.logger import get_logger, trace_context
from utils.logging.trace_processor import EnhancementTraceProcessor

# Create logger for OpenAI SDK
sdk_logger = get_logger("openai.sdk")

class LoggingAgentHooks(AgentHooks):
    """
    Agent hooks for logging agent execution events.
    
    This class provides hooks into the OpenAI Agent SDK execution pipeline
    to add logging at key points in agent execution.
    """
    
    def __init__(self, agent_type: str, agent_name: str, log_level: str = "INFO"):
        """
        Initialize the logging hooks.
        
        Args:
            agent_type: Type of agent (triage, analysis, etc.)
            agent_name: Name of the agent
            log_level: Log level for the hooks (DEBUG, INFO, WARNING, ERROR)
        """
        super().__init__()
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.logger = get_logger(f"{agent_type}.agent")
        
        # Set log level
        level = getattr(logging, log_level, logging.INFO)
        self.logger.logger.setLevel(level)
    
    async def pre_completion(self, 
                            context: RunContextWrapper, 
                            params: AgentCompletionParameters):
        """
        Hook called before the agent processes the request.
        
        Args:
            context: The execution context
            params: Agent completion parameters
            
        Returns:
            Modified parameters if needed
        """
        # Try to extract context values
        request_id = None
        workspace_id = None
        story_id = None
        
        if hasattr(context, 'context'):
            ctx = context.context
            if hasattr(ctx, 'request_id'):
                request_id = ctx.request_id
            if hasattr(ctx, 'workspace_id'):
                workspace_id = ctx.workspace_id
            if hasattr(ctx, 'story_id'):
                story_id = ctx.story_id
        
        # Log agent request start
        with trace_context(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        ):
            self.logger.info(
                f"Starting {self.agent_name} request",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=self.agent_type,
                agent_name=self.agent_name,
                event="agent_request_start"
            )
        
        # Return original parameters
        return params
    
    async def post_completion(self, 
                            context: RunContextWrapper, 
                            response: AgentResponse):
        """
        Hook called after the agent processes the request.
        
        Args:
            context: The execution context
            response: Agent response
            
        Returns:
            Modified response if needed
        """
        # Try to extract context values
        request_id = None
        workspace_id = None
        story_id = None
        
        if hasattr(context, 'context'):
            ctx = context.context
            if hasattr(ctx, 'request_id'):
                request_id = ctx.request_id
            if hasattr(ctx, 'workspace_id'):
                workspace_id = ctx.workspace_id
            if hasattr(ctx, 'story_id'):
                story_id = ctx.story_id
        
        # Log agent request completion
        with trace_context(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        ):
            # For AgentChatResponse, there might be multiple items
            if isinstance(response, AgentChatResponse) and hasattr(response, 'items'):
                # Count different item types
                counts = {}
                for item in response.items:
                    item_type = getattr(item, 'type', 'unknown')
                    counts[item_type] = counts.get(item_type, 0) + 1
                
                self.logger.info(
                    f"Completed {self.agent_name} request",
                    request_id=request_id,
                    workspace_id=workspace_id,
                    story_id=story_id,
                    agent_type=self.agent_type,
                    agent_name=self.agent_name,
                    item_counts=counts,
                    event="agent_request_complete"
                )
            else:
                # Generic completion log
                self.logger.info(
                    f"Completed {self.agent_name} request",
                    request_id=request_id,
                    workspace_id=workspace_id,
                    story_id=story_id,
                    agent_type=self.agent_type,
                    agent_name=self.agent_name,
                    event="agent_request_complete"
                )
        
        # Return original response
        return response
    
    async def pre_function_call(self, 
                              context: RunContextWrapper, 
                              function_call: FunctionInputPair):
        """
        Hook called before a function is called.
        
        Args:
            context: The execution context
            function_call: Function call information
            
        Returns:
            Modified function call if needed
        """
        # Try to extract context values
        request_id = None
        workspace_id = None
        story_id = None
        
        if hasattr(context, 'context'):
            ctx = context.context
            if hasattr(ctx, 'request_id'):
                request_id = ctx.request_id
            if hasattr(ctx, 'workspace_id'):
                workspace_id = ctx.workspace_id
            if hasattr(ctx, 'story_id'):
                story_id = ctx.story_id
        
        # Get function name
        function_name = getattr(function_call, 'name', 'unknown')
        
        # Get parameters (excluding sensitive data)
        parameters = getattr(function_call, 'parameters', {})
        safe_params = {}
        for key, value in parameters.items():
            if key.lower() in ["api_key", "token", "password", "secret"]:
                safe_params[key] = "[REDACTED]"
            else:
                safe_params[key] = value
        
        # Log function call
        with trace_context(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        ):
            self.logger.info(
                f"Calling function: {function_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=self.agent_type,
                agent_name=self.agent_name,
                function_name=function_name,
                parameters=safe_params,
                event="function_call"
            )
        
        # Return original function call
        return function_call
    
    async def post_function_call(self, 
                               context: RunContextWrapper, 
                               function_output: FunctionOutputPair):
        """
        Hook called after a function is called.
        
        Args:
            context: The execution context
            function_output: Function output information
            
        Returns:
            Modified function output if needed
        """
        # Try to extract context values
        request_id = None
        workspace_id = None
        story_id = None
        
        if hasattr(context, 'context'):
            ctx = context.context
            if hasattr(ctx, 'request_id'):
                request_id = ctx.request_id
            if hasattr(ctx, 'workspace_id'):
                workspace_id = ctx.workspace_id
            if hasattr(ctx, 'story_id'):
                story_id = ctx.story_id
        
        # Get function name
        function_name = getattr(function_output, 'name', 'unknown')
        
        # Get output (exclude sensitive data)
        output = getattr(function_output, 'output', None)
        output_type = type(output).__name__ if output is not None else 'None'
        
        # Log function output
        with trace_context(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        ):
            self.logger.info(
                f"Function returned: {function_name}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=self.agent_type,
                agent_name=self.agent_name,
                function_name=function_name,
                output_type=output_type,
                event="function_output"
            )
        
        # Return original function output
        return function_output
    
    async def post_step(self, 
                       context: RunContextWrapper, 
                       run_step: RunStep):
        """
        Hook called after each step in the agent's execution.
        
        Args:
            context: The execution context
            run_step: The run step information
            
        Returns:
            Modified run step if needed
        """
        # Try to extract context values
        request_id = None
        workspace_id = None
        story_id = None
        
        if hasattr(context, 'context'):
            ctx = context.context
            if hasattr(ctx, 'request_id'):
                request_id = ctx.request_id
            if hasattr(ctx, 'workspace_id'):
                workspace_id = ctx.workspace_id
            if hasattr(ctx, 'story_id'):
                story_id = ctx.story_id
        
        # Determine step type and log at debug level (to avoid too much noise)
        step_type = getattr(run_step, 'step_type', 'unknown')
        
        with trace_context(
            request_id=request_id,
            workspace_id=workspace_id,
            story_id=story_id
        ):
            self.logger.debug(
                f"Agent step: {step_type}",
                request_id=request_id,
                workspace_id=workspace_id,
                story_id=story_id,
                agent_type=self.agent_type,
                agent_name=self.agent_name,
                step_type=step_type,
                event="agent_step"
            )
        
        # Return original run step
        return run_step

def configure_openai_sdk_logging() -> None:
    """
    Configure OpenAI Agent SDK logging integration.
    
    This sets up the trace processor and configures SDK loggers.
    """
    if not OPENAI_SDK_AVAILABLE:
        sdk_logger.warning("OpenAI Agent SDK not available - SDK logging integration disabled")
        return
    
    try:
        # Configure SDK loggers
        openai_logger = logging.getLogger("openai")
        agents_logger = logging.getLogger("openai.agents")
        tracing_logger = logging.getLogger("openai.agents.tracing")
        
        # Set appropriate levels based on environment
        if os.environ.get("ENVIRONMENT", "development") == "production":
            # Less verbose in production
            openai_logger.setLevel(logging.WARNING)
            agents_logger.setLevel(logging.INFO)
            tracing_logger.setLevel(logging.INFO)
        else:
            # More verbose in development
            openai_logger.setLevel(logging.INFO)
            agents_logger.setLevel(logging.DEBUG)
            tracing_logger.setLevel(logging.DEBUG)
        
        # Add trace processor
        trace_processor = EnhancementTraceProcessor()
        add_trace_processor(trace_processor)
        
        sdk_logger.info("OpenAI Agent SDK logging integration configured")
    except Exception as e:
        sdk_logger.error(f"Error configuring OpenAI SDK logging: {str(e)}")

# Initialize when module is imported
if OPENAI_SDK_AVAILABLE:
    configure_openai_sdk_logging()