#!/bin/bash
# Test script for running a full workflow with real APIs

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY is not set"
  echo "Please set your OpenAI API key before running this script:"
  echo "export OPENAI_API_KEY=your_api_key"
  exit 1
fi

# Check for Shortcut API key
if [ -z "$SHORTCUT_API_KEY" ] && [ -z "$SHORTCUT_API_KEY_WORKSPACE1" ]; then
  echo "Error: No Shortcut API key found"
  echo "Please set either SHORTCUT_API_KEY or SHORTCUT_API_KEY_WORKSPACE1 before running this script:"
  echo "export SHORTCUT_API_KEY=your_api_key"
  exit 1
fi

# Check for required parameters
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <workspace_id> <story_id> [workflow_type]"
  echo ""
  echo "Parameters:"
  echo "  workspace_id    The Shortcut workspace ID"
  echo "  story_id        The Shortcut story ID to test with"
  echo "  workflow_type   The workflow to test (enhance or analyse, default: analyse)"
  exit 1
fi

WORKSPACE_ID="$1"
STORY_ID="$2"
WORKFLOW_TYPE="${3:-analyse}"

# Override OpenAI model for faster testing if needed
export MODEL_TRIAGE=${MODEL_TRIAGE:-"o3-mini"}
export MODEL_ANALYSIS=${MODEL_ANALYSIS:-"o3-mini"}
export MODEL_UPDATE=${MODEL_UPDATE:-"o3-mini"}

echo "========================================================================"
echo "RUNNING FULL WORKFLOW TEST WITH REAL APIs"
echo "========================================================================"
echo "Workspace:   $WORKSPACE_ID"
echo "Story:       $STORY_ID"
echo "Workflow:    $WORKFLOW_TYPE"
echo "Triage:      $MODEL_TRIAGE"
echo "Analysis:    $MODEL_ANALYSIS"
echo "Update:      $MODEL_UPDATE"
echo "------------------------------------------------------------------------"
echo "Setting up environment..."

# Set up the Python environment
if [ -d "agent_venv" ]; then
  echo "Activating virtual environment..."
  source agent_venv/bin/activate
fi

# Install required packages
echo "Installing required packages..."
pip install aiohttp openai requests

echo "Starting test..."
echo ""

# Run the test script
python3 scripts/test_direct.py --workspace "$WORKSPACE_ID" --story "$STORY_ID" --workflow "$WORKFLOW_TYPE"
EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo "Test completed successfully!"
else
  echo ""
  echo "Test failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE