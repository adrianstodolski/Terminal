# EdgeDepth Terminal — Integration workspace

> **Migration in progress. The original C++/WebAssembly EdgeDepth Terminal and its gateway have NOT yet been pushed to this repository.** The committed research API and dashboard are standalone research tools, not a complete deployed trading platform.

## What works in this repository

The following Python modules are committed:

- `integration/api.py`: local read-only Hyperliquid completed-candle API
- `integration/analytics.py`: risk sizing and historical breakout analysis
- `integration/indicator_lab.py`: CCI, RSI, RSI-Bollinger, EMA, MACD, ATR
- `integration/advanced_indicators.py`: documented causal trend/momentum approximations (not exact MT4/Jurik clones)
- `integration/strategy_lab.py`: simplified indicator-versus-breakout research comparisons
- `integration/tests/test_imported_theta.py`: deterministic unit smoke tests
- `research-ui/index.html`: standalone research dashboard
- `.github/workflows/python-integration.yml`: automated Python smoke test configuration

These are **adapted/reimplemented research components**, not a complete file-for-file import of the Theta archive.

## Run on macOS

Requires Python 3.13. The committed code uses Python standard library only.

Terminal 1:

```bash
git clone https://github.com/adrianstodolski/Terminal.git
cd Terminal
python3 integration/api.py --port 8765
```

Terminal 2:

```bash
cd Terminal
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://127.0.0.1:8080/research-ui/`. The API is available on `http://127.0.0.1:8765/api/health`. Historical candle requests need Internet access to `api.hyperliquid.xyz`.

Run smoke tests:

```bash
python3 -m unittest discover -s integration/tests -p 'test_imported_theta.py' -v
```

## Still missing from GitHub

- The original EdgeDepth C++/Emscripten terminal and the modified ImGui/browser shell
- EdgeDepth Gateway and its Protobuf/WebSocket reader
- Full local HyperData and CCXT integrations, venue-aware depth fusion and signal history
- Remaining tests from the Theta ZIP and full WebAssembly build
- Validation on local live feeds and historical orderflow replay

The project was previously built into a local **EdgeDepth Integrated Theta** archive. Its local 28-test suite was executed successfully, but the **entire archive is not on GitHub**. This repository cannot currently be claimed as a complete transfer or a production-ready terminal.

## Execution and research limitations

- **Read-only**: no exchange authentication and no orders
- All indicator outputs are research approximations
- Backtests do not model all live execution effects, gaps, orderflow history, funding or liquidity
- No profitability or reliability claims are made
- Keep API bound to localhost; do not commit exchange credentials

## Upstream projects and licensing

- [EdgeDepth Terminal](https://github.com/edgedepthhq/edgedepth-terminal), **AGPL-3.0**
- [EdgeDepth Gateway](https://github.com/edgedepthhq/edgedepth-gateway), **MIT**

Before redistributing modified upstream code, preserve the relevant licenses and attributions. Repository is currently public; change visibility if desired and review files before uploading.
