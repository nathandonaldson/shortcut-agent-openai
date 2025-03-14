# Agent Refactoring Migration Plan

## Overview

This document outlines the migration from the original agent implementations to the refactored versions based on the `BaseAgent` class. The migration is designed to be incremental and backwards compatible.

## Changes Implemented

### 1. Updated Entry Points

The main entry points have been updated to use the refactored agents:

- `/api/webhook/handler.py`: Now imports from `agents.triage.triage_agent_refactored`
- `/api/test_pipeline.py`: Now imports from `agents.triage.triage_agent_refactored`

### 2. Added Base Agent Documentation

A comprehensive documentation file has been added at `/agents/README.md` that explains:

- Base agent architecture
- How to create new agents
- How to implement agent hooks
- Handoff mechanics
- Trace context preservation
- Testing approach

### 3. Added Unit Tests

Unit tests have been added for the refactored agents:

- `/tests/unit/agents/test_base_agent.py`: Tests for the BaseAgent class
- `/tests/unit/agents/triage/test_triage_agent.py`: Tests for the refactored triage agent

### 4. Added Integration Tests

Integration tests have been added to verify the full workflow:

- `/tests/integration/test_agent_workflow.py`: Tests agent handoffs and workflow

### 5. Enhanced Trace Context Monitoring

A new tracing utility module has been added:

- `/utils/tracing.py`: Provides utilities for preserving trace context across agent handoffs

### 6. Added Workflow Testing Tool

A command-line tool has been added for testing traced workflows:

- `/scripts/test_traced_workflow.py`: Tests the full workflow with trace visualization

## Migration Steps

### Completed Steps

1. ✅ Updated main entry points to use refactored agents
2. ✅ Added documentation for the base agent pattern
3. ✅ Added unit tests for the base agent and refactored agents
4. ✅ Added integration tests for the agent workflow
5. ✅ Enhanced trace context monitoring
6. ✅ Added workflow testing tool

### Remaining Steps

1. ✅ **Update Additional Entry Points**
   - Updated CLI tools in `/agents/analysis/cli.py` and `/agents/update/cli.py` 
   - Updated package `__init__.py` files to export refactored implementations
   - All direct imports of original agents now point to refactored versions

2. ✅ **Verify Import Integration**
   - Created test script `verify_imports.py` to verify imports
   - Fixed import compatibility issues 
   - Confirmed imports work correctly across all entry points

3. ✅ **Prepare for Validation**
   - Added mock implementation to support testing without OpenAI Agent SDK
   - Created environment setup script `setup_env.sh`
   - Created validation guide `VALIDATION_GUIDE.md`

4. **Validate In Development Environment**
   - Set up proper virtual environment with OpenAI Agent SDK
   - Run the workflow testing tool against development stories
   - Verify trace context is preserved across handoffs

5. **Deploy to Production**
   - Deploy changes to Vercel
   - Monitor agent execution in production

6. **Cleanup**
   - Once refactored agents are validated in production:
     - Rename `*_refactored.py` files to replace originals
     - Remove original agent implementations

## Testing Refactored Agents

### Unit Tests

Run unit tests for the base agent and refactored agents:

```bash
pytest tests/unit/agents/test_base_agent.py
pytest tests/unit/agents/triage/test_triage_agent.py
```

### Integration Tests

Run integration tests for the agent workflow:

```bash
pytest tests/integration/test_agent_workflow.py
```

### Workflow Testing Tool

Test the full workflow with trace visualization:

```bash
python scripts/test_traced_workflow.py --workspace your-workspace --story 12345 --workflow enhance
```

### Comprehensive Validation Script

A comprehensive validation script is provided to verify all aspects of the refactored agents:

```bash
./scripts/validate_refactored.sh your-workspace 12345 enhance
```

This script:
1. Runs unit tests for the BaseAgent class
2. Runs unit tests for the refactored TriageAgent
3. Runs integration tests for the agent workflow
4. Executes a traced workflow test
5. Provides detailed error information and troubleshooting steps if any test fails

### Migration Finalization Script

Once the refactored agents have been validated in production, use the finalization script to replace the original files:

```bash
./scripts/finalize_migration.sh
```

This script:
1. Backs up the original agent files
2. Renames the refactored files to replace the originals
3. Updates import statements in the package `__init__.py` files
4. Runs validation tests to ensure everything still works
5. Restores from backup if any issues are detected

## Trace Context Visualization

The trace context is preserved across agent handoffs and can be visualized in the logs. Each log entry includes:

- `trace_id`: Unique ID for the workflow
- `request_id`: ID of the webhook request
- `handoff_id`: ID for each agent handoff
- Source and target agents
- Timestamps
- Story and workspace context

This allows for end-to-end observation of the workflow.

## Backward Compatibility

The refactored agents maintain the same function signatures and return types as the original implementations, ensuring backward compatibility. The `process_webhook`, `process_analysis`, and `process_update` functions have identical signatures.

## Error Handling

The refactored agents include improved error handling:

- Standardized error responses
- Trace context preservation during errors
- Detailed error logging
- Simplified execution fallbacks

## Performance Considerations

The refactored agents include several performance improvements:

- Cached model selection
- Consistent tracing with minimal overhead
- Efficient context management
- Simplified execution for development environments

## Future Enhancements

After completing the migration, consider these future enhancements:

1. **Parallel Tool Execution**: Implement parallel execution of tools
2. **Streaming Support**: Enhance streaming support for long-running operations
3. **Agent Metrics**: Add metrics collection for agent performance
4. **Detailed Tracing UI**: Create a UI for visualizing trace context
5. **Agent Cache**: Implement caching for agent results