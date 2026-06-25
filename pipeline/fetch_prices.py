"""Fetch daily price series from Yahoo Finance (keyless, browser-UA).

Uses adjusted close => total return (dividends reinvested) where available.
Caches one JSON per symbol in data/prices/. FX series use raw close.
"""
import os
import time
from datetime import datetime, timezone, date, timedelta
from common import http_get_json, save_json, load_json, PRICES_DIR

YH = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit"
YH_HEADERS = {"Accept": "application/json", "Origin": "https://finance.yahoo.com",
              "Referer": "https://finance.yahoo.com/"}


def _epoch(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def _cache_path(symbol):
    safe = symbol.replace("^", "_").replace("=", "_").replace("/", "_")
    return os.path.join(PRICES_DIR, f"{safe}.json")


def fetch_series(symbol, start, end, use_adjclose=True, force=False, pause=0.3):
    """Return {iso_date: price}. Incremental: fetch only the recent tail and merge
    into cache, so daily runs stay fast and fresh. One network hit per symbol/day."""
    path = _cache_path(symbol)
    cached = load_json(path) or {}
    series = {} if force else dict(cached.get("series", {}))
    today_iso = date.today().isoformat()
    if not force and series and cached.get("_fetched") == today_iso:
        return series                       # already refreshed today

    if series and cached.get("_last"):
        fstart = max(start, date.fromisoformat(cached["_last"]) - timedelta(days=5))
    else:
        fstart = start
    url = YH.format(sym=symbol, p1=_epoch(fstart), p2=_epoch(end) + 86400)
    try:
        data = http_get_json(url, headers=YH_HEADERS, timeout=60)
    except Exception as e:
        print(f"  ! {symbol}: fetch error {type(e).__name__}")
        return series
    try:
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        adj = None
        if use_adjclose:
            ac = res["indicators"].get("adjclose")
            if ac and isinstance(ac, list) and ac[0].get("adjclose"):
                adj = ac[0]["adjclose"]
        for i, t in enumerate(ts):
            v = adj[i] if (adj and i < len(adj) and adj[i] is not None) else \
                (closes[i] if i < len(closes) else None)
            if v is None:
                continue
            d = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
            series[d] = round(float(v), 6)
        if series:
            save_json(path, {"_last": max(series), "_fetched": today_iso,
                             "_symbol": symbol, "series": series})
        time.sleep(pause)
        return series
    except (KeyError, IndexError, TypeError) as e:
        print(f"  ! {symbol}: parse error {type(e).__name__} ({str(e)[:60]})")
        return series


if __name__ == "__main__":
    from datetime import date
    start, end = date(2019, 1, 1), date.today()
    tests = ["AAPL", "MSFT", "NVDA",            # sample stocks
             "URTH", "SPY", "^GSPC",            # global + US benchmarks
             "OSEBX.OL", "^OSEAX", "EWGS", "ENOR",  # Oslo Bors candidates
             "NOK=X"]                            # FX USD/NOK
    for s in tests:
        ser = fetch_series(s, start, end, force=True)
        if ser:
            ks = sorted(ser)
            print(f"OK  {s:10s} pts={len(ser):5d}  {ks[0]} .. {ks[-1]}  last={ser[ks[-1]]}")
        else:
            print(f"XX  {s:10s} NO DATA")
