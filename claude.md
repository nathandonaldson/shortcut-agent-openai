# Shortcut Enhancement System

Vercel Domain: shortcut-agent-openai.vercel.app
Local Tailscale URL: nathans-macbook-air.lamb-cobra.ts.net
ngrok Domain: kangaroo-superb-cheaply.ngrok-free.app

## Project Overview

The Shortcut Enhancement System is an intelligent, agent-based system that automatically improves Shortcut stories based on tags. The system supports two main workflows:

1. **Full Enhancement** (triggered by "enhance" tag): Analyzes story quality, generates improvements, and updates stories with enhanced content
2. **Analysis Only** (triggered by "analyse" tag): Performs quality analysis without making changes, adding analysis results as comments

This implementation leverages Python with the OpenAI Agent SDK, deployed on Vercel using Python function handlers. The system utilizes full LLM-driven orchestration where agents intelligently decide when to hand off to other agents based on their reasoning.

## System Architecture

### Core Components

1. **Triage Agent**: Evaluates incoming webhooks and determines the appropriate workflow based on tags
2. **Analysis Agent**: Analyzes story quality and identifies improvement areas
3. **Generation Agent**: Creates enhanced content based on analysis results
4. **Update Agent**: Applies enhancements back to Shortcut
5. **Comment Agent**: Adds analysis results as comments without modifying content
6. **Notification Agent**: Informs stakeholders about enhancements or analysis

### Dual Workflow Support

The system supports two distinct workflows:

**Full Enhancement Workflow**:
- Trigger: Story tagged with "enhance"
- Process: Analysis → Generation → Update → Notification
- Result: Story content improved, tag changed from "enhance" to "enhanced"

**Analysis-Only Workflow**:
- Trigger: Story tagged with "analyse" 
- Process: Analysis → Comment → Notification
- Result: Analysis added as comment, tag changed from "analyse" to "analysed"
- Benefit: Users can review analysis before deciding to enhance

### Pure LLM-Driven Orchestration

We're using full LLM-driven orchestration where:
- Each agent has access to all other agents through handoffs
- Agents independently decide when to hand off based on their reasoning
- The flow is completely dynamic, determined by the LLMs at runtime
- No hardcoded decision trees or explicit agent chaining in code

This creates a highly flexible and intelligent workflow that can adapt to different story types and situations.

### Model Configuration

Each agent can use a different model based on its requirements:

**Development Configuration (Default):**
- Triage Agent: `o3-mini` (fastest/cheapest for initial screening)
- Analysis Agent: `o3-mini` (for development speed)
- Generation Agent: `o3-mini` (for development speed)
- Update Agent: `o3-mini` (for simple task execution)
- Comment Agent: `o3-mini` (for formatting analysis as comments)
- Notification Agent: `o3-mini` (for simple message creation)

**Production Configuration (Future):**
- Triage Agent: `gpt-3.5-turbo` (good balance of speed/capability)
- Analysis Agent: `gpt-4o` (sophisticated analysis needs)
- Generation Agent: `gpt-4o` (complex content creation)
- Update Agent: `gpt-3.5-turbo` (straightforward task execution)
- Comment Agent: `gpt-3.5-turbo` (formatting and comment creation)
- Notification Agent: `gpt-3.5-turbo` (message creation)

This configuration strategy optimizes for development speed initially, while allowing us to switch to more powerful models for production use.

## Technical Implementation

### Core Requirements

- Python 3.9+
- OpenAI Agent SDK
- Vercel Pro Plan
- Redis (for local development and KV storage)
- Anthropic API (Claude) - optional
- Shortcut API

### Project Structure

```
/
├── api/
│   ├── webhook/
│   │   └── [workspace].py        # Webhook receiver with workspace path param
│   ├── process_task.py           # Background processor for agent execution
│   └── test_pipeline.py          # End-to-end test endpoint
├── agents/
│   ├── triage.py                 # Triage agent with workflow selection
│   ├── analysis.py               # Analysis agent
│   ├── generation.py             # Generation agent
│   ├── update.py                 # Story update agent
│   ├── comment.py                # Comment agent for analysis-only workflow
│   └── notification.py           # Notification agent
├── tools/
│   ├── shortcut_tools.py         # Function tools for Shortcut API
│   ├── claude_tools.py           # Function tools for Claude API
│   └── slack_tools.py            # Function tools for Slack notifications
├── context/
│   ├── shortcut_context.py       # Shared context definitions
│   └── workspace_config.py       # Workspace configuration
├── prompts/
│   ├── triage_prompts.py         # Triage agent prompts
│   ├── analysis_prompts.py       # Analysis agent prompts
│   ├── generation_prompts.py     # Generation agent prompts
│   ├── update_prompts.py         # Update agent prompts
│   └── comment_prompts.py        # Comment agent prompts
├── utils/
│   ├── kv_store.py               # Redis/KV storage utilities
│   └── logger.py                 # Logging utilities
├── guardrails/
│   ├── input_validation.py       # Input guardrails
│   └── output_validation.py      # Output guardrails
├── lifecycle/
│   ├── hooks.py                  # Agent lifecycle hooks
│   └── callbacks.py              # Custom callback handlers
├── tracing/
│   ├── exporters.py              # Custom trace exporters
│   └── processors.py             # Trace processors
├── config/
│   ├── __init__.py               # Environment-aware configuration
│   ├── development.py            # Development-specific settings
│   └── production.py             # Production-specific settings
├── tests/
│   ├── mocks/                    # Mock data for testing
│   ├── unit/                     # Unit tests 
│   └── integration/              # Integration tests
├── scripts/
│   ├── seed_test_data.py         # Seed test data in development
│   └── setup_webhooks.py         # Automate webhook configuration
├── .env.example                  # Example environment variables
├── requirements.txt              # Python dependencies
├── vercel.json                   # Vercel configuration
└── docker-compose.yml            # Docker configuration for local development
```

### Environment-Aware Configuration

Create an environment-aware configuration system that automatically switches settings based on the environment:

```python
# config/__init__.py
import os
from typing import Dict, Any

# Determine the current environment
ENV = os.environ.get("VERCEL_ENV", "development")

# Import the correct config module
if ENV == "production":
    from .production import config
else:
    from .development import config

def get_config() -> Dict[str, Any]:
    """Get the configuration for the current environment"""
    return config

def get_value(key: str, default: Any = None) -> Any:
    """Get a configuration value with fallback"""
    return config.get(key, default)
```

```python
# config/development.py
config = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "password": "",
    },
    "models": {
        "triage": "o3-mini",
        "analysis": "o3-mini",
        "generation": "o3-mini",
        "update": "o3-mini",
        "comment": "o3-mini",
        "notification": "o3-mini",
    },
    "log_level": "DEBUG",
    "timeout": 30,  # Longer timeouts for development
    "webhook_base_url": "https://kangaroo-superb-cheaply.ngrok-free.app/api/webhook",
}
```

```python
# config/production.py
config = {
    "redis": {
        "url": None,  # Will use Vercel KV REST API
        "token": None,  # Will use Vercel KV REST API
    },
    "models": {
        "triage": "gpt-3.5-turbo",
        "analysis": "gpt-4o",
        "generation": "gpt-4o",
        "update": "gpt-3.5-turbo",
        "comment": "gpt-3.5-turbo",
        "notification": "gpt-3.5-turbo",
    },
    "log_level": "INFO",
    "timeout": 10,  # Shorter timeouts for production
    "webhook_base_url": "https://your-app.vercel.app/api/webhook",
}
```

### Redis/KV Store Configuration

The system uses Redis for task queueing and state management. Vercel KV (in production) is built on Redis, allowing us to use a consistent approach in both development and production.

#### Local Development Setup

For local development, use Docker to run Redis:

1. **Create a docker-compose.yml file:**
```yaml
version: '3'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
volumes:
  redis_data:
```

2. **Start Redis container:**
```bash
docker-compose up -d
```

3. **Redis configuration in .env.local:**
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

#### KV Store Implementation

Create a utility class that works with both local Redis and Vercel KV:

```python
# utils/kv_store.py
import os
import json
import redis
from typing import Dict, List, Optional, Any

from config import get_config

class KVStore:
    def __init__(self):
        config = get_config()
        
        # Check if we're in production (Vercel)
        if os.environ.get("VERCEL_ENV") == "production":
            # In production, use Vercel KV via REST API
            self.is_production = True
            self.kv_url = os.environ.get("KV_REST_API_URL")
            self.kv_token = os.environ.get("KV_REST_API_TOKEN")
            # You'll need to use a HTTP client for REST API calls
            self.client = None  # Initialize your Vercel KV client here
        else:
            # For local development, connect to Docker Redis
            self.is_production = False
            redis_config = config["redis"]
            self.client = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                password=redis_config["password"],
                decode_responses=True  # Auto-decode from bytes to string
            )
    
    # Rest of implementation...
```

### Mocking and Testing

Set up proper mocking for testing:

```python
# tests/mocks/shortcut_api.py
"""Mock responses for Shortcut API calls during testing"""

MOCK_STORY = {
    "id": "12345",
    "name": "Test Story",
    "description": "This is a test story for enhancement.",
    "workflow_state_id": 500001,
    "labels": [{"name": "enhance"}],
    # Other fields...
}

class MockShortcutClient:
    """Mock client for Shortcut API"""
    
    def __init__(self):
        self.stories = {"12345": MOCK_STORY.copy()}
        self.calls = []
    
    async def get_story(self, story_id):
        """Mock get story endpoint"""
        self.calls.append(("get_story", story_id))
        return self.stories.get(story_id)
    
    async def update_story(self, story_id, data):
        """Mock update story endpoint"""
        self.calls.append(("update_story", story_id, data))
        
        if story_id in self.stories:
            for key, value in data.items():
                self.stories[story_id][key] = value
                
        return self.stories.get(story_id)
```

```python
# tests/unit/test_triage_agent.py
import pytest
from unittest.mock import patch
from context.shortcut_context import ShortcutContext
from agents.triage import create_triage_agent
from tests.mocks.shortcut_api import MockShortcutClient, MOCK_STORY

@pytest.fixture
def mock_shortcut_client():
    return MockShortcutClient()

@pytest.fixture
def context():
    return ShortcutContext(
        workspace_id="test-workspace",
        story_id="12345",
        api_key="test-api-key"
    )

@patch("tools.shortcut_tools.get_shortcut_client")
async def test_triage_agent_enhance_tag(mock_get_client, mock_shortcut_client, context):
    # Setup mock
    mock_get_client.return_value = mock_shortcut_client
    
    # Create agent
    agent = create_triage_agent()
    
    # Execute agent with sample input
    result = await Runner.run(
        agent, 
        {"actions": [{"action": "update", "changes": {"labels": {"adds": ["enhance"]}}}]},
        context=context
    )
    
    # Assertions
    assert context.workflow_type == WorkflowType.ENHANCE
    assert "Analysis Agent" in [item.target_agent.name for item in result.items if item.type == "handoff_call_item"]
```

### Feature Flags

Implement feature flags for controlled rollout:

```python
# utils/feature_flags.py
import os
from typing import Dict, Any, Optional
from config import get_config

class FeatureFlags:
    """Feature flag management"""
    
    def __init__(self):
        self.config = get_config()
        self.override_flags = {}
        
        # Load flags from environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """Load feature flags from environment variables"""
        for key, value in os.environ.items():
            if key.startswith("FEATURE_"):
                flag_name = key[8:].lower()  # Strip FEATURE_ prefix
                self.override_flags[flag_name] = value.lower() in ("true", "1", "yes")
    
    def is_enabled(self, flag_name: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled"""
        # Check overrides first
        if flag_name in self.override_flags:
            return self.override_flags[flag_name]
            
        # Then check config
        flags = self.config.get("feature_flags", {})
        return flags.get(flag_name, default)
    
    def get_variant(self, flag_name: str, default: Any = None) -> Any:
        """Get a feature flag variant (for A/B testing)"""
        variants = self.config.get("feature_variants", {})
        return variants.get(flag_name, default)

# Singleton instance
feature_flags = FeatureFlags()
```

Usage:

```python
from utils.feature_flags import feature_flags

# Use in code
if feature_flags.is_enabled("use_notification_agent"):
    # Use the notification agent
    await Runner.run(notification_agent, ...)
```

### Development-Production Parity

Set up consistent environment variables for parity:

1. **Create a .env.example file**:
```
# API Keys
OPENAI_API_KEY=
SHORTCUT_API_KEY_WORKSPACE1=
SHORTCUT_API_KEY_WORKSPACE2=

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Feature Flags
FEATURE_USE_NOTIFICATION=true
FEATURE_ENABLE_ANALYTICS=false

# Environment
VERCEL_ENV=development
```

2. **Script to set up webhooks for development**:
```python
# scripts/setup_webhooks.py
"""Configure Shortcut webhooks for local development"""
import os
import argparse
import requests
from config import get_config

def setup_webhook(workspace_id, api_key, base_url):
    """Set up a webhook for the given workspace"""
    # API endpoint
    url = f"https://api.app.shortcut.com/api/v3/webhooks"
    
    # Webhook configuration
    webhook_config = {
        "description": "Enhancement System Webhook (Development)",
        "enabled": True,
        "url": f"{base_url}/{workspace_id}",
        "webhook_secret": "dev-secret-change-me",
        "events": ["story-update"]
    }
    
    # Create webhook
    response = requests.post(
        url, 
        json=webhook_config,
        headers={"Shortcut-Token": api_key}
    )
    
    if response.status_code == 201:
        print(f"✅ Webhook created for workspace {workspace_id}")
        webhook_data = response.json()
        print(f"   ID: {webhook_data['id']}")
    else:
        print(f"❌ Failed to create webhook for workspace {workspace_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")

def main():
    parser = argparse.ArgumentParser(description="Set up Shortcut webhooks for development")
    parser.add_argument("--workspace", help="Specific workspace ID to configure", required=False)
    args = parser.parse_args()
    
    config = get_config()
    base_url = config["webhook_base_url"]
    
    if args.workspace:
        # Configure a specific workspace
        api_key = os.environ.get(f"SHORTCUT_API_KEY_{args.workspace.upper()}")
        if not api_key:
            print(f"❌ No API key found for workspace {args.workspace}")
            return
        
        setup_webhook(args.workspace, api_key, base_url)
    else:
        # Configure all workspaces with API keys
        for key in os.environ:
            if key.startswith("SHORTCUT_API_KEY_"):
                workspace_id = key[18:].lower()  # Strip SHORTCUT_API_KEY_ prefix
                api_key = os.environ[key]
                setup_webhook(workspace_id, api_key, base_url)

if __name__ == "__main__":
    main()
```

3. **Script to seed test data**:
```python
# scripts/seed_test_data.py
"""Seed test data in Shortcut for development"""
import os
import argparse
import requests
from config import get_config

def create_test_story(workspace_id, api_key):
    """Create a test story in the given workspace"""
    # API endpoint
    url = f"https://api.app.shortcut.com/api/v3/stories"
    
    # Story data
    story_data = {
        "name": "Test Enhancement Story",
        "description": "This is a test story for the enhancement system. It needs improvement in clarity and structure.",
        "labels": [{"name": "test"}, {"name": "enhance"}],
        "workflow_state_id": 500001  # Assumes "To Do" state - adjust as needed
    }
    
    # Create story
    response = requests.post(
        url, 
        json=story_data,
        headers={"Shortcut-Token": api_key}
    )
    
    if response.status_code == 201:
        print(f"✅ Test story created in workspace {workspace_id}")
        story_data = response.json()
        print(f"   ID: {story_data['id']}")
        print(f"   URL: https://app.shortcut.com/{workspace_id}/story/{story_data['id']}")
    else:
        print(f"❌ Failed to create test story in workspace {workspace_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")

def main():
    parser = argparse.ArgumentParser(description="Seed test data in Shortcut")
    parser.add_argument("--workspace", help="Specific workspace ID to seed", required=False)
    args = parser.parse_args()
    
    if args.workspace:
        # Seed a specific workspace
        api_key = os.environ.get(f"SHORTCUT_API_KEY_{args.workspace.upper()}")
        if not api_key:
            print(f"❌ No API key found for workspace {args.workspace}")
            return
        
        create_test_story(args.workspace, api_key)
    else:
        # Seed all workspaces with API keys
        for key in os.environ:
            if key.startswith("SHORTCUT_API_KEY_"):
                workspace_id = key[18:].lower()  # Strip SHORTCUT_API_KEY_ prefix
                api_key = os.environ[key]
                create_test_story(workspace_id, api_key)

if __name__ == "__main__":
    main()
```

### Local Tunnel for Webhook Testing

There are multiple options for exposing your local server to receive webhooks:

#### Option 1: Tailscale (if using Tailscale network)

If you have Tailscale set up, you can use your Tailscale hostname:

```
http://nathans-macbook-air.lamb-cobra.ts.net:3000/api/webhook/[workspace]
```

#### Option 2: ngrok (recommended for public access)

Use ngrok to create a temporary public URL:

```bash
# Install ngrok with Homebrew
brew install ngrok

# Start the webhook test server and ngrok in one command
./scripts/start_webhook_server.sh

# This will use the custom domain: https://kangaroo-superb-cheaply.ngrok-free.app
# Use this URL in your webhook configuration: https://kangaroo-superb-cheaply.ngrok-free.app/api/webhook/[workspace]
```

#### Option 3: localtunnel (alternative to ngrok)

```bash
# Install localtunnel
npm install -g localtunnel

# Start your server
python scripts/test_webhooks.py

# In another terminal, start localtunnel
lt --port 3000 --subdomain shortcut-enhancement

# This gives you a URL like: https://shortcut-enhancement.loca.lt
# Use this URL in your webhook configuration
```

### Unified Logging

Create a logging system that works across environments:

```python
# utils/logger.py
import os
import json
import logging
from datetime import datetime
from pythonjsonlogger import jsonlogger
from config import get_config

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with added fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        
        # Add trace info if available
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id
            
        if hasattr(record, 'span_id'):
            log_record['span_id'] = record.span_id
            
        # Add environment
        log_record['environment'] = os.environ.get("VERCEL_ENV", "development")

def get_logger(name):
    """Get a configured logger"""
    config = get_config()
    logger = logging.getLogger(name)
    
    # Set log level from config
    log_level = config.get("log_level", "INFO")
    logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler()
    
    # Use JSON in production, readable format in development
    if os.environ.get("VERCEL_ENV") == "production":
        formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

### Deployment Checklist

Add a deployment checklist:

```
# Deployment Checklist

Before deploying to production, ensure the following:

## Configuration
- [ ] Set all required environment variables in Vercel
- [ ] Configure Vercel KV instance and link to project
- [ ] Update production model configuration
- [ ] Set appropriate logging levels

## Testing
- [ ] Run all unit tests: `pytest tests/unit`
- [ ] Run all integration tests: `pytest tests/integration`
- [ ] Verify webhook handling with test events
- [ ] Test full enhancement pipeline end-to-end

## Shortcut Configuration
- [ ] Configure production webhooks for all workspaces
- [ ] Verify API keys have appropriate permissions
- [ ] Test with real story enhancements

## Monitoring
- [ ] Set up alerts for errors
- [ ] Configure trace collection
- [ ] Set up monitoring dashboard

## Performance
- [ ] Verify function execution times within limits
- [ ] Check model token usage estimates
- [ ] Ensure KV storage patterns are efficient
```

### Switching Between Development and Production Modes

Create a utility script to toggle development/production mode locally:

```python
# scripts/toggle_mode.py
"""Toggle between development and production mode locally"""
import os
import argparse
import json
import subprocess

def update_env_file(mode):
    """Update .env.local file with the selected mode"""
    # Load current .env.local file
    env_data = {}
    if os.path.exists(".env.local"):
        with open(".env.local", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_data[key] = value
    
    # Update the VERCEL_ENV value
    env_data["VERCEL_ENV"] = mode
    
    # Update the models based on mode
    if mode == "production":
        env_data["USE_PRODUCTION_MODELS"] = "true"
    else:
        env_data["USE_PRODUCTION_MODELS"] = "false"
    
    # Write back to .env.local
    with open(".env.local", "w") as f:
        for key, value in env_data.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ Updated .env.local to use {mode} mode")

def update_vercel_dev(mode):
    """Update local Vercel dev server with environment variables"""
    try:
        subprocess.run(["vercel", "env", "pull", ".env.local"], check=True)
        print("✅ Pulled environment variables from Vercel")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to pull environment variables from Vercel")

def main():
    parser = argparse.ArgumentParser(description="Toggle between development and production mode")
    parser.add_argument("mode", choices=["development", "production"], help="Mode to switch to")
    args = parser.parse_args()
    
    # Update .env.local
    update_env_file(args.mode)
    
    # Update Vercel dev variables if needed
    if args.mode == "production":
        update_vercel_dev(args.mode)
    
    print(f"🚀 Now running in {args.mode} mode")
    print("➡️ Restart your Vercel dev server for changes to take effect")

if __name__ == "__main__":
    main()
```

### Dependency Management

Add a setup script for dependencies:

```python
# scripts/setup.py
"""Set up the development environment"""
import os
import subprocess
import platform
import argparse

def check_prerequisites():
    """Check for required prerequisites"""
    prerequisites = ["python", "pip", "node", "npm", "docker"]
    missing = []
    
    for cmd in prerequisites:
        try:
            subprocess.run([cmd, "--version"], capture_output=True)
        except FileNotFoundError:
            missing.append(cmd)
    
    return missing

def setup_python_environment():
    """Set up Python virtual environment and dependencies"""
    print("Setting up Python environment...")
    
    # Create virtual environment
    subprocess.run(["python", "-m", "venv", "venv"], check=True)
    
    # Activate virtual environment
    if platform.system() == "Windows":
        activate_cmd = "venv\\Scripts\\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    # Install dependencies
    subprocess.run(f"{activate_cmd} && pip install -r requirements.txt", shell=True, check=True)
    
    print("✅ Python environment set up successfully")

def setup_local_env():
    """Set up local environment variables"""
    print("Setting up local environment...")
    
    # Check if .env.local exists
    if not os.path.exists(".env.local"):
        # Copy from example
        if os.path.exists(".env.example"):
            subprocess.run(["cp", ".env.example", ".env.local"], check=True)
            print("✅ Created .env.local from example")
        else:
            # Create minimal .env.local
            with open(".env.local", "w") as f:
                f.write("VERCEL_ENV=development\n")
                f.write("OPENAI_API_KEY=\n")
            print("✅ Created minimal .env.local")
    else:
        print("⚠️ .env.local already exists, skipping")

def setup_docker():
    """Set up Docker containers"""
    print("Setting up Docker containers...")
    
    # Start Docker containers
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    
    print("✅ Docker containers started")

def setup_vercel():
    """Set up Vercel CLI and link project"""
    print("Setting up Vercel...")
    
    # Install Vercel CLI
    subprocess.run(["npm", "install", "-g", "vercel"], check=True)
    
    # Link project if not already linked
    if not os.path.exists(".vercel"):
        print("Linking Vercel project...")
        subprocess.run(["vercel", "link"], check=True)
    else:
        print("⚠️ Vercel project already linked, skipping")
    
    # Pull environment variables
    subprocess.run(["vercel", "env", "pull", ".env.local"], check=True)
    
    print("✅ Vercel set up successfully")

def main():
    parser = argparse.ArgumentParser(description="Set up the development environment")
    parser.add_argument("--skip-venv", action="store_true", help="Skip virtual environment setup")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker setup")
    parser.add_argument("--skip-vercel", action="store_true", help="Skip Vercel setup")
    args = parser.parse_args()
    
    # Check prerequisites
    missing = check_prerequisites()
    if missing:
        print(f"❌ Missing prerequisites: {', '.join(missing)}")
        print("Please install these tools before continuing.")
        return
    
    # Set up components
    if not args.skip_venv:
        setup_python_environment()
        
    setup_local_env()
    
    if not args.skip_docker:
        setup_docker()
        
    if not args.skip_vercel:
        setup_vercel()
    
    print("\n🚀 Setup complete! Next steps:")
    print("1. Edit .env.local to set your API keys")
    print("2. Run 'vercel dev' to start the local development server")
    print("3. Run 'python scripts/setup_webhooks.py' to set up Shortcut webhooks")

if __name__ == "__main__":
    main()
```

## Getting Started

1. Set up the development environment:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/shortcut-enhancement.git
   cd shortcut-enhancement
   
   # Run the setup script
   python scripts/setup.py
   
   # Edit .env.local to set your API keys
   
   # Start the development server
   vercel dev
   
   # In another terminal, set up webhooks (optional)
   python scripts/setup_webhooks.py
   
   # Seed test data (optional)
   python scripts/seed_test_data.py
   ```

2. Local development workflow:
   ```bash
   # Start local tunnel for webhook testing
   lt --port 3000 --subdomain shortcut-enhancement
   
   # Toggle between development and production mode
   python scripts/toggle_mode.py development
   python scripts/toggle_mode.py production
   ```

3. Deploy to Vercel:
   ```bash
   # Run deployment checklist first
   cat DEPLOYMENT_CHECKLIST.md
   
   # Deploy to production
   vercel --prod
   ```

4. Configure Vercel KV:
   - Create a KV database in Vercel Dashboard
   - Link it to your project
   - Get the KV_REST_API_URL and KV_REST_API_TOKEN values
   - Add them to environment variables

5. Configure Shortcut webhooks:
   - URL: https://your-app.vercel.app/api/webhook/{workspace_id}
   - Events: Story updates (specifically label changes)
   - Add webhook secret for security

## Dev-to-Production Best Practices

### Environment Parity

- **Use Docker for local development**: Ensures consistent Redis setup
- **Environment-aware configuration**: Same code runs in both environments with different settings
- **Feature flags**: Control feature rollout separately in dev and production
- **Testing with production-like data**: Seed realistic test data for better testing

### Graceful Degradation

Implement fallback strategies:

```python
async def process_task(task_data):
    """Process a task with graceful degradation"""
    try:
        # Create context from task data
        context = ShortcutContext(
            workspace_id=task_data['workspace_id'],
            story_id=task_data['story_id'],
            api_key=get_api_key(task_data['workspace_id'])
        )
        
        # Start with triage agent
        result = await Runner.run(
            starting_agent=triage_agent,
            input=task_data['webhook_payload'],
            context=context,
            # Set timeout based on environment
            timeout=get_config().get('timeout', 30)
        )
        
        return result
    except TimeoutError:
        # Handle timeout gracefully
        logger.warning(f"Processing timed out for task {task_data['id']}")
        
        # Save partial progress if available
        if context and context.analysis_results:
            # At least save the analysis as a comment
            await add_analysis_comment(
                context.story_id, 
                context.api_key, 
                "Analysis completed but enhancement timed out. Please try again."
            )
        
        return {"status": "timeout", "partial_results": context.analysis_results if context else None}
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        return {"status": "error", "error": str(e)}
```

### Progressive Enhancement

Start with minimal features and add complexity gradually:

1. **Phase 1**: Basic Analysis workflow only
2. **Phase 2**: Add Enhancement workflow
3. **Phase 3**: Add advanced features (workspace-specific rules, notifications)

### Monitoring and Debugging

- **Structured logging**: JSON logs in production for easy querying
- **Trace correlation**: Add trace IDs to connect logs across requests
- **Error aggregation**: Use a service like Sentry to collect errors
- **Performance monitoring**: Track agent execution times and model usage

```python
# Example of adding trace context to logs
async def process_task(task_data):
    trace_id = f"trace_{task_data['id']}"
    logger = get_logger("task_processor")
    
    # Add trace context to log records
    logger = logging.LoggerAdapter(logger, {"trace_id": trace_id})
    
    logger.info(f"Processing task {task_data['id']}")
    
    with trace(workflow_name="enhancement", trace_id=trace_id):
        # Process task
        pass
```

## Additional Resources

- [OpenAI Agent SDK Documentation](https://github.com/openai/openai-agents-python)
- [Vercel KV Documentation](https://vercel.com/docs/storage/vercel-kv)
- [Redis Documentation](https://redis.io/docs/)
- [Shortcut API Documentation](https://developer.shortcut.com/api/rest/v3)
- [Python on Vercel Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)

These additions to the claude.md file address the complete development-to-production workflow with specific tools, scripts, and best practices to ensure a smooth transition between environments.
