import json
import time
import urllib.request

API = "https://api.hyperliquid.xyz/info"

CANDIDATES = {
    "LONG": ["ONDO", "INJ", "UNI", "DOGE", "TIA", "ENA"],
    "SHORT": ["LTC", "NEAR", "CRV", "ARB", "BCH", "COMP"],
}

def post(payload):
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

def candles(coin, interval, count=100):
    end = int(time.time() * 1000)
    minutes = {"5m": 5, "15m": 15}[interval]
    start = end - count * minutes * 60_000
    return post({
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start,
            "endTime": end,
        },
    })

def f(x):
    return float(x)

def analyze(data, side):
    if not isinstance(data, list) or len(data) < 30:
        raise ValueError(f"za mało świec ({len(data) if isinstance(data, list) else 0})")

    data = sorted(data, key=lambda x: int(x["t"]))
    highs = [f(x["h"]) for x in data]
    lows = [f(x["l"]) for x in data]
    closes = [f(x["c"]) for x in data]
    last = closes[-1]

    # ATR(14), true range
    trs = []
    for i in range(1, len(data)):
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1]),
        ))
    atr = sum(trs[-14:]) / min(14, len(trs))

    # Exclude the currently forming/latest candle from breakout levels.
    prior_high = max(highs[-21:-1])
    prior_low = min(lows[-21:-1])
    swing_low = min(lows[-11:-1])
    swing_high = max(highs[-11:-1])

    if side == "LONG":
        trigger = prior_high
        stop = trigger - 1.5 * atr
        risk = trigger - stop
        target1 = trigger + risk * 1.5
        target2 = trigger + risk * 2
        structure = "WYBICIE POTWIERDZONE" if last > trigger else "CZEKAJ NA WYBICIE"
        invalidation = swing_low
    else:
        trigger = prior_low
        stop = trigger + 1.5 * atr
        risk = stop - trigger
        target1 = trigger - risk * 1.5
        target2 = trigger - risk * 2
        structure = "WYBICIE POTWIERDZONE" if last < trigger else "CZEKAJ NA WYBICIE"
        invalidation = swing_high

    return {
        "last": last, "atr": atr, "atr_pct": atr / last * 100,
        "trigger": trigger, "stop": stop,
        "target1": target1, "target2": target2,
        "prior_high": prior_high, "prior_low": prior_low,
        "swing_invalidation": invalidation,
        "structure": structure,
        "bars": len(data),
    }

def main():
    print("POZIOMY Z CANDLES HYPERLIQUID")
    print("Poziomy orientacyjne; nie są automatycznym sygnałem transakcyjnym.")

    for side, symbols in CANDIDATES.items():
        print(f"\n{'=' * 20} {side} {'=' * 20}")
        for symbol in symbols:
            try:
                c5 = candles(symbol, "5m", 100)
                c15 = candles(symbol, "15m", 80)
                a5 = analyze(c5, side)
                a15 = analyze(c15, side)

                print(f"\n{symbol} | {a5['structure']}")
                print(f"  Cena zamknięcia 5m: {a5['last']:.8g}")
                print(f"  ATR 5m: {a5['atr']:.8g} ({a5['atr_pct']:.2f}%)")
                print(f"  Trigger: {a5['trigger']:.8g}")
                print(f"  Stop modelowy: {a5['stop']:.8g}")
                print(f"  Cel 1 (1.5R): {a5['target1']:.8g}")
                print(f"  Cel 2 (2R):   {a5['target2']:.8g}")
                print(f"  Unieważnienie strukturalne: {a5['swing_invalidation']:.8g}")
                print(f"  Zakres 20 świec: {a5['prior_low']:.8g} – {a5['prior_high']:.8g}")
                print(f"  Potwierdzenie 15m: close={c15[-1]['c']} | "
                      f"zakres 20 świec={a15['prior_low']:.8g}–{a15['prior_high']:.8g}")

                if side == "LONG" and a5["last"] < a5["trigger"]:
                    print("  Decyzja: brak potwierdzenia wybicia — nie gonić ceny.")
                elif side == "SHORT" and a5["last"] > a5["trigger"]:
                    print("  Decyzja: brak potwierdzenia wybicia — nie otwierać shorta tylko na podstawie rankingu.")
                else:
                    print("  Decyzja: sprawdź zgodność 15m i order flow przed rozważeniem wejścia.")

            except Exception as e:
                print(f"\n{symbol} | BRAK WIARYGODNYCH DANYCH: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
