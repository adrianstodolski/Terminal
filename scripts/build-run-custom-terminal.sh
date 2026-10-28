#!/usr/bin/env bash
# Compile the CUSTOM original EdgeDepth C++/WASM from this repository.
set -euo pipefail
cd "$(dirname "$0")/.."
SOURCE="$(pwd)/vendor/edgedepth-terminal"
NAME="atse-edgedepth-custom"
PORT="${ATSE_TERMINAL_PORT:-8082}"
GATEWAY_PORT="${EDGEDEPTH_GATEWAY_PORT:-9001}"
IMAGE="${ATSE_TERMINAL_IMAGE:-atse-edgedepth:local}"
if ! docker info >/dev/null 2>&1; then echo "Start Docker Desktop first." >&2; exit 1; fi
if ! test -f "$SOURCE/src/ui/atse_research_panel.h"; then echo "Native panel missing; git pull." >&2; exit 1; fi
echo "Building modified EdgeDepth source (not pulling upstream terminal image)..."
docker build --platform linux/amd64 -t "$IMAGE" "$SOURCE"
if docker ps -a --format '{{.Names}}' | grep -Fxq "$NAME"; then docker rm -f "$NAME" >/dev/null; fi
if docker ps -a --format '{{.Names}}' | grep -Fxq "edgedepth-full-terminal"; then
  echo "Stopping old upstream-only terminal to free the port..."
  docker rm -f edgedepth-full-terminal >/dev/null
fi
echo "Launching custom EdgeDepth native app on $PORT"
docker run -d --name "$NAME" -p "127.0.0.1:$PORT:8080" -e "EDGEDEPTH_WS_URL=ws://127.0.0.1:$GATEWAY_PORT/ws" "$IMAGE" >/dev/null
echo "Open http://127.0.0.1:$PORT (Chrome/Firefox)"
echo "Run local API separately: python3 integration/api.py --port 8765 --gateway"
echo "Look for native ATSE | Market Intelligence panel"
echo "Logs: docker logs --tail 100 $NAME"
