#!/bin/bash
# Double-click to launch the image-pipeline maps dashboard (edit + gates + drill-down).
# Starts the local server and opens the browser. Close this Terminal window to stop.
cd "$(dirname "$0")/.." || exit 1
echo "Starting image-pipeline maps dashboard on http://localhost:8780 …"
(sleep 1; open "http://localhost:8780/#map=family-a-panel") &
exec node maps/serve.js 8780
