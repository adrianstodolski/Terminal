import json
import urllib.request

BASE = "http://127.0.0.1:8420"

def get(path):
    req = urllib.request.Request(
        BASE + path,
        headers={"User-Agent": "market-funnel/0.1"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

for symbol in ["BTC", "GRASS", "ENA", "PYTH", "ANIME", "COMP"]:
    print(f"\n{'=' * 24} ORDER FLOW: {symbol} {'=' * 24}")
    try:
        data = get(f"/v1/orderflow/{symbol}")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:6500])
    except Exception as e:
        print(f"BŁĄD: {type(e).__name__}: {e}")

print(f"\n{'=' * 24} FUNDING RATES {'=' * 24}")
try:
    data = get("/v1/funding-rates")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2, ensure_ascii=False)[:8000])
    else:
        print(json.dumps(data[:15], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"BŁĄD: {type(e).__name__}: {e}")
