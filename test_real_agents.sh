#!/bin/bash
# Test the agents with real OpenAI Agent SDK (or graceful fallback)

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Testing with real OpenAI Agent SDK${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: OPENAI_API_KEY is not set.${NC}"
    echo -e "${YELLOW}Testing will proceed but may fall back to mocks.${NC}"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted.${NC}"
        exit 1
    fi
fi

# Set environment variables for testing
export PYTHONPATH=$PWD
export USE_MOCK_AGENTS=false

# Parameters
WORKSPACE_ID=${1:-"workspace1"}
STORY_ID=${2:-"308"}
LABEL=${3:-"enhance"}
MODEL=${4:-"gpt-4o-mini"}  # Default to gpt-4o-mini

echo -e "${BLUE}Using the following parameters:${NC}"
echo -e "Workspace ID: ${YELLOW}$WORKSPACE_ID${NC}"
echo -e "Story ID:     ${YELLOW}$STORY_ID${NC}"
echo -e "Label:        ${YELLOW}$LABEL${NC}"
echo -e "Model:        ${YELLOW}$MODEL${NC}"
echo

# Make a direct API call to the webhook handler
echo -e "${BLUE}Making a direct API call to test the refactored agent...${NC}"

# Create a temporary webhook payload file
PAYLOAD_FILE=$(mktemp)
cat > "$PAYLOAD_FILE" << EOF
{
    "action": "update",
    "changes": {
        "labels": {
            "adds": [{"name": "$LABEL"}],
            "removes": []
        }
    },
    "primary_id": "$STORY_ID",
    "id": "$STORY_ID",
    "name": "Test Story",
    "story_type": "feature",
    "description": "This is a test story for webhook testing",
    "resource": {
        "id": "$STORY_ID",
        "entity_type": "story"
    }
}
EOF

# Run with Python directly using the webhook handler
echo -e "${BLUE}Running webhook handler directly with Python...${NC}"

# Create a Python script
PYTHON_FILE=$(mktemp)
cat > "$PYTHON_FILE" << 'PYTHONCODE'
import asyncio
import json
import os
import sys
from api.webhook.handler import handle_webhook

async def test():
    # Get parameters from command line
    workspace_id = sys.argv[1]
    payload_file = sys.argv[2]
    
    # Set environment variables
    os.environ[f'SHORTCUT_API_KEY_{workspace_id.upper()}'] = 'test-api-key'
    os.environ['USE_MOCK_AGENTS'] = 'false'
    os.environ['MODEL_TRIAGE'] = sys.argv[3]  # Set model from command line argument
    
    # Load webhook payload
    with open(payload_file, 'r') as f:
        webhook_data = json.load(f)
    
    # Call the webhook handler
    result = await handle_webhook(workspace_id, webhook_data, f'/api/webhook/{workspace_id}', '127.0.0.1')
    
    # Pretty print the result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
PYTHONCODE

# Run the Python script
PYTHONPATH=$PWD python3 "$PYTHON_FILE" "$WORKSPACE_ID" "$PAYLOAD_FILE" "$MODEL"

# Clean up
rm "$PYTHON_FILE"

# Clean up
rm "$PAYLOAD_FILE"

echo
echo -e "${BLUE}The response above shows the result of the webhook handler.${NC}"
echo -e "${BLUE}Check the logs to see the full trace of the real agent execution.${NC}"
echo -e "${BLUE}If you see a success response, the refactored agent is ready for production!${NC}"