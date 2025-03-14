#!/bin/bash

# Set the API key directly
export SHORTCUT_API_KEY_WORKSPACE1=d58a1ad0-4deb-44fd-a6c7-d29ccb9221fa

# Test analysis on a specific story
WORKSPACE="workspace1"
STORY_ID="308"

echo "Running analysis on $WORKSPACE story $STORY_ID"
python3 agents/analysis/cli.py --workspace $WORKSPACE analyze $STORY_ID

# Exit successfully
exit 0