# ATSE TITAN — Design System and UX Architecture v2
Status: approved design direction, implementation follows; 2026-10-29.

## Product goal
One dense, beautiful, quiet native C++/ImGui/ImPlot trading terminal, developed **on EdgeDepth source**; preserve heatmap, footprint, DOM, TPO, trade bubbles, replay. Do not build a second HTML application.

## Reference products and extractable patterns
- Bookmap (https://bookmap.com/en/features): the chart is a liquidity canvas, not a collection of competing cards. Depth and executions must use independent optical scales.
- Exocharts (https://exocharts.com/): fixed numeric columns, efficient footprint/volume-at-price encoding.
- TradingView (https://www.tradingview.com/): pan/zoom, linked crosshair, right price scale and layering ergonomics.
- Linear (https://linear.app/): restraint, command navigation, crisp information hierarchy, consistent controls.
These are inspiration sources. Never copy proprietary brand marks, graphics or the visual layout pixel-for-pixel.

## Design tokens (single source of truth)
| Token | Hex | Use |
| --- | --- | --- |
| canvas | #080D16 | central chart/background |
| surface | #101827 | docked panels |
| elevated | #192437 | overlays/menus |
| line | #27364A | hairlines |
| text | #EAF1FA | primary text |
| muted | #8A9AB0 | secondary text |
| buy | #36D6A4 | aggressive buy/execution positive |
| sell | #F16F84 | aggressive sell/execution negative |
| research | #7B91FF | information/ATSE annotation |
| caution | #F2BC73 | warning/stale/unconfirmed |
Absolute no: gradients in chrome, neon borders on all cards, emoji icon clutter, blinking digits, equal visual weight for every datum.
Color may not be the only carrier of state; use labels/shapes.

## Typography
- Candidate: IBM Plex Sans with IBM Plex Mono (SIL OFL-1.1); https://github.com/IBM/plex
- **Do not** replace font assets blindly. Compare against shipped Inter + Roboto Mono and check font glyph coverage, size, loading and OFL notices.
- UI base 13–14 px, secondary 11–12 px, labels 10px, primary price 20–24px. Fixed-width right-aligned price/size/volume columns; use tabular glyphs.

## Spatial system
- 4 px spacing unit; panel padding 12–16 px; compact table rows 21–25 px; 1 px dividers; corners 6–10 px.
- Desktop 1440px+: top command bar 48 px; left collapsible market rail 200–230px; center chart >=660px; right docked intelligence inspector 310–380px; lower analytics tray 160–250px and collapsible.
- Wide-screen center chart grows, not sidebars. Below 1200px: collapse left rail. Below 900px: right inspector becomes selectable lower tab.
- Workspace presets: Heatmap, Footprint, Scalp, Swing, Research. User-saved overrides win.
- **The ATSE inspector is docked, not a movable default modal obscuring the plot.** Tab content: Market / Orderflow / Signals / Risk / Sources; render only selected tab.

## Chart and heatmap integration
- Overlay annotation only when market, venue, timeframe, historical/live mode and price units are compatible. Explicit data source + timestamp in hover.
- Price chart: prior highs/lows, EMA, VWAP, validated scenario levels. Keep RSI/CCI/CVD in lower studies, not pasted across the price canvas.
- Footprint: fixed bid/ask columns; significance thresholds; cumulative delta; optional imbalances and stacked imbalances.
- Heatmap: independently calibrated liquidity intensity; bubbles sized to aggressive volume; markers clustered, collision-avoiding; never confuse executed volume with resting liquidity.
- Time/price coordinate transformations are owned by existing ImPlot chart. No separate HTML SVG overlay over WebGL canvas.
- Every visual event must include freshness, sample window, origin and replay compatibility.

## Motion and interaction
- No motion that obstructs price reading. Optional 120–180 ms tint for changed cells, not numeric jumping; 160–220 ms easing for opening panels.
- Reduced Motion option suppresses nonessential animations. Do not animate entire ImGui windows on each tick.
- Keyboard: Cmd/Ctrl+K market switch/command palette, / search, F8 inspector toggle, Esc closes active overlay. Guard existing EdgeDepth bindings.
- Contextual rather than permanent control bars: zoom/pan/measurement tools appear on hover or focused chart.

## Technology decision
**Keep** Dear ImGui (docking/tables), ImPlot, C++20, SDL3, WebGL2/ImGui draw lists and existing CPU/GPU heatmap renderer. These are already integrated with EdgeDepth and preserve native fidelity.
Use existing ImGui table and draw-list primitives for data-dense panels; do not add an unrelated React shell or large motion framework.
Consider official `imnodes` only if a future signal-builder graph is required; consider `nlohmann/json` (already present) for state serialization. Avoid adding them speculatively.
Use GPU-friendly overlay primitives and cached text layout. Benchmark the actual platform before adding animation libraries.

## Delivery gates
1. Theme/token acceptance: screenshots at 1440x900, 1920x1080 and 2560x1440, with saved and clean preferences.
2. Inspector docking: chart always readable; no default floating panel; persist layout.
3. Tables: aligned prices, freeze headers where useful, low-noise heat scale and depth columns.
4. Time/price links: crosshair and symbol changes propagate without displaying one market's ATSE data on another.
5. Visual confidence: state labels for stale/missing/inconclusive inputs and disconnected gateway.
6. Performance: target 60fps with active heatmap on Apple Silicon Chrome; profile frame times, input latency, CPU/GPU usage, don't claim achieved until measured.
7. Accessibility: high contrast, keyboard navigation, reduced motion and text scaling.

## Iteration sequence
P0 (next coding milestone): move ATSE from floating window into docked tabbed inspector while preserving chart resize/docking; wire source status + risk scenario tabs with honest no-data states.
P1: redesign top command bar/market selector and chart tools; integrate research levels with legend and layer manager.
P2: footprint/DOM numeric column language, intelligent event badges and lower CVD/delta panel.
P3: heatmap annotation and richer risk/scenario tooling; replay-aware diagnostics.

## Source implementation files
`vendor/edgedepth-terminal/src/rendering/theme.{h,cpp}`, `src/rendering/layout.cpp`, `src/rendering/app_shell.cpp`, `src/ui/chart_widget.cpp`, `src/ui/atse_research_panel.h`, `src/ui/atse_chart_overlay.h`.
Do not alter backend sources solely for cosmetic effects.
