"""
Configuration management for the Shortcut Enhancement System.
Handles environment-aware configuration.
"""

import os
from typing import Dict, Any, Optional

# Determine the current environment
ENV = os.environ.get("VERCEL_ENV", "development")

def is_development() -> bool:
    """Check if the system is running in development mode"""
    return ENV == "development"

def is_production() -> bool:
    """Check if the system is running in production mode"""
    return ENV == "production"

def get_config() -> Dict[str, Any]:
    """Get the configuration for the current environment"""
    if is_production():
        from config.production import config
    else:
        from config.development import config
    
    return config

def get_value(key: str, default: Optional[Any] = None) -> Any:
    """
    Get a configuration value with fallback.
    
    Args:
        key: The configuration key
        default: Default value if key not found
        
    Returns:
        The configuration value
    """
    # First try environment variable
    env_var = os.environ.get(key)
    if env_var is not None:
        return env_var
    
    # Then try config
    config = get_config()
    return config.get(key, default)