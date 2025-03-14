#!/bin/bash
# Test script for running with real OpenAI API and Agent SDK
set -e

# Check if OPENAI_API_KEY is available
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable not set."
    echo "Please set your OpenAI API key before running this test:"
    echo "export OPENAI_API_KEY=your-api-key"
    exit 1
fi

# Set environment variables for testing
export USE_MOCK_AGENTS=false

# Set model override for faster/cheaper testing
export MODEL_TRIAGE=gpt-3.5-turbo
export MODEL_ANALYSIS=gpt-3.5-turbo
export MODEL_UPDATE=gpt-3.5-turbo

echo "Running tests with real SDK integration..."
echo "Using model overrides:"
echo "  Triage: $MODEL_TRIAGE"
echo "  Analysis: $MODEL_ANALYSIS"
echo "  Update: $MODEL_UPDATE"
echo ""

# Run the test script
python scripts/test_real_sdk.py