# Local Development Guide

## OpenAI Agent SDK Compatibility

The Shortcut Enhancement System uses the OpenAI Agent SDK for agent-based workflows. However, there are compatibility issues between the expected SDK structure and the actual structure in the current version (0.0.4) of the package.

### The Problem

Our codebase was designed with import paths like:
```python
from openai.types.agent import Agent, AgentHooks, GuardrailFunctionOutput
from openai.agent.runner import Runner
# etc.
```

However, the actual package structure is:
```python
from agents import Agent, AgentHooks, GuardrailFunctionOutput, Runner
# etc.
```

Additionally, there are circular import issues when trying to use the installed `agents` package alongside our local `agents` module.

### The Solution

We've implemented a graceful fallback system using mock implementations:

1. The code first tries to import from the OpenAI Agent SDK
2. If that fails, it falls back to mock implementations that simulate the SDK's behavior
3. The fallback is controlled by the `USE_MOCK_AGENTS` environment variable

This allows us to:
- Develop and test locally without the exact SDK structure
- Run the system in production with the real SDK when available

## Running With Mock Implementation

For local development, use the provided helper script:

```bash
# Make the script executable
chmod +x run_with_mock.sh

# Run verification
./run_with_mock.sh verify

# Test webhook processing
./run_with_mock.sh test-webhook workspace1 123 enhance

# Test analysis agent
./run_with_mock.sh test-analysis workspace1 123

# Test update agent
./run_with_mock.sh test-update workspace1 123

# Run the complete workflow
./run_with_mock.sh run-all workspace1 123 enhance
```

The script sets the necessary environment variables and ensures the proper Python path is used.

## Production Deployment

For production deployment, the system should work with the OpenAI Agent SDK when properly installed in the production environment. The code is designed to use the real SDK when available and fall back to mocks only when necessary.

### Ensuring Compatibility

In the future, if the OpenAI Agent SDK structure changes to match our expected import paths, or if we update our code to match the SDK's structure, we can simply set:

```
USE_MOCK_AGENTS=false
```

## Testing Both Implementations

To validate that both implementations work as expected:

1. Test locally with mocks:
   ```bash
   export USE_MOCK_AGENTS=true
   python verify_imports.py
   ```

2. Test with the real SDK (when available):
   ```bash
   export USE_MOCK_AGENTS=false
   python verify_imports.py
   ```

## Future Work

As the OpenAI Agent SDK evolves, we should periodically check if our code needs to be updated to match its structure. When the API stabilizes, we should:

1. Update our import paths to match the stable SDK structure
2. Remove the mock implementations or keep them only for testing
3. Simplify the conditional import logic

For now, the mock implementation provides a reliable way to develop and test locally while maintaining compatibility with future SDK versions.