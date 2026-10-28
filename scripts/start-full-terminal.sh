#!/usr/bin/env bash
# Start the real EdgeDepth C++/WebAssembly terminal in a Docker container.
# It uses an existing EdgeDepth Gateway on the Mac at port 9001.
# The experimental Research Lab is NOT used here.
set -euo pipefail

PORT="${EDGEDEPTH_TERMINAL_PORT:-8082}"
GATEWAY_PORT="${EDGEDEPTH_GATEWAY_PORT:-9001}"
NAME="edgedepth-full-terminal"
IMAGE="${EDGEDEPTH_TERMINAL_IMAGE:-ghcr.io/edgedepthhq/edgedepth-terminal:latest}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop is required. Install/start it before using this script." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop daemon is not running." >&2
  exit 1
fi
if ! [[ "$PORT" =~ ^[0-9]+$ && "$GATEWAY_PORT" =~ ^[0-9]+$ ]]; then
  echo "Ports must be numeric" >&2
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$NAME"; then
  echo "Recreating previous $NAME container..."
  docker rm -f "$NAME" >/dev/null
fi

echo "Pulling official upstream EdgeDepth terminal image..."
docker pull "$IMAGE"

echo "Starting actual C++/WASM EdgeDepth at http://127.0.0.1:$PORT"
echo "Browser gateway: ws://127.0.0.1:$GATEWAY_PORT/ws"
docker run --detach \
  --name "$NAME" \
  --restart unless-stopped \
  --publish "127.0.0.1:$PORT:8080" \
  --env "EDGEDEPTH_WS_URL=ws://127.0.0.1:$GATEWAY_PORT/ws" \
  "$IMAGE" >/dev/null

echo
echo "Full terminal: http://127.0.0.1:$PORT"
echo "Read-only diagnostics API (if running): http://127.0.0.1:8765/api/health"
echo "Research Lab (if running): http://127.0.0.1:8080/research-ui/"
echo "Gateway must be listening on Mac port $GATEWAY_PORT for live Binance depth."
echo "First open the terminal in Chrome/Firefox. Enable bubbles in Layers."
echo "For recorded data, use Replay > Replay Library."
echo "Check logs: docker logs --tail=100 $NAME"
echo "Stop: docker stop $NAME"
