#!/usr/bin/env python3
"""
Simple script to read and parse log file content directly.
This helps diagnose issues with the log follower.
"""

import os
import sys
import json
from datetime import datetime

# Get log file from command line argument
if len(sys.argv) > 1:
    log_file = sys.argv[1]
else:
    log_file = "/Users/nathandonaldson/Documents/shortcut-agent-openai/logs/example.log"

print(f"Testing log file: {log_file}")
print("-" * 80)

# Check if file exists
if not os.path.exists(log_file):
    print(f"Error: Log file '{log_file}' does not exist")
    sys.exit(1)

# Read the file directly
print(f"File size: {os.path.getsize(log_file)} bytes")
print(f"Reading entire file...")

success_count = 0
error_count = 0

with open(log_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
            
        print(f"Line {i}: ", end="")
        
        # Try to parse as JSON
        try:
            data = json.loads(line)
            timestamp = data.get("timestamp", "")
            level = data.get("level", "INFO")
            logger = data.get("logger", "unknown")
            message = data.get("message", "")
            
            # Format timestamp
            formatted_timestamp = timestamp
            if "T" in timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    formatted_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            # Print success message
            print(f"✓ JSON OK: {formatted_timestamp} | {logger} | {level} | {message}")
            success_count += 1
            
        except json.JSONDecodeError as e:
            # JSON parsing failed
            print(f"✗ JSON Error: {str(e)}")
            print(f"  Raw line: {line[:100]}..." if len(line) > 100 else f"  Raw line: {line}")
            error_count += 1

print("-" * 80)
print(f"Results: {success_count} successful, {error_count} errors")