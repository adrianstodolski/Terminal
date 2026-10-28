# Full EdgeDepth Terminal — original C++/WebAssembly interface

The **primary** terminal is the original EdgeDepth C++/ImGui/WebAssembly application with heatmap, DOM, footprint, TPO/market profile, trade bubbles, volume profile and replay. `research-ui/` is only a separate read-only analytics companion; it does not replace these features.

## Mac launch — reuse your existing working Gateway

Prerequisites: Docker Desktop running, and EdgeDepth Gateway already reachable on Mac at `ws://127.0.0.1:9001/ws`.

```bash
cd ~/Dev/Terminal
git pull --ff-only origin main
bash scripts/start-full-terminal.sh
```

Open `http://127.0.0.1:8082` in **Chrome or Firefox** (Safari is not verified upstream).

Enable trade bubbles from **Layers**. Use **Replay → Replay Library** for recorded market scenarios. The original application also contains DOM, Footprint, TPO/Market Profile, VPVR and heatmap tools.

The script uses the published **upstream** Docker image `ghcr.io/edgedepthhq/edgedepth-terminal:latest`, not a build of the modified `vendor/edgedepth-terminal` tree. This gets the complete original interface running without Emscripten installation but is **not** proof that our Python analytics are embedded in its ImGui workspace. Upstream `latest` is a moving tag; it is recommended to pin an image digest once tested.

```bash
docker logs --tail 100 edgedepth-full-terminal
docker stop edgedepth-full-terminal
```

If 8082 is in use, launch with `EDGEDEPTH_TERMINAL_PORT=8083 bash scripts/start-full-terminal.sh`.

If live feed is empty, check the Gateway on port 9001. The original app is Binance-facing by default; our Hyperliquid order-book diagnostics remain in the read-only local API and are **not** integrated into the C++ terminal yet. Browser-side WebSocket connects to localhost:9001 from the Mac, not from the Docker network.

## Where the actual integration stands

- **Working source diagnostics:** `integration/api.py` on 8765, HyperData + Hyperliquid + EdgeDepth Gateway and CCXT.
- **Native EdgeDepth interface:** available through the upstream container on 8082.
- **Still missing:** real C++ ImGui panel(s) for analytics and orderflow; a validated C++/WASM rebuild from our repository; multi-source model fusion in native UI; comprehensive live/recorded acceptance testing.
- **Do not represent separate browser windows as a unified terminal.**

### Engineering direction

Extend original `vendor/edgedepth-terminal/src/ui/` and `src/rendering/` to display well-defined, timestamped read-only analytics snapshots. Prefer a same-origin proxy that preserves WebAssembly COOP/COEP requirements, and avoid insecure cross-origin WebAssembly fetch workarounds. Keep source freshness and execution venue distinctions in the UI. Build with Emscripten 4.0.15 and protoc 21.12, per `vendor/edgedepth-terminal/docs/SETUP.md`.
