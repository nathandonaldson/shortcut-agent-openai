#!/bin/bash
# Test script for running the full workflow integration test
set -e

# Set environment variables for testing
export USE_MOCK_AGENTS=true

echo "Running full workflow integration test..."

# Run the test script
python scripts/test_full_workflow.py