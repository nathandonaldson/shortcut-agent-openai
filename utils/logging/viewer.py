"""
Log viewer utility for debugging webhook processing and agent execution.
"""

import os
import sys
import json
import argparse
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")

# ANSI color codes for terminal output
COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "GRAY": "\033[90m",
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

# Level color mapping
LEVEL_COLORS = {
    "DEBUG": COLORS["GRAY"],
    "INFO": COLORS["GREEN"],
    "WARNING": COLORS["YELLOW"],
    "ERROR": COLORS["RED"],
    "CRITICAL": COLORS["RED"] + COLORS["BOLD"],
}

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a log line into a structured object.
    
    Args:
        line: The log line to parse
        
    Returns:
        Parsed log entry or None if couldn't parse
    """
    try:
        # Try to parse as JSON first
        # First strip any leading/trailing whitespace, as it might interfere with JSON parsing
        line = line.strip()
        
        # Debugging: print raw line content
        print(f"[DEBUG] Parsing line: {line[:50]}..." if len(line) > 50 else f"[DEBUG] Parsing line: {line}")
        
        try:
            data = json.loads(line)
            print(f"[DEBUG] Successfully parsed JSON object with keys: {', '.join(list(data.keys()))}")
            return data
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {str(e)}")
            # If the error is unexpected end of data, we might have truncated JSON
            if "Expecting ',' delimiter" in str(e) or "Unterminated string" in str(e):
                print("[DEBUG] Trying to fix malformed JSON...")
                # Try to fix potential truncation by adding closing brace
                if not line.endswith('}'):
                    fixed_line = line + '}'
                    try:
                        data = json.loads(fixed_line)
                        print("[DEBUG] Fixed JSON parse successful")
                        return data
                    except json.JSONDecodeError:
                        print("[DEBUG] Failed to fix JSON with simple repair")
                
        # If JSON parsing failed, try to parse as a standard log line
        print("[DEBUG] Trying standard log format")
        try:
            # Example format: 2023-01-01 12:34:56,789 - component - LEVEL - Message
            parts = line.split(" - ", 3)
            if len(parts) >= 4:
                timestamp_str, component, level, message = parts
                
                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S,%f")
                except ValueError:
                    timestamp = datetime.now()  # Fallback
                
                data = {
                    "timestamp": timestamp.isoformat(),
                    "logger": component.strip(),
                    "level": level.strip(),
                    "message": message.strip()
                }
                print("[DEBUG] Parsed standard log format successfully")
                return data
            else:
                print(f"[DEBUG] Standard format failed: found {len(parts)} parts, expected 4")
        except Exception as e:
            print(f"[DEBUG] Error parsing standard format: {str(e)}")
        
        print("[DEBUG] Could not parse log line with any method")
        return None
    except Exception as e:
        print(f"[DEBUG] Unexpected error while parsing log line: {str(e)}")
        return None

def get_component_color(component: str) -> str:
    """
    Get the color code for a component.
    
    Args:
        component: Component name
        
    Returns:
        ANSI color code
    """
    for key, color in COMPONENT_COLORS.items():
        if key in component.lower():
            return color
    return COLORS["WHITE"]

def get_level_color(level: str) -> str:
    """
    Get the color code for a log level.
    
    Args:
        level: Log level
        
    Returns:
        ANSI color code
    """
    return LEVEL_COLORS.get(level.upper(), COLORS["WHITE"])

def format_log_entry(entry: Dict[str, Any], show_timestamp: bool = True) -> str:
    """
    Format a log entry for terminal display.
    
    Args:
        entry: Parsed log entry
        show_timestamp: Whether to show the timestamp
        
    Returns:
        Formatted log line
    """
    # Debugging: print the raw entry
    print(f"[DEBUG] Formatting entry: {str(entry)[:100]}...")
    
    # Extract common fields
    timestamp = entry.get("timestamp", "")
    component = entry.get("logger", entry.get("component", "unknown"))
    level = entry.get("level", "INFO")
    message = entry.get("message", "")
    
    print(f"[DEBUG] Extracted fields: timestamp={timestamp}, component={component}, level={level}")
    
    # Format timestamp if present and requested
    timestamp_str = ""
    if show_timestamp and timestamp:
        try:
            # Convert ISO format to readable format
            if "T" in timestamp:
                print(f"[DEBUG] Converting ISO timestamp: {timestamp}")
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = timestamp
            timestamp_str = f"{COLORS['GRAY']}{timestamp_str}{COLORS['RESET']} | "
            print(f"[DEBUG] Formatted timestamp: {timestamp_str}")
        except Exception as e:
            print(f"[DEBUG] Error formatting timestamp: {str(e)}")
            timestamp_str = f"{COLORS['GRAY']}{timestamp}{COLORS['RESET']} | "
    
    # Get colors
    component_color = get_component_color(component)
    level_color = get_level_color(level)
    
    # Format component and level
    component_str = f"{component_color}{component[:20]:20s}{COLORS['RESET']}"
    level_str = f"{level_color}{level:8s}{COLORS['RESET']}"
    
    # Build full line
    line = f"{timestamp_str}{component_str} | {level_str} | {message}"
    
    # Add contextual information if present
    context_fields = []
    for key, value in entry.items():
        if key not in ["timestamp", "logger", "component", "level", "message"] and value is not None:
            # Format the value based on type
            if isinstance(value, (dict, list)):
                try:
                    value_str = json.dumps(value, ensure_ascii=False)
                except Exception as e:
                    print(f"[DEBUG] Error serializing complex value for key {key}: {str(e)}")
                    value_str = str(value)
            else:
                value_str = str(value)
            
            # Add to context fields
            context_fields.append(f"{COLORS['BOLD']}{key}{COLORS['RESET']}={value_str}")
    
    # Add context if available
    if context_fields:
        context_str = " ".join(context_fields)
        line += f"\n{COLORS['GRAY']}    {context_str}{COLORS['RESET']}"
    
    print(f"[DEBUG] Final formatted line: {line[:100]}...")
    return line

def read_log_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read and parse a log file.
    
    Args:
        file_path: Path to the log file
        
    Returns:
        List of parsed log entries
    """
    entries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                entry = parse_log_line(line)
                if entry:
                    entries.append(entry)
    except Exception as e:
        print(f"Error reading log file {file_path}: {str(e)}", file=sys.stderr)
    
    return entries

def filter_log_entries(entries: List[Dict[str, Any]], 
                      request_id: Optional[str] = None,
                      workspace_id: Optional[str] = None,
                      story_id: Optional[str] = None,
                      trace_id: Optional[str] = None,
                      min_level: str = "DEBUG") -> List[Dict[str, Any]]:
    """
    Filter log entries by various criteria.
    
    Args:
        entries: List of log entries to filter
        request_id: Filter by request ID
        workspace_id: Filter by workspace ID
        story_id: Filter by story ID
        trace_id: Filter by trace ID
        min_level: Minimum log level to include
        
    Returns:
        Filtered log entries
    """
    # Define log level ranking
    level_rank = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4
    }
    
    # Get the minimum level rank
    min_level_rank = level_rank.get(min_level.upper(), 0)
    
    # Filter entries
    filtered = []
    for entry in entries:
        # Check level
        level = entry.get("level", "INFO").upper()
        if level_rank.get(level, 0) < min_level_rank:
            continue
        
        # Check request ID
        if request_id and entry.get("request_id") != request_id:
            continue
        
        # Check workspace ID
        if workspace_id and entry.get("workspace_id") != workspace_id:
            continue
        
        # Check story ID
        if story_id and entry.get("story_id") != story_id:
            continue
        
        # Check trace ID
        if trace_id and entry.get("trace_id") != trace_id:
            continue
        
        # Include this entry
        filtered.append(entry)
    
    return filtered

def print_logs(entries: List[Dict[str, Any]], show_timestamp: bool = True) -> None:
    """
    Print log entries to the console.
    
    Args:
        entries: Log entries to print
        show_timestamp: Whether to show timestamps
    """
    for entry in entries:
        print(format_log_entry(entry, show_timestamp))

def find_request_ids(entries: List[Dict[str, Any]]) -> List[str]:
    """
    Find all request IDs in the log entries.
    
    Args:
        entries: Log entries to search
        
    Returns:
        List of unique request IDs
    """
    request_ids = set()
    
    for entry in entries:
        if "request_id" in entry and entry["request_id"]:
            request_ids.add(entry["request_id"])
    
    return sorted(list(request_ids))

def find_traces(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find all traces in the log entries.
    
    Args:
        entries: Log entries to search
        
    Returns:
        List of trace information
    """
    traces = {}
    
    for entry in entries:
        if "trace_id" in entry and entry["trace_id"]:
            trace_id = entry["trace_id"]
            
            if trace_id not in traces:
                traces[trace_id] = {
                    "trace_id": trace_id,
                    "workflow": entry.get("workflow_name", "unknown"),
                    "workspace_id": entry.get("workspace_id", "unknown"),
                    "story_id": entry.get("story_id", "unknown"),
                    "first_seen": entry.get("timestamp", ""),
                    "entries": 0
                }
            
            traces[trace_id]["entries"] += 1
            
            # Update timestamp if this entry is newer
            if "timestamp" in entry:
                if not traces[trace_id]["first_seen"] or entry["timestamp"] < traces[trace_id]["first_seen"]:
                    traces[trace_id]["first_seen"] = entry["timestamp"]
    
    return list(traces.values())

def main() -> None:
    """Main entry point for the log viewer CLI."""
    parser = argparse.ArgumentParser(description="Shortcut Enhancement System Log Viewer")
    parser.add_argument("--log-file", "-f", help="Path to log file (default: logs/application.log)")
    parser.add_argument("--request-id", "-r", help="Filter by request ID")
    parser.add_argument("--workspace-id", "-w", help="Filter by workspace ID")
    parser.add_argument("--story-id", "-s", help="Filter by story ID")
    parser.add_argument("--trace-id", "-t", help="Filter by trace ID")
    parser.add_argument("--level", "-l", default="DEBUG", help="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--no-timestamp", action="store_true", help="Hide timestamps")
    parser.add_argument("--list-requests", action="store_true", help="List all request IDs in the logs")
    parser.add_argument("--list-traces", action="store_true", help="List all traces in the logs")
    parser.add_argument("--webhook-logs", action="store_true", help="Show webhook logs (from logs/webhook_*.json)")
    
    args = parser.parse_args()
    
    # Determine log file path
    log_file_path = args.log_file
    if not log_file_path:
        log_file_path = os.path.join(LOG_DIR, "application.log")
        if not os.path.exists(log_file_path):
            # Try to find any log file
            log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log")]
            if log_files:
                log_file_path = os.path.join(LOG_DIR, log_files[0])
            else:
                print(f"No log files found in {LOG_DIR}", file=sys.stderr)
                sys.exit(1)
    
    # Check if log file exists
    if not os.path.exists(log_file_path):
        print(f"Log file not found: {log_file_path}", file=sys.stderr)
        sys.exit(1)
    
    # Read log entries
    log_entries = read_log_file(log_file_path)
    
    # Add webhook logs if requested
    if args.webhook_logs:
        webhook_log_dir = os.path.join(LOG_DIR)
        for filename in os.listdir(webhook_log_dir):
            if filename.startswith("webhook_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(webhook_log_dir, filename), 'r') as f:
                        webhook_data = json.load(f)
                        
                        # Create a log entry from the webhook data
                        log_entries.append({
                            "timestamp": webhook_data.get("timestamp", ""),
                            "logger": "webhook.handler",
                            "level": "INFO",
                            "message": "Webhook received",
                            "workspace_id": webhook_data.get("workspace_id", ""),
                            "client_ip": webhook_data.get("client_ip", ""),
                            "path": webhook_data.get("path", ""),
                            "data": webhook_data.get("data", {})
                        })
                except Exception as e:
                    print(f"Error reading webhook log {filename}: {str(e)}", file=sys.stderr)
    
    # Sort entries by timestamp
    log_entries.sort(key=lambda e: e.get("timestamp", ""))
    
    # List request IDs if requested
    if args.list_requests:
        request_ids = find_request_ids(log_entries)
        if request_ids:
            print(f"Found {len(request_ids)} request IDs:")
            for request_id in request_ids:
                # Count entries for this request
                count = len([e for e in log_entries if e.get("request_id") == request_id])
                print(f"  {request_id} ({count} entries)")
        else:
            print("No request IDs found in logs")
        sys.exit(0)
    
    # List traces if requested
    if args.list_traces:
        traces = find_traces(log_entries)
        if traces:
            print(f"Found {len(traces)} traces:")
            for trace in sorted(traces, key=lambda t: t.get("first_seen", "")):
                print(f"  {trace['trace_id']} - Workflow: {trace['workflow']}, " +
                      f"Workspace: {trace['workspace_id']}, Story: {trace['story_id']}, " +
                      f"Entries: {trace['entries']}")
        else:
            print("No traces found in logs")
        sys.exit(0)
    
    # Filter entries
    filtered_entries = filter_log_entries(
        log_entries,
        request_id=args.request_id,
        workspace_id=args.workspace_id,
        story_id=args.story_id,
        trace_id=args.trace_id,
        min_level=args.level
    )
    
    # Print filtered entries
    if filtered_entries:
        print(f"Showing {len(filtered_entries)} log entries:")
        print_logs(filtered_entries, show_timestamp=not args.no_timestamp)
    else:
        print("No matching log entries found")

if __name__ == "__main__":
    main()