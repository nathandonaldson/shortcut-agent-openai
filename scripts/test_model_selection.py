#!/usr/bin/env python3
"""
Test script to verify model selection logic is working correctly.
"""

import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_result = load_dotenv(override=True)
    print(f"Loaded environment variables from .env file: {'Success' if load_result else 'Failed'}")
    
    # Check if we can read the file directly
    import os
    if os.path.exists('.env'):
        print("Found .env file, reading it directly:")
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    print(f"  {line.strip()}")
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

# Import our agent tools
from shortcut_agents.base_agent import BaseAgent
from shortcut_agents.triage.triage_agent import create_triage_agent
from shortcut_agents.analysis.analysis_agent import create_analysis_agent
from shortcut_agents.update.update_agent import create_update_agent

# Print environment variables
print("Environment variables:")
print(f"  MODEL_TRIAGE: {os.environ.get('MODEL_TRIAGE', 'not set')}")
print(f"  MODEL_ANALYSIS: {os.environ.get('MODEL_ANALYSIS', 'not set')}")
print(f"  MODEL_UPDATE: {os.environ.get('MODEL_UPDATE', 'not set')}")
print(f"  USE_MOCK_AGENTS: {os.environ.get('USE_MOCK_AGENTS', 'not set')}")
print(f"  USE_REAL_SHORTCUT: {os.environ.get('USE_REAL_SHORTCUT', 'not set')}")

# Create each agent type
print("\nCreating agents and checking model selection:")
triage_agent = create_triage_agent()
print(f"  Triage Agent model: {triage_agent.get_model()}")

analysis_agent = create_analysis_agent()
print(f"  Analysis Agent model: {analysis_agent.get_model()}")

update_agent = create_update_agent()
print(f"  Update Agent model: {update_agent.get_model()}")

# Check config values
print("\nConfig values:")
from config import get_config
config = get_config()
print(f"  Environment: {os.environ.get('VERCEL_ENV', 'development')}")
print(f"  Config models: {config.get('models', {})}")