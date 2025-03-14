# Validation Guide for Refactored Agents

This guide explains how to validate the refactored agent implementation in a development environment.

## Environment Setup

The refactored agent implementation requires the OpenAI Agent SDK, which has specific version requirements. 

### Prerequisites

- Python 3.9+
- OpenAI API key with access to the OpenAI Agent SDK
- Shortcut API key for workspace

### Setup Virtual Environment

1. Create a virtual environment:
   ```bash
   python -m venv agent_venv
   source agent_venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -U pip
   pip install -r requirements.txt pytest
   ```

3. Set the required environment variables:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   export SHORTCUT_API_KEY_WORKSPACE1=your_shortcut_api_key
   ```

## Basic Validation

Run the validation script to verify imports:

```bash
python test_refactored_agents.py
```

This will test that all the refactored agent modules can be imported correctly.

## Running Tests

1. Run the unit tests for BaseAgent:
   ```bash
   pytest tests/unit/agents/test_base_agent.py -v
   ```

2. Run the unit tests for TriageAgent:
   ```bash
   pytest tests/unit/agents/triage/test_triage_agent.py -v
   ```

3. Run the integration tests:
   ```bash
   pytest tests/integration/test_agent_workflow.py -v
   ```

## Testing Traced Workflow

To test the full agent workflow with trace context:

```bash
python scripts/test_traced_workflow.py --workspace workspace1 --story 308 --workflow enhance
```

This will simulate the full workflow from triage through analysis and update, verifying that trace context is properly preserved across handoffs.

## Comprehensive Validation

For comprehensive validation, use the validation script:

```bash
./scripts/validate_refactored.sh workspace1 308 enhance
```

This will run all unit tests, integration tests, and the traced workflow test in sequence.

## Next Steps

Once validated in development:

1. Deploy to production and monitor for issues
2. Run the validation script against production stories
3. If everything works correctly, finalize the migration:
   ```bash
   ./scripts/finalize_migration.sh
   ```

## Troubleshooting

### OpenAI Agent SDK Issues

If you encounter issues with the OpenAI Agent SDK imports, verify:

1. That you have the correct version of the OpenAI package installed
2. That you have access to the OpenAI Agent SDK
3. That your OpenAI API key has the necessary permissions

### Environment Issues

If you encounter environment issues:

1. Make sure PYTHONPATH includes the project root:
   ```bash
   export PYTHONPATH=/path/to/shortcut-agent-openai
   ```

2. Verify that all dependencies are installed in your virtual environment:
   ```bash
   pip list | grep openai
   ```

### Test Failures

If tests fail:

1. Check the error messages for specific issues
2. Verify that the mock implementations are working correctly
3. Look for any missing environment variables