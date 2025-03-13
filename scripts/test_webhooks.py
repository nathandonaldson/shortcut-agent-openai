#!/usr/bin/env python3
"""
Test script to verify webhook reception from Shortcut.
This script simulates the Vercel serverless function and logs incoming webhooks.
"""

import os
import json
import logging
import http.server
import socketserver
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("webhook_test")

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
            
            # Log the request
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
            
            # Return success response
            self._set_response()
            self.wfile.write(json.dumps({
                "status": "received",
                "message": "Webhook logged successfully",
                "log_file": log_file
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
        logger.info(f"For Tailscale, use: http://nathans-macbook-air.lamb-cobra.ts.net:{port}/api/webhook/[workspace]")
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