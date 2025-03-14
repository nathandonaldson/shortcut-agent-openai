#!/usr/bin/env python3
"""
Fixed log follower with minimal dependencies and robust JSON handling.
This version should work reliably in all terminal environments.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Define terminal color codes with fallback for terminals that don't support ANSI
try:
    # Try to print a colored character to test ANSI support
    print("\033[32mTesting ANSI color support...\033[0m")
    USE_COLORS = True
except Exception:
    USE_COLORS = False

# Color codes for terminal output
COLORS = {
    "RESET": "\033[0m" if USE_COLORS else "",
    "BOLD": "\033[1m" if USE_COLORS else "",
    "RED": "\033[31m" if USE_COLORS else "",
    "GREEN": "\033[32m" if USE_COLORS else "",
    "YELLOW": "\033[33m" if USE_COLORS else "",
    "BLUE": "\033[34m" if USE_COLORS else "",
    "MAGENTA": "\033[35m" if USE_COLORS else "",
    "CYAN": "\033[36m" if USE_COLORS else "",
    "WHITE": "\033[37m" if USE_COLORS else "",
    "GRAY": "\033[90m" if USE_COLORS else "",
}

# Level color mapping
LEVEL_COLORS = {
    "DEBUG": COLORS["GRAY"],
    "INFO": COLORS["GREEN"],
    "WARNING": COLORS["YELLOW"],
    "ERROR": COLORS["RED"],
    "CRITICAL": COLORS["RED"] + COLORS["BOLD"],
}

# Component color mapping
COMPONENT_COLORS = {
    "webhook": COLORS["CYAN"],
    "triage": COLORS["BLUE"],
    "analysis": COLORS["GREEN"],
    "generation": COLORS["YELLOW"],
    "update": COLORS["MAGENTA"],
    "notification": COLORS["WHITE"],
    "openai.trace": COLORS["GRAY"],
    "openai.span": COLORS["GRAY"],
}

def get_color_for_level(level):
    """Get the color code for a log level."""
    return LEVEL_COLORS.get(level.upper(), COLORS["WHITE"])

def get_color_for_component(component):
    """Get the color code for a component."""
    for key, color in COMPONENT_COLORS.items():
        if key in component.lower():
            return color
    return COLORS["WHITE"]

def parse_json_log(line):
    """Parse a JSON log line safely."""
    try:
        return json.loads(line.strip())
    except:
        return None

def format_log_entry(entry, show_timestamp=True):
    """Format a log entry for display."""
    # Extract basic fields
    timestamp = entry.get("timestamp", "")
    level = entry.get("level", "INFO")
    component = entry.get("logger", entry.get("component", "unknown"))
    message = entry.get("message", "")
    
    # Format timestamp
    timestamp_str = ""
    if show_timestamp and timestamp:
        try:
            if "T" in timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = timestamp
        except:
            timestamp_str = timestamp
    
    # Get colors
    level_color = get_color_for_level(level)
    component_color = get_color_for_component(component)
    
    # Format the log entry
    if show_timestamp:
        line = f"{COLORS['GRAY']}{timestamp_str}{COLORS['RESET']} | "
    else:
        line = ""
        
    line += f"{component_color}{component[:20]:20s}{COLORS['RESET']} | "
    line += f"{level_color}{level:7s}{COLORS['RESET']} | "
    line += message
    
    # Add important context fields
    context_fields = []
    for key in ["request_id", "workspace_id", "story_id", "trace_id", "event"]:
        if key in entry and entry[key]:
            context_fields.append(f"{COLORS['BOLD']}{key}{COLORS['RESET']}={entry[key]}")
    
    if context_fields:
        line += f"\n  {COLORS['GRAY']}→ {' | '.join(context_fields)}{COLORS['RESET']}"
    
    return line

def follow_log_file(file_path, 
                   show_timestamp=True,
                   filter_request_id=None,
                   filter_workspace_id=None,
                   filter_story_id=None,
                   min_level="INFO"):
    """Follow a log file, printing formatted entries as they arrive."""
    # Define log level ranking
    level_rank = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4
    }
    
    # Get minimum level rank
    min_level_rank = level_rank.get(min_level.upper(), 0)
    
    # Track processed lines
    processed_lines = set()
    
    # Initialize - read the entire file first to avoid duplicating old entries
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    processed_lines.add(line)
        
        print(f"Loaded {len(processed_lines)} existing log entries")
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        print(f"Waiting for log file to be created: {file_path}")
        file_size = 0
    
    # Main loop
    try:
        while True:
            if not os.path.exists(file_path):
                time.sleep(1)
                continue
            
            current_size = os.path.getsize(file_path)
            if current_size > file_size:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(file_size)
                    
                    for line in f:
                        line = line.strip()
                        if not line or line in processed_lines:
                            continue
                        
                        processed_lines.add(line)
                        
                        # Parse the line
                        entry = parse_json_log(line)
                        if not entry:
                            # If not valid JSON, print the raw line
                            print(f"Invalid log format: {line[:100]}..." if len(line) > 100 else line)
                            continue
                        
                        # Apply filters
                        level = entry.get("level", "INFO").upper()
                        if level_rank.get(level, 0) < min_level_rank:
                            continue
                        
                        if filter_request_id and entry.get("request_id") != filter_request_id:
                            continue
                        
                        if filter_workspace_id and entry.get("workspace_id") != filter_workspace_id:
                            continue
                        
                        if filter_story_id and entry.get("story_id") != filter_story_id:
                            continue
                        
                        # Print the formatted entry
                        print(format_log_entry(entry, show_timestamp))
                
                # Update file size
                file_size = current_size
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nLog following stopped")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Follow Shortcut Enhancement System logs")
    parser.add_argument("--file", "-f", help="Log file to follow")
    parser.add_argument("--request-id", "-r", help="Filter by request ID")
    parser.add_argument("--workspace-id", "-w", help="Filter by workspace ID")
    parser.add_argument("--story-id", "-s", help="Filter by story ID")
    parser.add_argument("--level", "-l", default="INFO", help="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--no-timestamp", action="store_true", help="Hide timestamps")
    
    args = parser.parse_args()
    
    # Default log directory
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    
    # Determine log file to follow
    log_file = args.file
    if not log_file:
        log_file = os.path.join(log_dir, "application.log")
        
        # If default doesn't exist, try example.log or find any log file
        if not os.path.exists(log_file):
            example_log = os.path.join(log_dir, "example.log")
            if os.path.exists(example_log):
                log_file = example_log
            else:
                log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
                if log_files:
                    log_file = os.path.join(log_dir, log_files[0])
                else:
                    print(f"No log files found in {log_dir}")
                    sys.exit(1)
    
    # Print summary of what we're doing
    print(f"Following log file: {log_file}")
    if args.request_id:
        print(f"Filtering by request ID: {args.request_id}")
    if args.workspace_id:
        print(f"Filtering by workspace ID: {args.workspace_id}")
    if args.story_id:
        print(f"Filtering by story ID: {args.story_id}")
    print(f"Minimum log level: {args.level}")
    print("Press Ctrl+C to stop")
    print("-" * 80)
    
    # Follow the log file
    follow_log_file(
        file_path=log_file,
        show_timestamp=not args.no_timestamp,
        filter_request_id=args.request_id,
        filter_workspace_id=args.workspace_id,
        filter_story_id=args.story_id,
        min_level=args.level
    )

if __name__ == "__main__":
    main()