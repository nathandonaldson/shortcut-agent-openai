#!/usr/bin/env python3
"""
Script to debug log parsing issues in the log follower.
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Set up arguments
parser = argparse.ArgumentParser(description="Debug log parsing")
parser.add_argument("--file", "-f", default="logs/example.log", help="Log file to examine")
args = parser.parse_args()

# Check if the log file exists
log_file = args.file
if not os.path.exists(log_file):
    print(f"Error: Log file '{log_file}' does not exist")
    sys.exit(1)

print(f"Examining log file: {log_file}")
print("=" * 80)

# Read and try to parse log lines
with open(log_file, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        
        print(f"\nLine {line_num}:")
        print("-" * 40)
        print(f"Raw line: {line[:100]}..." if len(line) > 100 else f"Raw line: {line}")
        
        # Try to parse as JSON
        try:
            entry = json.loads(line)
            print("✅ Successfully parsed as JSON")
            
            # Print key fields
            print(f"timestamp: {entry.get('timestamp', 'N/A')}")
            print(f"level: {entry.get('level', 'N/A')}")
            print(f"logger: {entry.get('logger', 'N/A')}")
            print(f"message: {entry.get('message', 'N/A')}")
            
            # Check for context fields
            context_fields = []
            for key, value in entry.items():
                if key not in ["timestamp", "level", "logger", "message"]:
                    context_fields.append(key)
            
            if context_fields:
                print(f"Context fields: {', '.join(context_fields)}")
            else:
                print("No additional context fields found")
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse as JSON: {str(e)}")
            
            # Try to parse as a standard log line
            parts = line.split(" - ", 3)
            if len(parts) >= 4:
                print("✅ Successfully parsed as standard log format")
                timestamp_str, component, level, message = parts
                print(f"timestamp: {timestamp_str}")
                print(f"component: {component}")
                print(f"level: {level}")
                print(f"message: {message}")
            else:
                print(f"❌ Failed to parse as standard format: found {len(parts)} parts")
        
        # Stop after 10 lines to avoid flooding output
        if line_num >= 10:
            print("\n...")
            print(f"Stopped after {line_num} lines. File has more entries.")
            break

print("\n" + "=" * 80)
print("Based on the parsing results, here's what we know:")

# Check if we could parse any JSON
with open(log_file, 'r', encoding='utf-8') as f:
    json_count = 0
    standard_count = 0
    error_count = 0
    
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        try:
            json.loads(line)
            json_count += 1
        except json.JSONDecodeError:
            parts = line.split(" - ", 3)
            if len(parts) >= 4:
                standard_count += 1
            else:
                error_count += 1

print(f"JSON format lines: {json_count}")
print(f"Standard format lines: {standard_count}")
print(f"Unparseable lines: {error_count}")

if json_count > 0 and standard_count == 0 and error_count == 0:
    print("\nConclusion: All lines are in JSON format. The follow_logs.py script should be able to parse them.")
    print("Check if your terminal supports ANSI color codes, as the script uses them for output formatting.")
elif standard_count > 0 and json_count == 0 and error_count == 0:
    print("\nConclusion: All lines are in standard log format. The follow_logs.py script should be able to parse them.")
    print("Check if your terminal supports ANSI color codes, as the script uses them for output formatting.")
elif json_count > 0 and standard_count > 0:
    print("\nConclusion: Log file contains mixed formats (JSON and standard). This might confuse the parser.")
elif error_count > 0:
    print("\nConclusion: Some lines couldn't be parsed in either format. Check the log file for corrupted entries.")
else:
    print("\nConclusion: Could not determine the log format. The file might be empty or using an unexpected format.")

print("\nSuggestion: Try modifying follow_logs.py to add some debug output about what it's reading and parsing.")