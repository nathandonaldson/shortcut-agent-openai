# Shortcut Enhancement System Testing Guide

This document provides comprehensive instructions for testing the Shortcut Enhancement System with real APIs using the OpenAI Agent SDK.

## Test Scripts Overview

The system includes several test scripts for different testing scenarios:

| Script | Purpose |
|--------|---------|
| `test_end_to_end.py` | Tests the complete webhook-triggered workflow with real APIs |
| `test_direct.py` | Core test script supporting both analyze and enhance workflows |
| `test_enhance_workflow.sh` | Wrapper script for testing the enhance workflow |
| `test_analyse_workflow.sh` | Wrapper script for testing the analyse workflow |
| `test_real_apis.sh` | General test script for running workflows with real APIs |

## Setting Up Test Environment

### 1. Set Required Environment Variables

```bash
# API Keys
export OPENAI_API_KEY="sk-your-openai-api-key"
export SHORTCUT_API_KEY_WORKSPACE1="your-shortcut-api-key"

# Testing Configuration
export USE_MOCK_AGENTS=false    # Use real OpenAI Agent SDK
export USE_REAL_SHORTCUT=true   # Use real Shortcut API
```

### 2. Test Story Options

#### Option A: Create a test story using the script
```bash
python scripts/create_test_story.py --workspace workspace1 --tag analyse
```

#### Option B: Manually prepare a test story in Shortcut
1. Create a new story with a descriptive title and description
2. Add either the "enhance" or "analyse" tag depending on which workflow you want to test
3. Note the story ID (visible in the URL when viewing the story)

## Running End-to-End Tests

The end-to-end test creates a new story, adds the appropriate tag, and verifies the complete workflow:

```bash
# Run with default configuration
python scripts/test_end_to_end.py

# Run with specific workspace and longer wait time
python scripts/test_end_to_end.py --workspace workspace1 --wait-time 300
```

## Running Direct Tests

### Testing Analysis Workflow

```bash
# Run with specific story
./scripts/test_analyse_workflow.sh --workspace workspace1 --story 12345

# Or use environment variables
export WORKSPACE=workspace1
export STORY=12345
./scripts/test_analyse_workflow.sh
```

### Testing Enhancement Workflow

```bash
# Run with specific story
./scripts/test_enhance_workflow.sh --workspace workspace1 --story 12345

# Or use environment variables
export WORKSPACE=workspace1
export STORY=12345
./scripts/test_enhance_workflow.sh
```

### Testing with Custom Options

You can run the core test script directly with custom options:

```bash
python scripts/test_direct.py --workspace workspace1 --story 12345 --workflow enhance
```

## Test Output and Verification

The test will provide detailed output including:

1. **Story Details**: Basic information about the processed story
2. **Analysis Results**: Quality scores and improvement recommendations
3. **Comment Results**: Information about analysis comment added to the story
4. **Enhancement Results** (for enhance workflow): Details of changes made to the story
5. **Label Update Results**: Information about updated story labels

### Verification Criteria

A successful test will show:
- For analysis workflow: An analysis comment was added and the story tag was changed from "analyse" to "analysed"
- For enhancement workflow: An analysis comment was added, story content was improved, and the tag was changed from "enhance" to "enhanced"

## Workflow Explanation

### Analysis Workflow

1. Fetches the story from Shortcut API
2. Processes the story through the triage agent to detect "analyse" label
3. Runs the analysis agent to evaluate story quality
4. Posts formatted analysis results as a comment on the story
5. Updates story labels: removes "analyse", adds "analysed"

### Enhancement Workflow

1. Fetches the story from Shortcut API
2. Processes the story through the triage agent to detect "enhance" label
3. Runs the analysis agent to evaluate story quality and identify improvement areas
4. Posts formatted analysis results as a comment on the story
5. Updates the story content based on analysis recommendations
6. Posts a comment explaining the changes made
7. Updates story labels: removes "enhance", adds "enhanced"

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure your API keys are correctly set as environment variables
2. **Missing Labels**: Make sure your test story has the appropriate tag ("enhance" or "analyse") 
3. **OpenAI Rate Limits**: If you encounter OpenAI API rate limits, wait a few minutes before retrying
4. **Agent SDK Compatibility**: Make sure you're using a compatible version of the OpenAI Agent SDK

### Debugging Tools

- Check the `logs` directory for detailed logs with timestamps
- Use the `follow_logs.py` script to view logs in real-time
- Run tests with `--verbose` flag for more detailed output

## Advanced Testing Options

### Testing with Mock Shortcut API

For testing without making real Shortcut API calls:

```bash
export USE_REAL_SHORTCUT=false
./scripts/test_enhance_workflow.sh
```

### Testing with Mock Agent SDK

For testing without making real OpenAI API calls:

```bash
export USE_MOCK_AGENTS=true
./scripts/test_enhance_workflow.sh
```
