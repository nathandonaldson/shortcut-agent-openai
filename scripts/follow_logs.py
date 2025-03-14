#!/usr/bin/env python3
"""
Log follower script to monitor webhook and agent activity in real-time.
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

# Add parent directory to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import logger viewer utilities
from utils.logging.viewer import (
    COLORS, 
    parse_log_line, 
    format_log_entry, 
    read_log_file
)

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

def follow_log_file(file_path: str,
                   show_timestamp: bool = True,
                   filter_request_id: Optional[str] = None,
                   filter_workspace_id: Optional[str] = None,
                   filter_story_id: Optional[str] = None,
                   min_level: str = "INFO") -> None:
    """
    Follow a log file in real-time, printing new entries as they appear.
    
    Args:
        file_path: Path to the log file to follow
        show_timestamp: Whether to show timestamps
        filter_request_id: Only show entries with this request ID
        filter_workspace_id: Only show entries with this workspace ID
        filter_story_id: Only show entries with this story ID
        min_level: Minimum log level to show
    """
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
    
    # Track processed lines to avoid duplicates
    processed_lines: Set[str] = set()
    
    # Get initial file size
    try:
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        file_size = 0
        print(f"Waiting for log file to be created: {file_path}")
    
    try:
        # Main loop
        while True:
            # Check if file exists
            if not os.path.exists(file_path):
                time.sleep(1)
                continue
            
            # Check if file size has changed
            current_size = os.path.getsize(file_path)
            if current_size > file_size:
                # Open file and read new lines
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Seek to last processed position
                    f.seek(file_size)
                    
                    # Read new lines
                    for line in f:
                        line = line.strip()
                        if not line or line in processed_lines:
                            continue
                        
                        # Parse line
                        entry = parse_log_line(line)
                        if entry:
                            # Check log level
                            level = entry.get("level", "INFO").upper()
                            if level_rank.get(level, 0) < min_level_rank:
                                continue
                            
                            # Check filters
                            if filter_request_id and entry.get("request_id") != filter_request_id:
                                continue
                            
                            if filter_workspace_id and entry.get("workspace_id") != filter_workspace_id:
                                continue
                            
                            if filter_story_id and entry.get("story_id") != filter_story_id:
                                continue
                            
                            # Print formatted entry
                            print(format_log_entry(entry, show_timestamp))
                        
                        # Mark as processed
                        processed_lines.add(line)
                        
                        # Limit processed lines cache size
                        if len(processed_lines) > 10000:
                            processed_lines = set(list(processed_lines)[-5000:])
                
                # Update file size
                file_size = current_size
            
            # Wait before checking again
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nLog following stopped")

def check_webhook_logs(logs_dir: str) -> List[Dict[str, Any]]:
    """
    Check for recent webhook log files.
    
    Args:
        logs_dir: Directory containing webhook logs
        
    Returns:
        List of webhook log metadata
    """
    webhooks = []
    
    # Get all webhook log files
    for filename in os.listdir(logs_dir):
        if filename.startswith("webhook_") and filename.endswith(".json"):
            try:
                file_path = os.path.join(logs_dir, filename)
                
                # Get file modification time
                mod_time = os.path.getmtime(file_path)
                
                # Read the webhook log
                with open(file_path, 'r') as f:
                    webhook_data = json.load(f)
                
                # Extract metadata
                webhook_info = {
                    "filename": filename,
                    "file_path": file_path,
                    "timestamp": webhook_data.get("timestamp", ""),
                    "modified": datetime.fromtimestamp(mod_time).isoformat(),
                    "workspace_id": webhook_data.get("workspace_id", "unknown"),
                    "story_id": webhook_data.get("story_id", "unknown"),
                    "request_id": webhook_data.get("request_id", "unknown")
                }
                
                webhooks.append(webhook_info)
            except Exception as e:
                print(f"Error reading webhook log {filename}: {str(e)}", file=sys.stderr)
    
    # Sort by timestamp (newest first)
    webhooks.sort(key=lambda w: w.get("timestamp", ""), reverse=True)
    
    return webhooks

def main() -> None:
    """Main entry point for the log follower script."""
    parser = argparse.ArgumentParser(description="Follow logs for the Shortcut Enhancement System")
    parser.add_argument("--file", "-f", help="Log file to follow (default: logs/application.log)")
    parser.add_argument("--webhook", "-w", action="store_true", help="Follow the most recent webhook")
    parser.add_argument("--request-id", "-r", help="Filter by request ID")
    parser.add_argument("--workspace-id", "-W", help="Filter by workspace ID")
    parser.add_argument("--story-id", "-s", help="Filter by story ID")
    parser.add_argument("--level", "-l", default="INFO", help="Minimum log level to show")
    parser.add_argument("--no-timestamp", action="store_true", help="Hide timestamps")
    
    args = parser.parse_args()
    
    # Determine log file to follow
    log_file = args.file
    
    if args.webhook:
        # Get recent webhook logs
        webhook_logs = check_webhook_logs(LOG_DIR)
        
        if webhook_logs:
            # Get the most recent webhook
            webhook = webhook_logs[0]
            print(f"Following most recent webhook: {webhook['filename']}")
            print(f"Workspace: {webhook['workspace_id']}, Story: {webhook['story_id']}")
            
            # Use the request ID from the webhook
            args.request_id = webhook["request_id"]
            
            # If no specific log file is provided, use the default application log
            if not log_file:
                log_file = os.path.join(LOG_DIR, "application.log")
                
                # If that doesn't exist, try to find any log file
                if not os.path.exists(log_file):
                    log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log")]
                    if log_files:
                        log_file = os.path.join(LOG_DIR, log_files[0])
        else:
            print("No webhook logs found")
            sys.exit(1)
    
    # Default log file if none specified
    if not log_file:
        log_file = os.path.join(LOG_DIR, "application.log")
        
        # If that doesn't exist, try to find any log file
        if not os.path.exists(log_file):
            log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log")]
            if log_files:
                log_file = os.path.join(LOG_DIR, log_files[0])
            else:
                print(f"No log files found in {LOG_DIR}")
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