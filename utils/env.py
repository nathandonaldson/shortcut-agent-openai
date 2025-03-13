"""
Environment variable utilities.
Loads environment variables from .env files.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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