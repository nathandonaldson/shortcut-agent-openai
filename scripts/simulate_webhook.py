#!/usr/bin/env python3
"""
Script to simulate a Shortcut webhook for testing.
Sends a sample webhook payload to the local webhook endpoint.
"""

import os
import json
import argparse
import requests
from datetime import datetime

def simulate_webhook(workspace_id, server_url, story_id=None, action="add_label", label="enhance"):
    """Simulate a Shortcut webhook by sending a request to the webhook endpoint"""
    
    if not story_id:
        # Use a fake story ID if none provided
        story_id = "12345"
    
    # Base URL for the webhook endpoint
    webhook_url = f"{server_url}/api/webhook/{workspace_id}"
    
    # Create a sample webhook payload based on the requested action
    if action == "add_label":
        webhook_data = {
            "action": "update",
            "changes": {
                "labels": {
                    "adds": [{"name": label}],
                    "removes": []
                }
            },
            "primary_id": story_id,
            "id": story_id,
            "name": "Test Story",
            "story_type": "feature",
            "description": "This is a test story for webhook testing",
            "resource": {
                "id": story_id,
                "entity_type": "story"
            },
            "timestamp": datetime.now().isoformat()
        }
    elif action == "remove_label":
        webhook_data = {
            "action": "update",
            "changes": {
                "labels": {
                    "adds": [],
                    "removes": [{"name": label}]
                }
            },
            "primary_id": story_id,
            "id": story_id,
            "name": "Test Story",
            "story_type": "feature",
            "description": "This is a test story for webhook testing",
            "resource": {
                "id": story_id,
                "entity_type": "story"
            },
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise ValueError(f"Unknown action: {action}")
    
    # Send the webhook payload
    print(f"Sending {action} webhook to {webhook_url}")
    print(f"Payload: {json.dumps(webhook_data, indent=2)}")
    
    response = requests.post(
        webhook_url,
        json=webhook_data,
        headers={"Content-Type": "application/json"}
    )
    
    # Print the response
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    return response

def get_ngrok_url():
    """Try to get the ngrok URL from the ngrok API"""
    # First check for custom domain
    custom_domain = "kangaroo-superb-cheaply.ngrok-free.app"
    if custom_domain:
        return f"https://{custom_domain}"
        
    # If no custom domain, try to get URL from ngrok API
    try:
        response = requests.get("http://localhost:4040/api/tunnels")
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get("tunnels", []):
                if tunnel.get("proto") == "https":
                    return tunnel.get("public_url")
            # Fall back to http if https not found
            for tunnel in data.get("tunnels", []):
                if tunnel.get("proto") == "http":
                    return tunnel.get("public_url")
    except:
        pass
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a Shortcut webhook")
    parser.add_argument("workspace_id", help="Workspace ID to use in the webhook URL")
    parser.add_argument("--server", default=None, help="Server URL (default: auto-detect ngrok URL or use http://localhost:3000)")
    parser.add_argument("--story-id", help="Story ID to use in the webhook payload")
    parser.add_argument("--action", choices=["add_label", "remove_label"], default="add_label", help="Webhook action (default: add_label)")
    parser.add_argument("--label", default="enhance", help="Label to add or remove (default: enhance)")
    
    args = parser.parse_args()
    
    # Auto-detect server URL if not specified
    server_url = args.server
    if not server_url:
        # Try to get ngrok URL
        ngrok_url = get_ngrok_url()
        if ngrok_url:
            print(f"Using detected ngrok URL: {ngrok_url}")
            server_url = ngrok_url
        else:
            # Fall back to localhost
            server_url = "http://localhost:3000"
            print(f"Using default server URL: {server_url}")
    
    simulate_webhook(
        args.workspace_id,
        server_url,
        args.story_id,
        args.action,
        args.label
    )