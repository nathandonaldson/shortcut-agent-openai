#!/bin/bash
# Setup script for the logging system

# Create log directories
mkdir -p logs/traces

# Create an example log file
touch logs/application.log

echo "Logging system setup complete. Directories created:"
echo "- logs/ - Main logs directory"
echo "- logs/traces/ - OpenAI Agent SDK trace storage"
echo ""
echo "You can now use the logging system with:"
echo "- python scripts/follow_logs.py - to follow logs in real-time"
echo "- python scripts/log_example.py - to run a logging example"
echo ""
echo "See utils/logging/README.md for more information on the logging system."