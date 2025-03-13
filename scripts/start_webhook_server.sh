#!/bin/bash
# Script to start the webhook server and ngrok tunnel

# Default port
PORT=3000

# Parse command line arguments
while getopts "p:" opt; do
  case $opt in
    p) PORT=$OPTARG ;;
    *) echo "Usage: $0 [-p port]" >&2
       exit 1 ;;
  esac
done

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the webhook server in the background
echo "Starting webhook server on port $PORT..."
python3 "$(dirname "$0")/test_webhooks.py" --port $PORT &
SERVER_PID=$!

# Trap Ctrl+C to stop both processes
trap "echo 'Stopping webhook server and ngrok...'; kill $SERVER_PID; killall ngrok; exit" INT

# Give the server a moment to start
sleep 2

# Start ngrok (use custom domain if specified)
echo "Starting ngrok tunnel to port $PORT..."
CUSTOM_DOMAIN="kangaroo-superb-cheaply.ngrok-free.app"
if [ -n "$CUSTOM_DOMAIN" ]; then
  echo "Using custom domain: $CUSTOM_DOMAIN"
  ngrok http $PORT --domain=$CUSTOM_DOMAIN --log=stdout > logs/ngrok.log &
else
  ngrok http $PORT --log=stdout > logs/ngrok.log &
fi
NGROK_PID=$!

# Wait a moment for ngrok to initialize
sleep 3

# Get the ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | grep -o 'http[^"]*')

if [ -z "$NGROK_URL" ]; then
  echo "Failed to get ngrok URL. Check logs/ngrok.log for details."
  echo "You can also try checking the ngrok dashboard at http://localhost:4040"
else
  echo "================== WEBHOOK SERVER READY =================="
  echo "ngrok public URL: $NGROK_URL"
  echo "Webhook endpoint: $NGROK_URL/api/webhook/[workspace_id]"
  echo "Ping test endpoint: $NGROK_URL/ping"
  echo "ngrok dashboard: http://localhost:4040"
  echo "=========================================================="
  echo "Use this URL in your Shortcut webhook configuration:"
  echo "$NGROK_URL/api/webhook/[workspace_id]"
  echo "=========================================================="
  echo "Press Ctrl+C to stop the server and ngrok tunnel"

  # Write URLs to a file for reference
  {
    echo "Webhook Server URLs (generated on $(date))"
    echo "ngrok public URL: $NGROK_URL"
    echo "Webhook endpoint: $NGROK_URL/api/webhook/[workspace_id]"
    echo "Ping test endpoint: $NGROK_URL/ping"
    echo "ngrok dashboard: http://localhost:4040"
  } > logs/webhook_urls.txt
  
  echo "URLs also saved to logs/webhook_urls.txt"
fi

# Wait for the webhook server to exit
wait $SERVER_PID