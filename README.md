# EdgeDepth Integrated Terminal

**Research / migration in progress. This is not yet a runnable complete trading terminal.**

This repository is gradually receiving the source of an EdgeDepth Terminal integration previously assembled as the local **EdgeDepth Integrated Theta** snapshot. The full snapshot was not transferable as one ZIP using the available GitHub connector.

## Code already committed

- `integration/analytics.py` — deterministic position sizing and historical breakout research
- `integration/indicator_lab.py` — CCI, Wilder RSI, RSI Bollinger bands, EMA, MACD, ATR
- `integration/advanced_indicators.py` — transparent, open research approximations of trend/momentum filters, prior-candle channel, KAMA and consensus
- `integration/strategy_lab.py` — breakout vs. indicator-filtered strategy comparison, including simplified cost assumptions
- `integration/tests/test_imported_theta.py` — basic deterministic smoke tests
- `.github/workflows/python-integration.yml` — Python 3.13 CI smoke tests

## Local module tests

Requires Python 3.13; these four modules use only the standard library.

```bash
git clone https://github.com/adrianstodolski/Terminal.git
cd Terminal
python3 -m compileall -q integration
python3 -m unittest discover -s integration/tests -p 'test_imported_theta.py' -v
```

## Still missing from this GitHub repository

- Original C++/WebAssembly EdgeDepth Terminal sources
- EdgeDepth Gateway sources and Protobuf integration
- HyperData, CCXT and Hyperliquid API server and market-depth fusion
- EdgeDepth terminal UI/JS integration and remaining test suite
- Full live integration tests and WebAssembly build

The separate local Theta archive contains additional work, **but the files above are the only migrated application modules currently guaranteed present in GitHub**. Do not infer feature completeness from the earlier Theta changelog.

## Trading safety

No automatic order execution. All analyses are experimental and not validated as profitable. Backtest output does not guarantee live performance. Cost and fill models are simplified and do not cover all cases.

## Repository privacy

Review repository visibility and do not commit credentials, API secrets, .env files, or exchange account data.
