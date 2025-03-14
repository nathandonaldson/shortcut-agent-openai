#!/bin/bash
# Script to start the webhook server, ngrok tunnel, and log follower

# Default port
PORT=3000
# Debug mode - starts log follower
DEBUG=true
# Use mock agents
USE_MOCK_AGENTS=false

# Parse command line arguments
while getopts "p:d:m:" opt; do
  case $opt in
    p) PORT=$OPTARG ;;
    d) DEBUG=$OPTARG ;;
    m) USE_MOCK_AGENTS=$OPTARG ;;
    *) echo "Usage: $0 [-p port] [-d true|false] [-m true|false]" >&2
       exit 1 ;;
  esac
done

# Create logs directory if it doesn't exist
mkdir -p logs

# Set environment variables for testing
export PYTHONPATH=$PWD

# Use real agents by default, can override with command line argument
if [ "${USE_MOCK_AGENTS:-false}" = "true" ]; then
  export USE_MOCK_AGENTS=true
  echo "Setting USE_MOCK_AGENTS=true to use refactored agent mocks"
else
  export USE_MOCK_AGENTS=false
  export USE_REAL_SHORTCUT=true
  echo "Setting USE_MOCK_AGENTS=false and USE_REAL_SHORTCUT=true to use real APIs"
fi

# Start the webhook server in the background
echo "Starting webhook server on port $PORT..."
python3 "$(dirname "$0")/test_webhooks.py" --port $PORT &
SERVER_PID=$!

# Track PIDs for cleanup
PIDS=($SERVER_PID)

# Trap Ctrl+C to stop all processes
trap "echo 'Stopping all processes...'; for pid in \${PIDS[@]}; do kill \$pid 2>/dev/null; done; killall ngrok 2>/dev/null; exit" INT

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
PIDS+=($NGROK_PID)

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

# Start log follower if in debug mode
if [ "$DEBUG" = "true" ]; then
  echo "Starting log follower in a new terminal..."
  
  # Determine the terminal application based on OS
  if [ "$(uname)" = "Darwin" ]; then
    # macOS - use Terminal.app or iTerm if available
    if osascript -e 'tell application "iTerm" to version' &>/dev/null; then
      # Open in iTerm
      osascript -e 'tell application "iTerm"' \
                -e 'set newWindow to (create window with default profile)' \
                -e 'tell current session of newWindow' \
                -e "write text \"cd $(pwd) && python3 scripts/follow_logs.py --webhook\"" \
                -e 'end tell' \
                -e 'end tell' &
    else
      # Open in Terminal.app
      osascript -e 'tell application "Terminal"' \
                -e "do script \"cd $(pwd) && python3 scripts/follow_logs.py --webhook\"" \
                -e 'end tell' &
    fi
  else
    # Linux/other - try to use gnome-terminal, xterm, or just run in background
    if command -v gnome-terminal &>/dev/null; then
      gnome-terminal -- bash -c "cd $(pwd) && python3 scripts/follow_logs.py --webhook; exec bash" &
    elif command -v xterm &>/dev/null; then
      xterm -e "cd $(pwd) && python3 scripts/follow_logs.py --webhook" &
    else
      # Fall back to running in background
      echo "Could not open a new terminal, starting log follower in background."
      python3 "$(dirname "$0")/follow_logs.py" --webhook &
      LOG_FOLLOWER_PID=$!
      PIDS+=($LOG_FOLLOWER_PID)
    fi
  fi
  
  echo "Log follower started. You can also manually run: python3 scripts/follow_logs.py --webhook"
fi

# Wait for the webhook server to exit
wait $SERVER_PID