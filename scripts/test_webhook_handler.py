#!/usr/bin/env python3
"""
Test script for webhook handler with the current format of webhook data.
"""

import os
import sys
import json
import asyncio
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the webhook handler
from api.webhook.handler import handle_webhook
from utils.logging.logger import configure_global_logging

# Set up logging
configure_global_logging(
    console_level="DEBUG",
    file_level="DEBUG",
    log_filename="test_webhook.log"
)

# Sample webhook data based on real Shortcut webhook
SAMPLE_WEBHOOK = {
    "id": str(uuid.uuid4()),
    "changed_at": "2025-03-14T00:39:41.971Z",
    "version": "v1",
    "primary_id": 305,
    "member_id": str(uuid.uuid4()),
    "actions": [
        {
            "id": 305,
            "entity_type": "story",
            "action": "update",
            "name": "US:101 Create a configurable metronome with audio and visual cues",
            "story_type": "feature",
            "app_url": "https://app.shortcut.com/shortcutagent/story/305",
            "changes": {
                "label_ids": {
                    "adds": [
                        {
                            "id": 293,
                            "name": "enhance"
                        }
                    ]
                }
            }
        }
    ],
    "references": [
        {
            "id": 293,
            "entity_type": "label",
            "name": "enhance",
            "app_url": "https://app.shortcut.com/shortcutagent/label/293"
        }
    ]
}

async def test_webhook_handler():
    """Test the webhook handler with a sample webhook."""
    # Set environment variable for testing
    os.environ["SHORTCUT_API_KEY_WORKSPACE1"] = "test-api-key"
    
    # Process the webhook
    workspace_id = "workspace1"
    result = await handle_webhook(
        workspace_id=workspace_id,
        webhook_data=SAMPLE_WEBHOOK,
        request_path="/api/webhook/workspace1",
        client_ip="127.0.0.1"
    )
    
    # Print the result
    print("Webhook processing result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    print("Testing webhook handler...")
    asyncio.run(test_webhook_handler())