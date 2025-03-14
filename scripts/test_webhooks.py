#!/usr/bin/env python3
"""
Test script to verify webhook reception from Shortcut.
This script simulates the Vercel serverless function and logs incoming webhooks.
"""

import os
import sys
import json
import logging
import http.server
import socketserver
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Try to load .env file if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()  # take environment variables from .env
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, attempting to install...")
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        print("Successfully installed python-dotenv")
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables from .env file")
    except Exception as e:
        print(f"Failed to install python-dotenv: {str(e)}")
        print("Continuing without loading .env file")

# Print OpenAI environment variable status (without revealing values)
openai_key = os.environ.get("OPENAI_API_KEY")
shortcut_key = os.environ.get("SHORTCUT_API_KEY")
shortcut_workspace_key = os.environ.get("SHORTCUT_API_KEY_WORKSPACE1")

print(f"Environment check:")
print(f"  OPENAI_API_KEY: {'SET' if openai_key else 'NOT SET'}")
print(f"  SHORTCUT_API_KEY: {'SET' if shortcut_key else 'NOT SET'}")
print(f"  SHORTCUT_API_KEY_WORKSPACE1: {'SET' if shortcut_workspace_key else 'NOT SET'}")
print(f"  USE_MOCK_AGENTS: {os.environ.get('USE_MOCK_AGENTS', 'false')}")
print(f"  USE_REAL_SHORTCUT: {os.environ.get('USE_REAL_SHORTCUT', 'false')}")

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize logging system (import after adding parent to path)
try:
    from utils.logging.logger import get_logger, configure_global_logging
    from utils.logging.webhook import log_webhook_receipt, extract_story_id
    
    # Configure global logging
    configure_global_logging(
        log_dir="logs",
        log_filename="webhook_test.log",
        console_level="INFO",
        file_level="DEBUG"
    )
    
    # Get logger
    logger = get_logger("webhook_test")
    using_new_logging = True
except ImportError:
    # Fall back to basic logging if imports fail
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("webhook_test.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("webhook_test")
    using_new_logging = False

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def _set_response(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    def do_GET(self):
        """Handle GET requests - just return a simple status page"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Log the GET request
        logger.info(f"Received GET request from {self.client_address[0]} to {self.path}")
        
        # Check for ping endpoint
        if self.path == '/ping':
            self.wfile.write(b"Server is up and running!")
            return
        
        # Simple status page
        self.wfile.write(b"""
        <html>
            <head><title>Webhook Tester</title></head>
            <body>
                <h1>Webhook Tester</h1>
                <p>Webhook server is running. Send POST requests to test webhook handling.</p>
                <p>To test if the server is accessible remotely, visit <a href="/ping">/ping</a></p>
            </body>
        </html>
        """)
    
    def do_POST(self):
        """Handle POST requests - process webhook data"""
        # Log all POST requests immediately
        client_ip = self.client_address[0]
        logger.info(f"Received POST request from {client_ip} to {self.path}")
        
        # Get request path and extract workspace ID
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')
        
        # Extract workspace ID from path
        workspace_id = None
        if len(path_parts) > 1 and path_parts[0] == "api" and path_parts[1] == "webhook":
            if len(path_parts) > 2:
                workspace_id = path_parts[2]
        
        # Log headers
        logger.info(f"Request headers: {dict(self.headers)}")
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Generate timestamp for log file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/webhook_{timestamp}.json"
        
        # Try to parse JSON
        try:
            webhook_data = json.loads(post_data.decode('utf-8')) if post_data else {}
            
            # Use new logging system if available
            if using_new_logging:
                # Log webhook with structured logging
                request_id = log_webhook_receipt(
                    workspace_id=workspace_id or "unknown",
                    path=self.path,
                    client_ip=client_ip,
                    headers=dict(self.headers),
                    data=webhook_data
                )
                
                # Extract story ID for logging
                story_id = extract_story_id(webhook_data)
                
                # Traditional logging for compatibility
                logger.info(f"Received webhook for workspace: {workspace_id}")
                logger.info(f"Webhook data: {json.dumps(webhook_data)[:500]}...")  # Log first 500 chars
                logger.info(f"Saving webhook data to: {log_file}")
            else:
                # Traditional logging
                logger.info(f"Received webhook for workspace: {workspace_id}")
                logger.info(f"Webhook data: {json.dumps(webhook_data)[:500]}...")  # Log first 500 chars
                logger.info(f"Saving webhook data to: {log_file}")
            
            # Save webhook data to file
            with open(log_file, 'w') as f:
                json.dump({
                    "timestamp": timestamp,
                    "workspace_id": workspace_id,
                    "client_ip": client_ip,
                    "path": self.path,
                    "headers": dict(self.headers),
                    "data": webhook_data
                }, f, indent=2)
            
            # Process the webhook using the actual handler
            try:
                from api.webhook.handler import handle_webhook
                
                # Process webhook asynchronously
                import asyncio
                logger.info(f"Processing webhook with handler for workspace: {workspace_id}")
                
                # Create asyncio event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Process webhook with handler
                handler_result = loop.run_until_complete(
                    handle_webhook(
                        workspace_id=workspace_id or "unknown",
                        webhook_data=webhook_data,
                        request_path=self.path,
                        client_ip=client_ip
                    )
                )
                
                # Log handler result
                logger.info(f"Webhook handler result: {json.dumps(handler_result)}")
                
                # Close the event loop
                loop.close()
                
                # Return success response with handler result
                self._set_response()
                self.wfile.write(json.dumps({
                    "status": "processed",
                    "message": "Webhook processed successfully",
                    "log_file": log_file,
                    "handler_result": handler_result
                }).encode('utf-8'))
            except Exception as e:
                # Log error
                logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
                
                # Return success response for webhook logging only
                self._set_response()
                self.wfile.write(json.dumps({
                    "status": "received",
                    "message": "Webhook logged successfully but processing failed",
                    "log_file": log_file,
                    "error": str(e)
                }).encode('utf-8'))
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            self._set_response(400)
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Invalid JSON in webhook payload"
            }).encode('utf-8'))

def run_server(port=3000):
    """Run the webhook test server"""
    handler = WebhookHandler
    
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    # Bind to all interfaces (0.0.0.0) to make it accessible from outside
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        logger.info(f"Starting webhook test server on port {port}")
        logger.info(f"Local webhook URL: http://localhost:{port}/api/webhook/[workspace]")
        logger.info(f"Ping test URL: http://localhost:{port}/ping")
        logger.info(f"Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            httpd.server_close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test webhook reception from Shortcut')
    parser.add_argument('--port', type=int, default=3000, help='Port to listen on (default: 3000)')
    
    args = parser.parse_args()
    run_server(args.port)