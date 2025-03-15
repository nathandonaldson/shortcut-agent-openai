# Installation Guide

## Requirements

- Python 3.9 or higher
- OpenAI API key with access to the Agent SDK (set as environment variable `OPENAI_API_KEY`)
- Shortcut API key (for accessing Shortcut stories)
- Redis (for task queue in production)

## Steps to Install the OpenAI Agents SDK

1. Create and activate a virtual environment:

```bash
python -m venv agent_venv
source agent_venv/bin/activate  # On macOS/Linux
# or
.\agent_venv\Scripts\activate    # On Windows
```

2. Install the OpenAI Agents SDK:

```bash
pip install openai-agents==0.0.4
```

3. Install other project dependencies:

```bash
pip install -r requirements.txt
```

4. Verify the installation:

```bash
python check_sdk.py
```

If the OpenAI Agents SDK is properly installed, you'll see confirmation that both the OpenAI API package and the OpenAI Agents SDK are available.

## Environment Setup

### Essential Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# API Keys
OPENAI_API_KEY=sk-your-openai-api-key
SHORTCUT_API_KEY_WORKSPACE1=your-shortcut-api-key

# Environment Configuration
ENVIRONMENT=development  # or production

# Feature Flags
USE_BACKGROUND_PROCESSING=true  # Set to false for easier debugging
USE_MOCK_AGENTS=false           # Set to true if you don't have Agent SDK access
USE_REAL_SHORTCUT=true          # Set to false for testing without Shortcut API
```

## Troubleshooting

### OpenAI Agent SDK Issues

If you encounter errors related to missing modules or classes:

- Verify the SDK version matches our requirements:
  ```bash
  pip list | grep openai-agents
  ```

- Try reinstalling with the exact version:
  ```bash
  pip uninstall -y openai-agents
  pip install openai-agents==0.0.4
  ```

- Check for import compatibility:
  ```bash
  python -c "from agents import Agent, Runner; print('SDK imports working')"
  ```

### Redis Setup

For local development with background processing:

1. Install Redis:
   ```bash
   # macOS
   brew install redis
   brew services start redis
   
   # Ubuntu
   sudo apt update
   sudo apt install redis-server
   sudo systemctl start redis-server
   ```

2. Verify Redis connection:
   ```bash
   redis-cli ping
   # Should return PONG
   ```

### Fallback Options

If you're unable to access the OpenAI Agent SDK:

1. Set `USE_MOCK_AGENTS=true` in your `.env` file
2. The system will use our mock implementation instead of the real SDK

## Next Steps

After installation, proceed to [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) for instructions on running the system locally.
