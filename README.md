# EdgeDepth Terminal — Integration workspace

> **Source import confirmed on 2026-10-28:** upstream C++/WebAssembly terminal and Go gateway are now in `vendor/`. Full Theta feature integration, WebAssembly build and end-to-end runtime tests remain **unverified / incomplete**. See [audit](AUDIT-2026-10-28.md).

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

## Imported source vs outstanding integration

- Original C++/Emscripten terminal and Go gateway have been imported under `vendor/`; this does **not** prove that modified Theta ImGui/browser panels were imported.
- EdgeDepth Gateway and its Protobuf code are present, but the separate Python gateway WebSocket bridge is not confirmed
- Full local HyperData and CCXT integrations, venue-aware depth fusion and signal history
- Remaining tests from the Theta ZIP and full WebAssembly build
- Validation on local live feeds and historical orderflow replay

The project was previously built into a local **EdgeDepth Integrated Theta** archive, but **its complete modifications are not on GitHub**. The original vendor code is now imported. No passing CI run or complete runtime validation has been verified; see [audit](AUDIT-2026-10-28.md).

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
