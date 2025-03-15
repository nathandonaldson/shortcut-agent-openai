"""
Environment variable utilities.
Loads environment variables from .env files.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# OpenAI and Agent SDK imports
try:
    from openai import AsyncOpenAI
    from agents import set_default_openai_key, set_tracing_export_api_key
    from agents.tracing import add_trace_processor
    AGENT_SDK_AVAILABLE = True
except ImportError:
    AGENT_SDK_AVAILABLE = False

# Set up logging
logger = logging.getLogger("env")

def load_env_vars(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file, defaults to .env.local for development
                and .env for production
    """
    # Determine the environment
    env = os.environ.get("VERCEL_ENV", "development")
    
    # If no env_file is specified, pick the appropriate one
    if not env_file:
        if env == "development":
            env_file = ".env.local"
            if not Path(env_file).exists():
                env_file = ".env"
        else:
            env_file = ".env"
    
    # Load environment variables from .env file if it exists
    env_path = Path(env_file)
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_file}")
        load_dotenv(env_path)
    else:
        logger.warning(f"Environment file {env_file} not found")
        
    logger.info(f"Running in {env} environment")

def get_env_or_default(key: str, default: Any = None) -> Any:
    """
    Get an environment variable or return a default value.
    
    Args:
        key: The environment variable name
        default: Default value if not found
        
    Returns:
        The environment variable value or default
    """
    return os.environ.get(key, default)

def get_required_env(key: str) -> str:
    """
    Get a required environment variable.
    
    Args:
        key: The environment variable name
        
    Returns:
        The environment variable value
        
    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Required environment variable {key} not set")
    return value

def setup_openai_configuration():
    """Configure OpenAI API keys for both SDK and tracing."""
    if not AGENT_SDK_AVAILABLE:
        logger.warning("OpenAI Agent SDK not available, skipping configuration")
        return
        
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Set the API key for the OpenAI SDK
    set_default_openai_key(api_key)
    
    # Explicitly set the same API key for tracing export
    set_tracing_export_api_key(api_key)
    
    # Enable tracing explicitly
    os.environ["OPENAI_TRACE_ENABLED"] = os.environ.get("OPENAI_TRACE_ENABLED", "true")
    
    # Set service name and version if not already set
    if "OPENAI_TRACE_SERVICE_NAME" not in os.environ:
        os.environ["OPENAI_TRACE_SERVICE_NAME"] = "shortcut-agent-app"
    
    if "OPENAI_TRACE_SERVICE_VERSION" not in os.environ:
        os.environ["OPENAI_TRACE_SERVICE_VERSION"] = "1.0.0"
    
    # Log tracing configuration
    logger.info(f"OpenAI Tracing enabled: {os.environ.get('OPENAI_TRACE_ENABLED')}")
    logger.info(f"OpenAI Trace service name: {os.environ.get('OPENAI_TRACE_SERVICE_NAME')}")
    logger.info(f"OpenAI Trace service version: {os.environ.get('OPENAI_TRACE_SERVICE_VERSION')}")
    
    # Set up trace processor
    try:
        # Import trace processor here to avoid circular imports
        from utils.logging.trace_processor import setup_trace_processor
        setup_trace_processor()
    except Exception as e:
        logger.warning(f"Failed to configure trace processor: {str(e)}")
    
    # Log configuration status
    logger.info("OpenAI API and tracing configuration complete")