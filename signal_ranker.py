import json
import math
import urllib.request
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8420"

def get(path):
    req = urllib.request.Request(
        BASE + path, headers={"User-Agent": "market-funnel/0.2"}
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

def number(x, default=None):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default

def clamp(x, low=-1, high=1):
    return max(low, min(high, x))

def main():
    print("SIGNAL RANKER |", datetime.now(timezone.utc).isoformat())

    market = get("/v1/market")
    assets = market.get("assets", [])
    ranked = []
    unavailable = []

    # Krótkie interwały mają największą wagę. Dłuższy interwał
    # jest używany tylko przy wystarczającym pokryciu danych.
    specs = [
        ("1m", 0.15, 10, 0.80),
        ("5m", 0.35, 20, 0.80),
        ("15m", 0.35, 50, 0.80),
        ("1h", 0.15, 100, 0.35),
    ]

    for asset in assets:
        symbol = str(asset.get("symbol", "")).upper()
        if not symbol:
            continue

        try:
            flow = get(f"/v1/orderflow/{symbol}")
        except Exception:
            unavailable.append(symbol)
            continue

        tf = flow.get("timeframes", {})
        weighted_sum = 0.0
        total_weight = 0.0
        used = []

        for name, weight, min_trades, min_coverage in specs:
            d = tf.get(name, {})
            ofi = number(d.get("ofi"))
            trades = int(number(d.get("trade_count"), 0))
            coverage = number(d.get("coverage"), 0)

            if (ofi is None or trades < min_trades
                    or coverage is None or coverage < min_coverage):
                continue

            weighted_sum += weight * clamp(ofi)
            total_weight += weight
            used.append(name)

        # Wymagamy minimum dwóch interwałów; inaczej ranking
        # nie udaje, że mamy wystarczające potwierdzenie.
        if len(used) < 2 or total_weight < 0.50:
            continue

        flow_score = weighted_sum / total_weight
        change = number(asset.get("price_change_24h_pct"))
        if change is None:
            continue

        # Pole zmiany jest w tym API interpretowane jako ułamek:
        # 0.05 ~= +5%. Momentum ma tylko 25% udziału.
        momentum_score = math.tanh(change / 0.05)
        score = 75 * flow_score + 25 * momentum_score

        ranked.append({
            "symbol": symbol,
            "price": number(asset.get("price")),
            "change": change,
            "score": score,
            "flow": flow_score,
            "momentum": momentum_score,
            "used": ",".join(used),
            "aggregate": flow.get("aggregate_signal", "UNKNOWN"),
            "volume": number(asset.get("volume_24h"), 0) or 0,
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    longs = [x for x in ranked if x["score"] > 0]
    shorts = [x for x in ranked if x["score"] < 0]

    def show(title, items):
        print(f"\n{title}")
        print("-" * 91)
        print(f"{'SYMBOL':<13}{'SCORE':>9}{'FLOW':>9}"
              f"{'MOMENTUM':>11}{'24H':>12}{'INTERWAŁY':>20}")
        for x in items:
            print(
                f"{x['symbol']:<13}{x['score']:>+9.1f}"
                f"{x['flow']:>+9.3f}{x['momentum']:>+11.3f}"
                f"{x['change']*100:>+11.2f}%"
                f"{x['used']:>20}"
            )

    show("TOP LONG — kandydaci do dalszej walidacji", longs[:10])
    show("TOP SHORT — kandydaci do dalszej walidacji", list(reversed(shorts))[:10])

    print("\nKONTROLA:")
    print(f"Aktywa z rynku HyperData: {len(assets)}")
    print(f"Aktywa z wystarczającymi danymi do rankingu: {len(ranked)}")
    print(f"Brak endpointu order flow: {len(unavailable)}")
    print("Funding celowo pominięty do czasu potwierdzenia jednostek.")
    print("To ranking obserwacyjny, nie sygnał wejścia ani backtest.")
    print("Następny etap: świece OHLCV, poziomy wejścia/SL/TP i test historyczny.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"BŁĄD SKANERA: {type(e).__name__}: {e}")
