# EdgeDepth integrated source — runbook

## What has been implemented
- Original C++/WebAssembly terminal in `vendor/edgedepth-terminal`.
- Original Go 1.24 gateway in `vendor/edgedepth-gateway`.
- Read-only Python API in `integration/api.py`: Hyperliquid completed candle research, CCI/RSI/EMA/ATR, advanced indicator proxies, breakout analysis, strategy comparison, risk sizing.
- Read-only HyperData health/market and optional CCXT Binance USD-M price diagnostics: `GET /api/overview?symbol=BTC`.
- Execution-venue depth from Hyperliquid, and optionally separate Binance Gateway depth: `GET /api/depth?symbol=BTC`.
- Venue-aware depth context: `GET /api/fusion?symbol=BTC`.
- Browser Research Lab with source health and depth panels: `research-ui/index.html`.
- Python smoke and depth tests; Go gateway CI workflow.

## Local commands (Mac)

```bash
cd ~/Dev/Terminal
git pull --ff-only origin main
python3 -m venv .venv
source .venv/bin/activate
pip install 'ccxt>=4,<5' 'websockets>=14,<17'
python3 -m unittest discover -s integration/tests -p 'test_*.py' -v
python3 integration/api.py --port 8765 --gateway
```

Second terminal:

```bash
cd ~/Dev/Terminal
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://127.0.0.1:8080/research-ui/`.

Optional EdgeDepth Gateway: follow `vendor/edgedepth-gateway/README.md`, start local WS at `ws://127.0.0.1:9001/ws`. Without it, the API reports Gateway disabled/unavailable. HyperData is independently expected at `http://127.0.0.1:8420`; without it, the API reports unavailable.

To verify:

```bash
curl -sS 'http://127.0.0.1:8765/api/health'
curl -sS 'http://127.0.0.1:8765/api/depth?symbol=BTC'
curl -sS 'http://127.0.0.1:8765/api/overview?symbol=BTC'
```

## Quality / safety

**Do not confuse feature presence with end-to-end validation.** The research UI is not embedded in the original Emscripten terminal. The gateway adapter uses a subset Protobuf decoder and should be checked against current protocol fixtures. CCXT market data refers to Binance USD-M, not tradeable Hyperliquid liquidity. A missing feed must never be treated as confirmation. Historical candle analyses lack realistic live fills, complete orderflow replay, and out-of-sample performance certification. No order execution is provided.

CI Go/Python workflows have been configured; check the Actions page for run outcomes. This README documents code, not evidence of successful production builds.

## Next acceptance criteria

1. Build Emscripten terminal, run browser tests and connect original UI to read-only API panels.
2. Validate gateway book synchronization and resnapshot on gaps using recorded live feeds.
3. Run live HyperData and Hyperliquid diagnostics for multiple assets and venue mapping.
4. Add persistence of timestamped, provenance-carrying signals and historical orderflow replay.
5. Perform out-of-sample and paper-trading validation with explicit fees/slippage before relying on any signals.
