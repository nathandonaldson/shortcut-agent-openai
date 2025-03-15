# Shortcut Enhancement System Testing Guide

This document provides a guide for testing the Shortcut Enhancement System with real APIs.

## Test Scripts

The following test scripts are available:

### End-to-End Tests with Real APIs

- `test_direct.py`: Core test script that supports both analyze and enhance workflows
- `test_enhance_workflow.sh`: Wrapper script for testing the enhance workflow
- `test_analyse_workflow.sh`: Wrapper script for testing the analyse workflow

## Setting Up Test Environment

### 1. Set Required Environment Variables

```bash
# API Keys
export OPENAI_API_KEY="sk-your-openai-api-key"
export SHORTCUT_API_KEY_WORKSPACE1="your-shortcut-api-key"

# Real API Usage
export USE_MOCK_AGENTS=false
export USE_REAL_SHORTCUT=true
```

### 2. Prepare a Test Story

In Shortcut:

1. Create a new story with a descriptive title and description
2. Add either the "enhance" or "analyse" tag depending on which workflow you want to test
3. Note the story ID (visible in the URL when viewing the story)

## Running Tests

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

## Test Output

The test will provide detailed output including:

1. **Story Details**: Basic information about the processed story
2. **Analysis Results**: Quality scores and improvement recommendations
3. **Comment Results**: Information about analysis comment added to the story
4. **Enhancement Results** (for enhance workflow): Details of changes made to the story
5. **Label Update Results**: Information about updated story labels

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

### Logs

Detailed logs are saved to the `logs` directory with timestamps. Check these logs for detailed debugging information.

## Advanced Testing

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
