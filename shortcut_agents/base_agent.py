"""
Base Agent implementation for the Shortcut Enhancement System.

This module provides a standardized base for all agents in the system,
implementing common patterns and best practices for the OpenAI Agent SDK.
"""

import os
import json
import logging
import time
import importlib.util
import sys
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Union, Callable
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("base_agent")

# Check for mock agent flag
USE_MOCK_AGENTS = os.environ.get("USE_MOCK_AGENTS", "false").lower() in ("true", "1", "yes")

# Check for OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY and not USE_MOCK_AGENTS:
    logger.warning("OPENAI_API_KEY not set, forcing mock implementation")
    USE_MOCK_AGENTS = True

# OpenAI imports
try:
    import openai
    from openai import OpenAI
    
    # Only try to import OpenAI Agent SDK if not using mocks
    if not USE_MOCK_AGENTS:
        try:
            # Check if the agents package is available
            if importlib.util.find_spec("agents") is not None:
                # Import from the OpenAI Agent SDK
                from agents import (
                    Agent, AgentHooks, Runner, ModelSettings, 
                    GuardrailFunctionOutput, FunctionTool, Tool, 
                    input_guardrail, output_guardrail, Trace, 
                    Span, get_current_trace, trace, RunItem,
                    RunContextWrapper, Handoff, InputGuardrail, OutputGuardrail
                )
                
                # Map to expected names
                RunStep = RunItem
                ThreadMessage = dict
                Handoffs = Handoff
                AgentChatResponse = dict
                OutputType = lambda result_type: {"result_type": result_type}
                FunctionDefinition = dict
                FunctionOutputPair = dict
                FunctionInputPair = dict
                
                logger.info(f"OpenAI version: {openai.__version__}")
                logger.info(f"OpenAI Agents SDK version found")
                SDK_AVAILABLE = True
            else:
                raise ImportError("OpenAI Agent SDK not found")
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.warning(f"OpenAI Agent SDK not available (error: {str(e)}), using mock implementation")
            USE_MOCK_AGENTS = True
            SDK_AVAILABLE = False
    else:
        SDK_AVAILABLE = False
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"OpenAI library not available (error: {str(e)}), using mock implementation")
    USE_MOCK_AGENTS = True
    SDK_AVAILABLE = False

# Mock classes for testing - these would normally come from OpenAI Agent SDK
class BaseAgentMock:
    """Mock for OpenAI Agent SDK."""
    
    def __init__(self, name=None, tools=None, hooks=None, simplified=False):
        self.name = name
        self.tools = tools or []
        self.hooks = hooks
        self.simplified = simplified
        self.response = None  # For tests to set the response
    
    async def run(self, input_data=None, context=None):
        """Mock run method for testing."""
        if self.hooks:
            if hasattr(self.hooks, 'pre_run'):
                input_data = self.hooks.pre_run(input_data, context)
            
            result = self.response or {"status": "success", "message": "Mock response"}
            
            if hasattr(self.hooks, 'post_run'):
                result = self.hooks.post_run(result, context)
            
            if hasattr(self.hooks, 'process_result'):
                result = self.hooks.process_result(result)
                
        return result
    
    def choose_model(self, context=None):
        """Mock model selection."""
        return "mock-model"
    
    @classmethod
    def handoff_to(cls, target_agent_class, context=None, input_data=None):
        """Mock handoff method for testing."""
        # Import utilities here to avoid circular imports
        from utils.tracing import prepare_handoff_context, record_handoff
        
        # Prepare the context for handoff
        if context:
            prepare_handoff_context(context)
            
            # Record the handoff for tracing
            source_agent_name = cls.__name__ if hasattr(cls, "__name__") else "Unknown"
            target_agent_name = target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
            record_handoff(source_agent_name, target_agent_name, context, input_data)
        
        return {
            "status": "success",
            "handoff": {
                "source": cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                "target": target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
            }
        }

# Set up mock classes if needed
if USE_MOCK_AGENTS:
    logger.info("Using mock OpenAI Agent SDK classes")
    Agent = BaseAgentMock
    AgentChatResponse = BaseAgentMock
    
    # Define hook base class
    class BaseAgentHooks:
        """Base class for agent hooks."""
        
        def __init__(self, agent_type="unknown", agent_name="Unknown Agent"):
            self.agent_type = agent_type
            self.agent_name = agent_name
        
        def pre_run(self, input_data, context):
            """Process input before running the agent."""
            return input_data
        
        def post_run(self, result, context):
            """Process result after running the agent."""
            return result
        
        def process_result(self, result):
            """Process the final result for return to caller."""
            return result
    
    AgentHooks = BaseAgentHooks
    
    # Create a BaseAgent class that matches the test expectations
    class BaseAgent(BaseAgentMock):
        """Base class for all agents."""
        
        def __init__(self, agent_type="unknown", agent_name="Unknown Agent", system_message="", output_class=None, **kwargs):
            """Initialize the agent."""
            self.agent_type = agent_type
            self.name = agent_name
            self.system_message = system_message
            self.output_class = output_class
            self.tools = kwargs.get("tools", [])
            self.hooks = kwargs.get("hooks", None)
            self.simplified = kwargs.get("simplified", False)
            self.logger = logging.getLogger(f"{agent_type}.agent")
            
        async def run(self, input_data, context=None):
            """Run the agent."""
            if self.simplified:
                return self.run_simplified(input_data, context)
                
            if self.hooks:
                input_data = self.hooks.pre_run(input_data, context)
                
            result = {"status": "success", "message": "Mock response"}
            
            if self.hooks:
                result = self.hooks.post_run(result, context)
                result = self.hooks.process_result(result)
                
            return result
        
        def run_simplified(self, input_data, context):
            """Run in simplified mode."""
            return {"simplified": True, "input": input_data}
        
        def get_model(self, context=None):
            """Choose a model based on configuration."""
            return "mock-model"
        
        @classmethod
        def handoff_to(cls, target_agent_class, context=None, input_data=None):
            """Hand off to another agent."""
            # Import utilities here to avoid circular imports
            from utils.tracing import prepare_handoff_context, record_handoff
            
            # Prepare the context for handoff
            if context:
                prepare_handoff_context(context)
                
                # Record the handoff for tracing
                source_agent_name = cls.__name__ if hasattr(cls, "__name__") else "Unknown"
                target_agent_name = target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
                record_handoff(source_agent_name, target_agent_name, context, input_data)
            
            return {
                "status": "success",
                "handoff": {
                    "source": cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                    "target": target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
                }
            }
else:
    # When using real OpenAI Agent SDK, these are already imported
    logger.info("Using real OpenAI Agent SDK classes")
    # BaseAgentHooks will use the real AgentHooks as base class
    class BaseAgentHooks(AgentHooks):
        """Base class for agent hooks."""
        
        def __init__(self, agent_type="unknown", agent_name="Unknown Agent"):
            """Initialize the agent hooks."""
            self.agent_type = agent_type
            self.agent_name = agent_name
        
        def pre_run(self, input_data, context):
            """Process input before running the agent."""
            return input_data
        
        def post_run(self, result, context):
            """Process result after running the agent."""
            return result
        
        def process_result(self, result):
            """Process the final result for return to caller."""
            return result
    
    # BaseAgent will extend the real Agent class
    class BaseAgent(Agent):
        """Base class for all agents."""
        
        def __init__(self, agent_type="unknown", agent_name="Unknown Agent", system_message="", output_class=None, **kwargs):
            """Initialize the agent."""
            super().__init__()
            self.agent_type = agent_type
            self.name = agent_name
            self.system_message = system_message
            self.output_class = output_class
            self.tools = kwargs.get("tools", [])
            self.hooks = kwargs.get("hooks", None)
            self.simplified = kwargs.get("simplified", False)
            self.logger = logging.getLogger(f"{agent_type}.agent")
            
        async def run(self, input_data, context=None):
            """Run the agent."""
            if self.simplified:
                return self.run_simplified(input_data, context)
                
            if self.hooks:
                input_data = self.hooks.pre_run(input_data, context)
                
            # Integration with OpenAI Agent SDK would happen here in real implementation
            result = {"status": "success", "message": "Real agent result would be here"}
            
            if self.hooks:
                result = self.hooks.post_run(result, context)
                result = self.hooks.process_result(result)
                
            return result
        
        def run_simplified(self, input_data, context):
            """Run in simplified mode."""
            return {"simplified": True, "input": input_data}
        
        def get_model(self, context=None):
            """Choose a model based on configuration."""
            return "gpt-4o"
        
        @classmethod
        def handoff_to(cls, target_agent_class, context=None, input_data=None):
            """Hand off to another agent."""
            # Import utilities here to avoid circular imports
            from utils.tracing import prepare_handoff_context, record_handoff
            
            # Prepare the context for handoff
            if context:
                prepare_handoff_context(context)
                
                # Record the handoff for tracing
                source_agent_name = cls.__name__ if hasattr(cls, "__name__") else "Unknown"
                target_agent_name = target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
                record_handoff(source_agent_name, target_agent_name, context, input_data)
            
            return {
                "status": "success",
                "handoff": {
                    "source": cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                    "target": target_agent_class.__name__ if hasattr(target_agent_class, "__name__") else "Unknown"
                }
            }

# Additional mock classes if needed
if USE_MOCK_AGENTS:
    GuardrailFunctionOutput = BaseAgentMock
    RunContextWrapper = BaseAgentMock
    FunctionTool = BaseAgentMock
    Tool = BaseAgentMock
    Handoffs = BaseAgentMock
    FunctionDefinition = BaseAgentMock
    FunctionOutputPair = BaseAgentMock 
    FunctionInputPair = BaseAgentMock
    RunStep = BaseAgentMock
    ModelSettings = BaseAgentMock
    OutputType = lambda result_type: {"result_type": result_type}  # Function to create output type
    input_guardrail = lambda func: func  # Mock decorator
    output_guardrail = lambda func: func  # Mock decorator
    Trace = BaseAgentMock
    Span = BaseAgentMock
    get_current_trace = lambda: None  # Mock function
    trace = lambda name, **kwargs: lambda func: func  # Mock decorator
    Runner = BaseAgentMock
    ThreadMessage = BaseAgentMock

# Local imports
from context.workspace.workspace_context import WorkspaceContext, WorkflowType
from utils.tracing import prepare_handoff_context, restore_handoff_context
from utils.storage.local_storage import local_storage
from config import get_config, is_development, is_production

# Type variable for the output type
T = TypeVar('T')
U = TypeVar('U')

class BaseAgentHooks(AgentHooks, Generic[T]):
    """
    Standard lifecycle hooks for all agents.
    
    This base class implements common hook functionality that all agents should use,
    providing consistent logging, tracing, and context management.
    """
    
    def __init__(self, agent_type: str, agent_name: str):
        """
        Initialize the agent hooks.
        
        Args:
            agent_type: Type of agent (triage, analysis, update, etc.)
            agent_name: Display name of the agent
        """
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"{agent_type}.agent")
    
    async def pre_generation(self, context, agent, input_items):
        """Hook that runs before the agent generates a response."""
        self.logger.info(f"Starting {self.agent_name} processing")
        
        # Extract context data if available
        if hasattr(context, "context") and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            story_id = getattr(workspace_context, "story_id", "unknown")
            workspace_id = getattr(workspace_context, "workspace_id", "unknown")
            
            self.logger.info(
                f"Processing {self.agent_type} for story {story_id} in workspace {workspace_id}",
                extra={"story_id": story_id, "workspace_id": workspace_id}
            )
            
            # Restore trace context if it exists
            trace_ctx = restore_handoff_context(workspace_context)
            if trace_ctx:
                self.logger.info(f"Restored trace context from previous agent")
        
        return input_items
    
    async def post_generation(self, context, agent, response):
        """Hook that runs after the agent generates a response."""
        self.logger.info(f"Completed {self.agent_name} processing")
        
        # Extract and store results if available
        if hasattr(context, "context") and isinstance(context.context, WorkspaceContext):
            workspace_context = context.context
            
            # Extract the result from the response
            result = None
            for item in response.items:
                if item.type == "output_type" and hasattr(item, "value"):
                    result = item.value
                    break
            
            if result:
                # Process the result (can be overridden by subclasses)
                await self.process_result(workspace_context, result)
                
                # Preserve trace context for potential handoffs
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
        
        self.logger.info(
            f"Calling function: {function_name}",
            extra={"parameters": safe_params, "agent": self.agent_type}
        )
        return function_call
    
    async def post_function_call(self, context, function_output):
        """Hook that runs after a function is called."""
        function_name = getattr(function_output, 'name', 'unknown')
        
        # Get output type without exposing sensitive data
        output = getattr(function_output, 'output', None)
        output_type = type(output).__name__ if output is not None else 'None'
        
        self.logger.info(
            f"Function completed: {function_name}",
            extra={"output_type": output_type, "agent": self.agent_type}
        )
        return function_output
    
    async def process_result(self, workspace_context: WorkspaceContext, result: Any) -> None:
        """
        Process and store the result from agent execution.
        
        This method should be overridden by subclasses to implement
        agent-specific result processing.
        
        Args:
            workspace_context: The workspace context
            result: The agent execution result
        """
        # Default implementation just logs the result type
        result_type = type(result).__name__
        self.logger.info(f"Agent produced result of type: {result_type}")

    async def post_message(self, context, agent, message: ThreadMessage) -> ThreadMessage:
        """Hook that runs after a message is added to the thread."""
        # Log message creation without exposing content
        self.logger.info(
            f"Added message to thread",
            extra={"agent": self.agent_type, "message_id": getattr(message, "id", "unknown")}
        )
        return message
    
    async def post_step(self, context, run_step: RunStep):
        """Hook that runs after each step of agent execution."""
        # Log step execution at debug level to avoid noise
        step_type = getattr(run_step, "step_type", "unknown")
        self.logger.debug(
            f"Executed agent step: {step_type}",
            extra={"agent": self.agent_type, "step_type": step_type}
        )
        return run_step


class BaseAgent(Generic[T, U]):
    """
    Base agent class implementing common agent functionality.
    
    This class provides a standardized way to create, configure, and run
    agents using the OpenAI Agent SDK, following best practices.
    """
    
    def __init__(
        self,
        agent_type: str,
        agent_name: str,
        system_message: str,
        output_class: Type[T],
        hooks_class: Type[BaseAgentHooks] = BaseAgentHooks,
        input_guardrails: List[Callable] = None,
        output_guardrails: List[Callable] = None,
        allowed_handoffs: List[str] = None,
        tools: List[Union[Tool, FunctionTool]] = None,
        model_override: str = None
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_type: Type identifier for the agent (e.g., "triage", "analysis")
            agent_name: Human-readable name for the agent
            system_message: System message/instructions for the agent
            output_class: Pydantic model class for structured output
            hooks_class: Agent hooks implementation class
            input_guardrails: List of input validation guardrail functions
            output_guardrails: List of output validation guardrail functions
            allowed_handoffs: List of agent names this agent can hand off to
            tools: List of function tools available to the agent
            model_override: Optional override for the model name from config
        """
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.system_message = system_message
        self.output_class = output_class
        self.hooks_class = hooks_class
        self.input_guardrails = input_guardrails or []
        self.output_guardrails = output_guardrails or []
        self.allowed_handoffs = allowed_handoffs or []
        self.tools = tools or []
        self.model_override = model_override
        
        self.logger = logging.getLogger(f"{agent_type}.agent")
        self._agent = None
    
    def get_model(self) -> str:
        """
        Get the appropriate model for this agent.
        
        Returns:
            Model name based on configuration or override
        """
        if self.model_override:
            return self.model_override
        
        # Get from environment variable specific to this agent
        env_var = f"MODEL_{self.agent_type.upper()}"
        model = os.environ.get(env_var)
        if model:
            return model
        
        # Get from configuration
        config = get_config()
        model_config = config.get("models", {})
        model = model_config.get(self.agent_type, "gpt-3.5-turbo")
        
        return model
    
    def create_agent(self) -> Agent:
        """
        Create and configure the OpenAI Agent.
        
        Returns:
            Configured OpenAI Agent instance
        """
        model = self.get_model()
        self.logger.info(f"Creating {self.agent_name} with model: {model}")
        
        # Format guardrails for the SDK
        formatted_guardrails = []
        for guardrail in self.input_guardrails:
            formatted_guardrails.append({
                "tag": guardrail.__name__,
                "function": guardrail
            })
        
        for guardrail in self.output_guardrails:
            formatted_guardrails.append({
                "tag": guardrail.__name__,
                "function": guardrail
            })
        
        # Create agent hooks instance
        hooks = self.hooks_class(self.agent_type, self.agent_name)
        
        # Create agent with OpenAI Agent SDK - with correct parameters based on SDK version
        
        # Create input and output guardrails according to SDK
        input_guardrails = []
        output_guardrails = []
        
        for guardrail in self.input_guardrails:
            input_guardrails.append(InputGuardrail(guardrail))
            
        for guardrail in self.output_guardrails:
            output_guardrails.append(OutputGuardrail(guardrail))
        
        # Create agent with correct parameters
        agent = Agent(
            name=self.agent_name,
            instructions=self.system_message,
            model=model,
            model_settings=ModelSettings(
                temperature=0.2,  # Lower temperature for consistent outputs
            ),
            tools=self.tools,
            hooks=hooks,
            input_guardrails=input_guardrails,
            output_guardrails=output_guardrails,
            output_type=self.output_class,  # Use the class directly, not OutputType wrapper
            handoffs=[]  # Empty list, we'll implement handoffs differently
        )
        
        self._agent = agent
        return agent
    
    async def run(
        self, 
        input_data: U, 
        workspace_context: WorkspaceContext,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Run the agent with the provided input data.
        
        Args:
            input_data: Input data for the agent
            workspace_context: Workspace context
            stream: Whether to stream the response
            
        Returns:
            Dictionary with execution results
        """
        request_id = workspace_context.request_id or f"{self.agent_type}_{int(time.time())}"
        story_id = workspace_context.story_id
        workspace_id = workspace_context.workspace_id
        
        self.logger.info(f"Running {self.agent_name} for story {story_id}")
        
        # Create trace for the agent process - SDK version
        with trace(
            workflow_name=f"{self.agent_name} Execution",
            group_id=f"{workspace_id}:{story_id}",
            metadata={  # Changed from trace_metadata to metadata for SDK compatibility
                "request_id": request_id,
                "workspace_id": workspace_id,
                "story_id": story_id,
                "agent_type": self.agent_type
            }
        ):
            # Create the agent if not already created
            if not self._agent:
                self._agent = self.create_agent()
            
            # For environments without OpenAI API key, use simplified logic
            if os.environ.get("OPENAI_API_KEY") is None:
                self.logger.warning("OpenAI API key not found, using simplified execution")
                return await self.run_simplified(input_data, workspace_context)
            
            try:
                # Prepare input for the agent (convert to string if needed)
                input_json = input_data
                if not isinstance(input_data, str):
                    input_json = json.dumps(input_data)
                
                # Run the agent with the OpenAI Agent SDK
                self.logger.info(f"Running {self.agent_name} with OpenAI Agent SDK")
                
                # Execute with streaming if requested
                if stream:
                    return await self.run_streaming(input_json, workspace_context)
                else:
                    # Regular execution - adjusted for SDK run() parameters
                    from agents import RunConfig
                    
                    # Create a run configuration
                    run_config = RunConfig(
                        workflow_name=f"{self.agent_name} Execution",
                        group_id=f"{workspace_id}:{story_id}"
                    )
                    
                    # Run with correct parameters for SDK version
                    result = await Runner.run(
                        starting_agent=self._agent,
                        input=input_json,
                        context=workspace_context,
                        run_config=run_config
                    )
                    
                    # Extract the result from the response - SDK has a different structure
                    # The SDK's RunResult has a final_output property
                    if hasattr(result, "final_output"):
                        agent_result = result.final_output
                        # Process the result
                        result_dict = self._process_result(agent_result, workspace_context)
                        return result_dict
                    # Fallback for other response structures (like our mock implementation)
                    elif hasattr(result, "items"):
                        agent_result = None
                        for item in result.items:
                            if item.type == "output_type" and hasattr(item, "value"):
                                agent_result = item.value
                                break
                        
                        if agent_result:
                            # Process the result
                            result_dict = self._process_result(agent_result, workspace_context)
                            return result_dict
                    
                    # If we couldn't extract the result through either method
                    self.logger.warning("Could not extract result from agent response")
                    return self._create_error_result(
                        "Could not extract result from agent response",
                        workspace_context
                    )
            
            except Exception as e:
                self.logger.error(f"Error running {self.agent_name}: {str(e)}")
                # Fall back to simplified implementation or return error
                if is_development():
                    self.logger.info(f"Falling back to simplified implementation")
                    return await self.run_simplified(input_data, workspace_context)
                else:
                    return self._create_error_result(str(e), workspace_context)
    
    async def run_streaming(
        self, 
        input_data: str, 
        workspace_context: WorkspaceContext
    ) -> Dict[str, Any]:
        """
        Run the agent with streaming response.
        
        Args:
            input_data: Input data for the agent
            workspace_context: Workspace context
            
        Returns:
            Dictionary with execution results
        """
        self.logger.info(f"Running {self.agent_name} with streaming")
        
        # Use the thread system for streaming responses
        try:
            client = OpenAI()
            
            # Create a thread
            thread = await client.beta.threads.create()
            self.logger.info(f"Created thread: {thread.id}")
            
            # Add a message to the thread
            message = await client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=input_data
            )
            
            # Start a run with the agent assistant
            run = await client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self._agent.id,  # Use the agent's ID as the assistant
                instructions=self.system_message,
            )
            
            # Stream the run steps
            stream_chunks = []
            async for chunk in client.beta.threads.runs.stream(
                thread_id=thread.id,
                run_id=run.id
            ):
                if hasattr(chunk, "data") and chunk.data:
                    stream_chunks.append(chunk.data)
                    # Could send this chunk to a client in a real streaming scenario
            
            # Get the final messages
            messages = await client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract the assistant's response
            for msg in messages.data:
                if msg.role == "assistant":
                    content = msg.content[0].text.value if msg.content else ""
                    try:
                        result_dict = json.loads(content)
                        return self._process_result(result_dict, workspace_context)
                    except json.JSONDecodeError:
                        # If the content is not valid JSON, return it as is
                        return {
                            "status": "success",
                            "agent": self.agent_type,
                            "result": content,
                            "streaming": True,
                            "timestamp": datetime.now().isoformat()
                        }
            
            # No assistant message found
            return self._create_error_result("No response from assistant", workspace_context)
        
        except Exception as e:
            self.logger.error(f"Error running streaming execution: {str(e)}")
            return self._create_error_result(str(e), workspace_context)
    
    async def run_simplified(
        self, 
        input_data: Any, 
        workspace_context: WorkspaceContext
    ) -> Dict[str, Any]:
        """
        Run a simplified version of the agent for development/testing.
        
        This method should be overridden by subclasses to implement
        agent-specific simplified processing.
        
        Args:
            input_data: Input data for the agent
            workspace_context: Workspace context
            
        Returns:
            Dictionary with execution results
        """
        # Default implementation just returns an error
        self.logger.warning(f"Simplified implementation not available for {self.agent_name}")
        return self._create_error_result(
            f"Simplified implementation not available for {self.agent_name}",
            workspace_context
        )
    
    def _process_result(self, result: Any, workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Process the result from agent execution.
        
        Args:
            result: The agent execution result
            workspace_context: Workspace context
            
        Returns:
            Dictionary with processed results
        """
        # Convert result to dict if needed
        result_dict = result
        if not isinstance(result, dict):
            # Support for Pydantic v2
            if hasattr(result, "model_dump") and callable(result.model_dump):
                result_dict = result.model_dump()
            # Support for Pydantic v1
            elif hasattr(result, "dict") and callable(result.dict):
                result_dict = result.dict()
            # Fallback for regular classes 
            elif hasattr(result, "__dict__"):
                result_dict = vars(result)
        
        # Add metadata
        metadata = {
            "agent": self.agent_type,
            "model": self.get_model(),
            "timestamp": datetime.now().isoformat(),
            "request_id": workspace_context.request_id,
            "workspace_id": workspace_context.workspace_id,
            "story_id": workspace_context.story_id
        }
        
        # Store in local storage for persistence
        storage_key = f"{self.agent_type}:{workspace_context.workspace_id}:{workspace_context.story_id}"
        local_storage.save_task(
            workspace_context.workspace_id,
            workspace_context.story_id,
            {
                "type": self.agent_type,
                "result": result_dict,
                "metadata": metadata
            }
        )
        
        return {
            "status": "success",
            "agent": self.agent_type,
            "result": result_dict,
            "metadata": metadata
        }
    
    def _create_error_result(self, error_message: str, workspace_context: WorkspaceContext) -> Dict[str, Any]:
        """
        Create a standardized error result.
        
        Args:
            error_message: Error message
            workspace_context: Workspace context
            
        Returns:
            Dictionary with error details
        """
        return {
            "status": "error",
            "agent": self.agent_type,
            "error": error_message,
            "workspace_id": workspace_context.workspace_id,
            "story_id": workspace_context.story_id,
            "timestamp": datetime.now().isoformat()
        }