#!/bin/bash
# 
# Test script for running the analyse workflow with real APIs
#

# Default values
WORKSPACE=${WORKSPACE:-"workspace1"}
STORY=${STORY:-"12345"}
WORKFLOW="analyse"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --story)
      STORY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Environment setup
export USE_MOCK_AGENTS=false
export USE_REAL_SHORTCUT=true

# Run the test
echo "Running analyse workflow test with:"
echo "  Workspace: $WORKSPACE"
echo "  Story: $STORY"
echo ""

python scripts/test_direct.py --workspace "$WORKSPACE" --story "$STORY" --workflow "$WORKFLOW"