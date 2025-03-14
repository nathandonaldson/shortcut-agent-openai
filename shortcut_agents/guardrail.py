"""
Guardrails for the Shortcut Enhancement System agents.

This module provides input and output guardrails for the agents to enforce
constraints and validate inputs and outputs.
"""

from typing import Dict, Any, Optional, Callable, List, Type, Awaitable
from functools import wraps

# Define the GuardrailFunctionOutput class
class GuardrailFunctionOutput:
    """Output from a guardrail function."""
    
    def __init__(self, output_info: Dict[str, Any] = None, tripwire_triggered: bool = False, reason: str = None):
        """
        Initialize the guardrail function output.
        
        Args:
            output_info: Information about the guardrail's output
            tripwire_triggered: Whether the guardrail's tripwire was triggered
            reason: Reason for the tripwire being triggered
        """
        self.output_info = output_info or {}
        self.tripwire_triggered = tripwire_triggered
        self.reason = reason
        
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output_info": self.output_info,
            "tripwire_triggered": self.tripwire_triggered,
            "reason": self.reason
        }

# Define the input_guardrail decorator
def input_guardrail(func: Callable) -> Callable:
    """
    Decorator for input guardrail functions.
    
    Args:
        func: The guardrail function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        """Wrapper function."""
        return await func(*args, **kwargs)
    
    # Set attributes for identification
    wrapper.is_guardrail = True
    wrapper.guardrail_type = "input"
    
    return wrapper

# Define the output_guardrail decorator
def output_guardrail(func: Callable) -> Callable:
    """
    Decorator for output guardrail functions.
    
    Args:
        func: The guardrail function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        """Wrapper function."""
        return await func(*args, **kwargs)
    
    # Set attributes for identification
    wrapper.is_guardrail = True
    wrapper.guardrail_type = "output"
    
    return wrapper

# Common guardrails that can be reused across agents

@input_guardrail
async def validate_story_webhook(ctx, agent, input_data: Dict[str, Any]) -> GuardrailFunctionOutput:
    """
    Validate that the webhook is a story update.
    
    Args:
        ctx: The context
        agent: The agent
        input_data: The input data to validate
        
    Returns:
        Guardrail function output
    """
    # Check if input data is a dictionary
    if not isinstance(input_data, dict):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            reason="Input data is not a dictionary"
        )
    
    # Check if it has the required keys
    if "primary_id" not in input_data and "id" not in input_data:
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            reason="Input data is missing story ID"
        )
    
    # Check if actions are present for a webhook
    if "actions" not in input_data or not input_data["actions"]:
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            reason="Input data is missing actions"
        )
    
    # All checks passed
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    )

@output_guardrail
async def validate_non_empty_result(ctx, agent, output_data: Dict[str, Any]) -> GuardrailFunctionOutput:
    """
    Validate that the output is not empty.
    
    Args:
        ctx: The context
        agent: The agent
        output_data: The output data to validate
        
    Returns:
        Guardrail function output
    """
    # Check if output data is a dictionary
    if not isinstance(output_data, dict):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            reason="Output data is not a dictionary"
        )
    
    # Check if it has content
    if not output_data:
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            reason="Output data is empty"
        )
    
    # All checks passed
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    )