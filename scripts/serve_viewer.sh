#!/usr/bin/env bash
set -e

PORT="${PORT:-5000}"

echo "Starting static server on port $PORT..."
echo ""
echo "Open the viewer at:"
echo "  http://localhost:$PORT/ui/viewer/index.html"
echo ""
echo "In Replit: Open the Webview pane and navigate to /ui/viewer/index.html"
echo ""
echo "Press Ctrl+C to stop."
echo ""

cd "$(dirname "$0")/.."
exec python3 -m http.server "$PORT" --bind 0.0.0.0
