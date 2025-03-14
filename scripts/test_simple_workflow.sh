#!/bin/bash
# Test script for running the simplified workflow integration test
set -e

# Set environment variables for testing
export USE_MOCK_AGENTS=true

echo "Running simplified workflow integration test..."

# Run the test script
python scripts/test_simple_workflow.py