#!/usr/bin/env python3
"""
Simplified log follower script for debugging purposes.
This version includes extensive debug output to diagnose JSON parsing issues.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Set up arguments
parser = argparse.ArgumentParser(description="Simple log follower")
parser.add_argument("--file", "-f", default="logs/example.log", help="Log file to follow")
parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
parser.add_argument("--print-raw", "-r", action="store_true", help="Print raw lines before parsing")
args = parser.parse_args()

# Enable debug mode
DEBUG = args.debug

# Check if the log file exists
log_file = args.file
if not os.path.exists(log_file):
    print(f"Error: Log file '{log_file}' does not exist")
    sys.exit(1)

print(f"Following log file: {log_file}")
print("Press Ctrl+C to stop")
print("-" * 80)

# Get initial file size
file_size = os.path.getsize(log_file)

# Set to store processed lines to avoid duplicates
processed_lines = set()

def debug(msg):
    """Print debug message if debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] {msg}")

try:
    # Read the entire file first
    debug(f"Reading entire file to avoid duplicate processing")
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                processed_lines.add(line)
    
    debug(f"Loaded {len(processed_lines)} existing lines")
    
    # Main loop
    while True:
        # Check if file size has changed
        current_size = os.path.getsize(log_file)
        if current_size > file_size:
            debug(f"File size changed: {file_size} -> {current_size}")
            
            # Open file and read new lines
            with open(log_file, 'r', encoding='utf-8') as f:
                # Seek to last processed position
                f.seek(file_size)
                debug(f"Seeking to position {file_size}")
                
                # Read new lines
                line_count = 0
                new_lines = 0
                for line in f:
                    line = line.strip()
                    line_count += 1
                    
                    if not line:
                        debug("Empty line, skipping")
                        continue
                    
                    if line in processed_lines:
                        debug(f"Already processed line {line_count}, skipping")
                        continue
                    
                    new_lines += 1
                    processed_lines.add(line)
                    
                    # Print raw line if requested
                    if args.print_raw:
                        print(f"RAW: {line}")
                    
                    debug(f"Processing line {line_count}: {line[:50]}..." if len(line) > 50 else f"Processing line {line_count}: {line}")
                    
                    # Try to parse JSON
                    try:
                        entry = json.loads(line)
                        debug(f"JSON parse successful: {list(entry.keys())}")
                        
                        # Extract fields
                        timestamp = entry.get("timestamp", "")
                        level = entry.get("level", "INFO")
                        logger = entry.get("logger", "unknown")
                        message = entry.get("message", "")
                        
                        debug(f"Extracted fields: timestamp={timestamp}, level={level}, logger={logger}")
                        
                        # Format timestamp
                        if timestamp:
                            try:
                                if "T" in timestamp:
                                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                                    debug(f"Formatted timestamp: {timestamp}")
                            except Exception as e:
                                debug(f"Error formatting timestamp: {str(e)}")
                        
                        # Print simplified log entry with context info
                        print(f"{timestamp} | {logger:20s} | {level:7s} | {message}")
                        
                        # Add key context fields if available
                        context_items = []
                        for key in ["request_id", "workspace_id", "story_id", "trace_id", "event"]:
                            if key in entry and entry[key]:
                                context_items.append(f"{key}={entry[key]}")
                        
                        if context_items:
                            print(f"  → {' | '.join(context_items)}")
                        
                    except json.JSONDecodeError as e:
                        # If not JSON, try to handle common errors
                        debug(f"JSON decode error: {str(e)}")
                        
                        # Try to fix common JSON issues
                        if "Expecting ',' delimiter" in str(e) or "Unterminated string" in str(e):
                            debug("Attempting to fix malformed JSON")
                            # Try to fix truncated JSON
                            if not line.endswith('}'):
                                fixed_line = line + '}'
                                try:
                                    entry = json.loads(fixed_line)
                                    debug("Fixed JSON by adding closing brace")
                                    
                                    # Extract and print as above
                                    timestamp = entry.get("timestamp", "")
                                    level = entry.get("level", "INFO")
                                    logger = entry.get("logger", "unknown")
                                    message = entry.get("message", "")
                                    
                                    # Format and print
                                    if "T" in timestamp:
                                        try:
                                            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                                            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                                        except:
                                            pass
                                    
                                    print(f"{timestamp} | {logger:20s} | {level:7s} | {message} (fixed JSON)")
                                    continue
                                except:
                                    debug("Failed to fix JSON")
                        
                        # If all attempts failed, just print the raw line
                        print(f"Error parsing: {line[:100]}..." if len(line) > 100 else line)
            
            debug(f"Processed {line_count} lines, {new_lines} new")
            
            # Update file size
            file_size = current_size
        
        # Wait before checking again
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\nLog following stopped")