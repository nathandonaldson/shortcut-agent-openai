#!/usr/bin/env python
"""
Script to view recent OpenAI Agent SDK traces for debugging.
Provides a convenient way to check trace status from the command line.
"""

import os
import asyncio
import argparse
from agents import set_default_openai_key

async def view_recent_traces(count: int = 10):
    """Fetch and display recent traces for debugging."""
    # Set up API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return
        
    set_default_openai_key(api_key)
    
    # Use OpenAI API to fetch traces (placeholder)
    print(f"Fetching {count} most recent traces...")
    print(f"Visit https://platform.openai.com/traces to view all traces")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View recent traces for debugging")
    parser.add_argument("--count", type=int, default=10, help="Number of traces to view")
    args = parser.parse_args()
    
    asyncio.run(view_recent_traces(args.count))