# ATSE Native UI — chart-linked integration

This is the actual modified **EdgeDepth C++ / ImGui / ImPlot / WASM** application, not the legacy HTML Research Lab and not the unmodified upstream GHCR image.

## This iteration
- Added **ATSE Obsidian** as a whole-terminal appearance preset (blue-graphite surfaces, cool text, indigo accent). Applied on first launch with no saved appearance; users with saved settings select **ATSE Obsidian** in the existing Appearance controls. Other presets remain available.
- Native ATSE window reduced to a compact research card with consistent spacing/colors, KPI grid, data quality state, and source diagnostics.
- **Follow active chart** is on by default: `TAO/USDT` chart gives **TAO** research, `BTC/USDT` gives BTC; timeframe sync from visible chart to the nearest supported interval. Manual selection remains possible when following is turned off.
- Actual **ImPlot overlay** in the original EdgeDepth chart: prior 20-bar support and resistance, EMA 12 and EMA 26, optional one-ATR reference zones, research-bias context HUD.
- Overlay runs only on supported matching instruments with close prices within 2%; disallowed on historical replay or comparison charts (do not mix live API readings into old replay data).
- If API depth is unavailable or stale, the native panel displays an explicit data warning; gateway Binance book is context only.
- Press **F8** to show or hide ATSE; levels, ATR bands and HUD have separate toggles.
- Old async API results from another symbol/timeframe are discarded. The runtime makes **no orders**.
- The original footprint, DOM, realtime heatmap, TPO/market profile, bubbles and replay are retained as authored by EdgeDepth.

## Build and verify

On Mac, Docker Desktop and the gateway on port 9001 must be available. Two terminal windows:

```bash
cd ~/Dev/Terminal
git pull --ff-only origin main
python3 -m unittest discover -s integration/tests -p 'test_*.py' -v
python3 integration/api.py --port 8765 --gateway
```

In the second terminal:

```bash
cd ~/Dev/Terminal
bash scripts/build-run-custom-terminal.sh
```

Open `http://127.0.0.1:8082` in Chrome or Firefox. **This build compiles from modified `vendor/edgedepth-terminal` source.** `scripts/start-full-terminal.sh` uses the unmodified upstream image and will *not* include ATSE.

Suggested visual acceptance:
1. Change chart from TAO/USDT to BTC/USDT. Panel symbol and chart overlays must switch automatically, never show BTC data on TAO.
2. Switch chart timeframe from 5m to 15m. The panel's interval should update.
3. Open Appearance and select **ATSE Obsidian** (unless already selected). Toggle **Levels**, **ATR range**, **HUD** to verify overlays on the **real ImPlot price chart**, not separate cards.
4. Drag/collapse the smaller ATSE card, then toggle with **F8**. Confirm original DOM, heatmap and trade bubble interaction still work.
5. Switch to Replay. Live ATSE levels should not draw over historical data.
6. Stop the local Python API. Confirm data-quality failure appears instead of a fabricated trade signal.

## Current limits

The changes are committed but have not yet passed a fresh WASM compilation/browser screenshot acceptance on the user's device. Native chart overlays display **historical indicator reference levels**, not order-book heatmap liquidity and not actual trade entry/SL/TP orders. No P&L or win-rate claim is made. Different venues can have different prices, so cross-venue levels are suppressed if the price divergence exceeds 2%, and that threshold is only a safety heuristic. Real-time research bias and quality checks still require deeper replay/backtesting before use for trades.

Future native modules should extend the same ImGui/ImPlot structures: timestamped orderflow/CVD, volume-at-price absorption, liquidity changes, confirmed liquidations and risk scenarios, without duplicating the original EdgeDepth feature set.
