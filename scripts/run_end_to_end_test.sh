#!/bin/bash
# Script to run the end-to-end test for story creation and enhancement

# Set default values
WORKSPACE_ID=""
TAG="analyse"
WAIT_TIME=180
CHECK_INTERVAL=10

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -w|--workspace)
      WORKSPACE_ID="$2"
      shift 2
      ;;
    -t|--tag)
      TAG="$2"
      shift 2
      ;;
    --wait-time)
      WAIT_TIME="$2"
      shift 2
      ;;
    --check-interval)
      CHECK_INTERVAL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Print test configuration
echo "=== End-to-End Test Configuration ==="
echo "Workspace ID: ${WORKSPACE_ID:-"(from environment)"}"
echo "Tag: $TAG"
echo "Maximum wait time: $WAIT_TIME seconds"
echo "Check interval: $CHECK_INTERVAL seconds"
echo "======================================="

# Run the Python script
echo "Starting end-to-end test..."
python scripts/test_end_to_end.py \
  ${WORKSPACE_ID:+--workspace "$WORKSPACE_ID"} \
  --tag "$TAG" \
  --wait-time "$WAIT_TIME" \
  --check-interval "$CHECK_INTERVAL"

# Capture the exit code
EXIT_CODE=$?

# Print result based on exit code
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ End-to-end test completed successfully!"
else
  echo "❌ End-to-end test failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE 