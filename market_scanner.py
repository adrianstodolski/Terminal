import json
import urllib.request
import urllib.error
import math
import ccxt
from datetime import datetime, timezone

HD = "http://127.0.0.1:8420"
HL = "https://api.hyperliquid.xyz/info"


def get_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "market-funnel/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post_json(url, payload, timeout=10):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json",
                 "User-Agent": "market-funnel/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def num(value, default=0.0):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def main():
    print("=" * 78)
    print("MARKET FUNNEL | WSTĘPNY SKANER")
    print(datetime.now(timezone.utc).strftime("UTC %Y-%m-%d %H:%M:%S"))
    print("=" * 78)

    # 1. Health check HyperData
    try:
        health = get_json(f"{HD}/v1/health")
        print("\n[DATA HEALTH]")
        print(json.dumps(health, ensure_ascii=False)[:1800])
    except Exception as e:
        print(f"\nBŁĄD HyperData health: {type(e).__name__}: {e}")

    # 2. Direct Hyperliquid mids — independent price reference
    mids = {}
    try:
        mids = post_json(HL, {"type": "allMids"})
        print(f"\n[HYPERLIQUID API] Otrzymano {len(mids)} cen mid.")
    except Exception as e:
        print(f"\nBŁĄD Hyperliquid API: {type(e).__name__}: {e}")

    # 3. HyperData market universe
    try:
        result = get_json(f"{HD}/v1/market")
        assets = result.get("assets", [])
        if not assets:
            print("Brak aktywów w /v1/market. Odpowiedź:")
            print(json.dumps(result, ensure_ascii=False)[:1500])
            return
    except Exception as e:
        print(f"BŁĄD HyperData market: {type(e).__name__}: {e}")
        return

    rows = []
    for a in assets:
        symbol = str(a.get("symbol", "")).upper()
        price = num(a.get("price"))
        change = num(a.get("price_change_24h_pct"))
        volume = num(a.get("volume_24h"))
        oi = num(a.get("open_interest"))
        funding = a.get("funding_rate")

        # HyperData's percentage-change field may be fractional.
        # Display both interpretations; verify units before trading.
        hl_price = num(mids.get(symbol))
        diff_pct = ((price / hl_price) - 1) * 100 if price and hl_price else None

        rows.append({
            "symbol": symbol, "price": price, "change": change,
            "volume": volume, "oi": oi, "funding": funding,
            "hl_price": hl_price, "diff_pct": diff_pct,
        })

    # Prefer active markets; use momentum only for preliminary sorting.
    active = [r for r in rows if r["price"] > 0 and r["volume"] > 0]
    active.sort(key=lambda r: abs(r["change"]), reverse=True)

    def pct_display(x):
        # Print raw field and fractional interpretation to expose unit ambiguity.
        return f"{x:+.4f} raw / {x*100:+.2f}% jeśli ułamek"

    def print_table(title, items):
        print(f"\n{title}")
        print("-" * 105)
        print(f"{'SYMBOL':<12}{'CENA HD':>15}{'ZMIANA 24H':>27}"
              f"{'VOLUME 24H':>18}{'OI':>14}{'RÓŻNICA HL':>14}")
        for r in items:
            diff = f"{r['diff_pct']:+.3f}%" if r["diff_pct"] is not None else "n/a"
            print(f"{r['symbol']:<12}{r['price']:>15,.6g}"
                  f"{pct_display(r['change']):>27}"
                  f"{r['volume']:>18,.5g}{r['oi']:>14,.5g}{diff:>14}")

    print_table("NAJWIĘKSZE RUCHY — WSTĘPNE KANDYDATY", active[:15])

    longs = sorted(
        [r for r in active if r["change"] > 0],
        key=lambda r: (r["change"], math.log1p(max(r["volume"], 0))),
        reverse=True
    )[:8]
    shorts = sorted(
        [r for r in active if r["change"] < 0],
        key=lambda r: (r["change"], -math.log1p(max(r["volume"], 0)))
    )[:8]

    print_table("WATCHLIST LONG — momentum dodatnie (jeszcze nie sygnały wejścia)", longs)
    print_table("WATCHLIST SHORT — momentum ujemne (jeszcze nie sygnały wejścia)", shorts)

    # 4. CCXT independent exchange connectivity check
    print("\n[CCXT / BINANCE USD-M] Kontrola niezależnego rynku")
    try:
        ex = ccxt.binanceusdm({"timeout": 8000, "enableRateLimit": True})
        ticker = ex.fetch_ticker("BTC/USDT:USDT")
        print(f"BTC/USDT:USDT last={ticker.get('last')}")
        if mids.get("BTC") and ticker.get("last"):
            delta = (float(ticker["last"]) / float(mids["BTC"]) - 1) * 100
            print(f"Binance vs Hyperliquid mid: {delta:+.4f}% "
                  "(różnica między giełdami, nie automatycznie błąd danych)")
        ex.close()
    except Exception as e:
        print(f"CCXT Binance niedostępne: {type(e).__name__}: {e}")

    print("\nUWAGI:")
    print("- Nie otwieraj pozycji na podstawie tej watchlisty.")
    print("- Jednostka zmiany 24h i funding wymagają potwierdzenia.")
    print("- Różnica cen między giełdami może wynikać z basisu i spreadu.")
    print("- Następny etap: order flow, OI/funding, jakość danych i poziomy ryzyka.")


if __name__ == "__main__":
    main()
