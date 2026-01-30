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

python3 -c "
import http.server
import socketserver

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

PORT = $PORT
with socketserver.TCPServer(('0.0.0.0', PORT), NoCacheHandler) as httpd:
    httpd.serve_forever()
"
