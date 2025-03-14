# Using the OpenAI Agent SDK Directly

The OpenAI Agent SDK (openai-agents) package has a different structure than what our code currently expects. To use the SDK directly, we need to update our import statements.

## Quick Start

I've created a script to automatically fix the imports across the codebase:

```bash
# Make the script executable
chmod +x fix_sdk_imports.py

# Run the script to fix imports
./fix_sdk_imports.py
```

The script will:
1. Find all Python files that use OpenAI Agent SDK imports
2. Replace the old import statements with the correct ones
3. Update any class usage that needs adjustment

## Manual Changes

If you prefer to make the changes manually, here are the key replacements needed:

### Import Statements

| Current Import | New Import |
|----------------|------------|
| `from openai.types.agent import Agent, AgentHooks, ...` | `from agents import Agent, AgentHooks, ...` |
| `from openai.types.agent.function_tools import ...` | `from agents.tool import ...` |
| `from openai.types.agent.hooks import ...` | `from agents.lifecycle import ...` |
| `from openai.types.shared_params import ModelSettings` | `from agents import ModelSettings` |
| `from openai.types.agent.utils import OutputType` | `from agents import AgentOutputSchema as OutputType` |
| `from openai.types.agent.guardrails import ...` | `from agents.guardrail import ...` |
| `from openai.types.agent.tracing import ...` | `from agents.tracing import ...` |
| `from openai.agent.runner import Runner` | `from agents import Runner` |
| `from openai.types.beta.threads import ThreadMessage` | Use `dict` instead |

### Class Usage

| Current Usage | New Usage |
|---------------|-----------|
| `OutputType(result_type=MyClass)` | `{'result_type': MyClass}` |
| `ThreadMessage` | `dict` |
| `Handoffs(...)` | `Handoff(...)` |

## Testing Your Changes

After making the changes, test your codebase:

```bash
# Verify imports
python verify_imports.py

# Test the full workflow
python api/test_pipeline.py --workspace workspace1 --story 123 --tag enhance
```

## SDK Installation

Make sure to install the SDK in your environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the SDK
pip install openai-agents

# Install other requirements
pip install -r requirements.txt
```

## Agent Factory Pattern

Our codebase uses a factory pattern (`create_*_agent()` functions) to abstract agent creation. After updating the imports, these factory functions should work with the real SDK.

## Environment Variables

Set the following environment variables:

```bash
# Use the real SDK (not mocks)
export USE_MOCK_AGENTS=false

# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here
```