"""Fetch and normalize US Congress stock trades.

Sources (provider-agnostic; v1 = House, Senate to follow):
  - House: TattooedHead/house-stock-watcher-data (clean JSON, auto-updated daily,
    derived from official House Clerk PTR filings). Fallback: House Clerk ZIP.

Normalized trade schema (one dict per transaction):
  {chamber, politician, ticker, tx_date (ISO), pub_date (ISO),
   side ('buy'|'sell'), amount_mid (float USD), amount_range, owner}
"""
import re
from common import http_get_json, save_json, load_json, parse_mdy, iso, DATA_DIR
import os

HOUSE_URL = ("https://raw.githubusercontent.com/TattooedHead/"
             "house-stock-watcher-data/main/data/all_transactions.json")

TRADES_PATH = os.path.join(DATA_DIR, "trades.json")

VALID_TICKER = re.compile(r"^[A-Z][A-Z.\-]{0,6}$")


def _side(t):
    t = (t or "").strip().lower()
    if t.startswith("purchase"):
        return "buy"
    if t.startswith("sale") or t.startswith("sell"):
        return "sell"
    return None  # exchange / receive / unknown -> skip


def _clean_ticker(tk):
    if not tk:
        return None
    tk = tk.strip().upper().replace("\x00", "")
    if tk in ("", "--", "N/A", "NA", "NONE", "--."):
        return None
    if not VALID_TICKER.match(tk):
        return None
    return tk


def normalize_house(rows):
    out = []
    for r in rows:
        if (r.get("asset_type") or "").strip() != "Stock":
            continue
        side = _side(r.get("type"))
        if not side:
            continue
        tk = _clean_ticker(r.get("ticker"))
        if not tk:
            continue
        txd = parse_mdy(r.get("transaction_date"))
        pubd = parse_mdy(r.get("disclosure_date"))
        if not pubd:
            continue
        # If tx date missing/after pub date, fall back to pub date.
        if not txd or txd > pubd:
            txd = pubd
        amid = r.get("amount_mid")
        try:
            amid = float(amid) if amid is not None else None
        except (TypeError, ValueError):
            amid = None
        if not amid or amid <= 0:
            amid = _parse_amount(r.get("amount"))
        if not amid:
            continue
        out.append({
            "chamber": "house",
            "politician": (r.get("representative") or "").strip(),
            "ticker": tk,
            "tx_date": iso(txd),
            "pub_date": iso(pubd),
            "side": side,
            "amount_mid": amid,
            "amount_range": (r.get("amount") or "").strip(),
            "owner": (r.get("owner") or "").strip(),
        })
    return out


def _parse_amount(s):
    """Fallback: midpoint of '$1,001 - $15,000'."""
    if not s:
        return None
    nums = [int(x.replace(",", "")) for x in re.findall(r"[\d,]+", s)]
    if len(nums) >= 2:
        return (nums[0] + nums[1]) / 2.0
    if len(nums) == 1:
        return float(nums[0])
    return None


def fetch():
    print("Downloading House trades...")
    rows = http_get_json(HOUSE_URL, timeout=120)
    print(f"  raw House rows: {len(rows):,}")
    trades = normalize_house(rows)
    print(f"  normalized stock trades: {len(trades):,}")
    trades.sort(key=lambda t: t["pub_date"])
    save_json(TRADES_PATH, trades)
    return trades


def stats(trades):
    if not trades:
        print("no trades")
        return
    buys = sum(1 for t in trades if t["side"] == "buy")
    sells = len(trades) - buys
    pols = len(set(t["politician"] for t in trades))
    tickers = len(set(t["ticker"] for t in trades))
    print(f"  date range: {trades[0]['pub_date']} .. {trades[-1]['pub_date']}")
    print(f"  buys={buys:,} sells={sells:,} politicians={pols} tickers={tickers}")
    from collections import Counter
    top = Counter(t["ticker"] for t in trades if t["side"] == "buy").most_common(10)
    print("  top bought tickers:", ", ".join(f"{k}({v})" for k, v in top))


if __name__ == "__main__":
    tr = fetch()
    stats(tr)
