"""Backtest engine: 'Congress copy' vs 3 index-fund benchmarks, in NOK.

Methodology (what a serious shop would model; documented in README):
  * LAG-AWARE: trades entered on DISCLOSURE date (pub_date), never the (secret)
    transaction date. This is the single most important realism factor.
  * STRATEGY A "Congress House basket": each month, hold the TOP_N tickers by
    trailing-12-month net congressional buying (buys minus sells, in $),
    conviction-weighted, capped at MAX_WEIGHT per name. Heavily-sold names fall
    out of the top list and exit. Long-only.
  * CURRENCY: US stocks valued in USD then converted to NOK at daily USD/NOK,
    so a Norwegian investor's FX exposure is included.
  * COSTS: per-rebalance commission+spread and a retail FX conversion fee on
    turnover; a small US dividend-withholding drag. Benchmarks bear an annual
    fund fee (TER). All disclosed and configurable below.
  * TOTAL RETURN: adjusted-close (dividends reinvested) for stocks/ETFs; the
    Oslo Bors price index gets a documented dividend add-back.
  * RISK: we report volatility, max drawdown and Sharpe, not just return.
"""
import os
import bisect
from datetime import date, timedelta
from collections import defaultdict

from common import load_json, save_json, DATA_DIR
import fetch_prices
import fetch_trades

# ----------------------------- configuration ------------------------------
START = date(2019, 1, 1)         # simulation start (post a full market cycle)
CAPITAL_NOK = 1_814_000          # the user's actual total across the DNB funds
TOP_N = 20                       # names held in the congress basket
LOOKBACK_DAYS = 365              # trailing window for the buy signal
MAX_WEIGHT = 0.10                # single-name cap (diversification)

TXN_COST = 0.0020                # 0.20% commission+spread on traded notional
FX_FEE = 0.0050                  # 0.50% retail FX conversion on traded notional
WHT_DRAG_ANNUAL = 0.0020         # ~US div yield x 15% withholding (congress)

RF_ANNUAL = 0.02                 # risk-free for Sharpe
TRADING_DAYS = 252

BENCHMARKS = {
    "Globalt indeksfond (MSCI World)": {"symbol": "URTH", "ccy": "USD",
                                        "ter": 0.0020, "div_addback": 0.0},
    "S&P 500 (USA)":                   {"symbol": "SPY",  "ccy": "USD",
                                        "ter": 0.0020, "div_addback": 0.0},
    "Oslo Bors (OSEBX)":               {"symbol": "OSEBX.OL", "ccy": "NOK",
                                        "ter": 0.0030, "div_addback": 0.034},
}
FX_SYMBOL = "NOK=X"
RESULTS_PATH = os.path.join(DATA_DIR, "results.json")
CONGRESS_NAME = "Congress (House + Senat)"

# The user's actual DNB fund portfolio, shown as one blended buy-and-hold box.
# Amounts define the weights; index proxies via Yahoo. Aktiv Rente (a NOK bond
# fund, no free price series) is approximated as a steady ~3%/yr sleeve.
DNB_NAME = "DNB-fond (vår portefølje)"
DNB_FUNDS = [
    {"name": "DNB Global Indeks A",   "symbol": "URTH",     "ccy": "USD", "amount": 900000, "ter": 0.0030},
    {"name": "DNB Norge Indeks A",    "symbol": "OSEBX.OL", "ccy": "NOK", "amount": 360000, "ter": 0.0030, "div_addback": 0.034},
    {"name": "DNB Global EM Indeks",  "symbol": "EEM",      "ccy": "USD", "amount": 180000, "ter": 0.0040},
    {"name": "DNB Aktiv Rente",       "symbol": None,       "amount": 374000, "fixed_annual": 0.030},
]
DNB_TOTAL = sum(f["amount"] for f in DNB_FUNDS)
DNB_SYMBOLS = [f["symbol"] for f in DNB_FUNDS if f["symbol"]]


# --------------------------- price lookup (ffill) --------------------------
class PriceBook:
    def __init__(self):
        self._dates = {}   # symbol -> sorted list of iso dates
        self._vals = {}    # symbol -> parallel list of values

    def add(self, symbol, series):
        ds = sorted(series)
        self._dates[symbol] = ds
        self._vals[symbol] = [series[d] for d in ds]

    def has(self, symbol):
        return symbol in self._dates and len(self._dates[symbol]) > 0

    def price(self, symbol, d_iso):
        """Last known price on or before d_iso (forward fill). None if before start."""
        ds = self._dates.get(symbol)
        if not ds:
            return None
        i = bisect.bisect_right(ds, d_iso) - 1
        if i < 0:
            return None
        return self._vals[symbol][i]

    def calendar(self, symbol, start_iso, end_iso):
        ds = self._dates.get(symbol, [])
        return [d for d in ds if start_iso <= d <= end_iso]


# --------------------------- congress signal -------------------------------
def build_signal_index(trades):
    """Sorted parallel arrays for fast windowed queries on pub_date."""
    rows = [(t["pub_date"], t["ticker"], t["side"], t["amount_mid"]) for t in trades]
    rows.sort(key=lambda r: r[0])
    return rows


def weights_as_of(sig_rows, as_of_iso, lookback_iso, top_n=TOP_N, cap=MAX_WEIGHT):
    """Top-N tickers by net buying ($ buys - $ sells) in (lookback, as_of], capped."""
    lo = bisect.bisect_left(sig_rows, (lookback_iso,))
    hi = bisect.bisect_right(sig_rows, (as_of_iso, chr(0x10FFFF)))
    net = defaultdict(float)
    for j in range(lo, hi):
        _, tk, side, amt = sig_rows[j]
        net[tk] += amt if side == "buy" else -amt
    pos = [(tk, v) for tk, v in net.items() if v > 0]
    if not pos:
        return {}
    pos.sort(key=lambda x: x[1], reverse=True)
    pos = pos[:top_n]
    total = sum(v for _, v in pos)
    w = {tk: v / total for tk, v in pos}
    return _apply_cap(w, cap)


def _apply_cap(w, cap):
    for _ in range(20):
        over = {k: v for k, v in w.items() if v > cap + 1e-9}
        if not over:
            break
        excess = sum(v - cap for v in over.values())
        for k in over:
            w[k] = cap
        under = {k: v for k, v in w.items() if v < cap - 1e-9}
        base = sum(under.values())
        if base <= 0:
            break
        for k in under:
            w[k] += excess * (w[k] / base)
    s = sum(w.values())
    return {k: v / s for k, v in w.items()} if s else w


def build_universe(sig_rows, start, end):
    """Every ticker that ever lands in a monthly top-(N+5) net-buy list."""
    uni = set()
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        as_of = date(y, m, 1).isoformat()
        lb = (date(y, m, 1) - timedelta(days=LOOKBACK_DAYS)).isoformat()
        uni.update(weights_as_of(sig_rows, as_of, lb, top_n=TOP_N + 5).keys())
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return uni


# ------------------------------ simulation ---------------------------------
def run_basket(cal, pb, weight_at, daily_drag):
    """Monthly-rebalanced long-only basket, valued daily in NOK, with costs.
    weight_at(date_iso) -> {ticker: target_weight}. Empty => hold current book."""
    shares = defaultdict(float)
    series = []
    cur_ym = None
    started = False

    def nav_now(d_iso, fx):
        v = 0.0
        for tk, sh in shares.items():
            if sh:
                p = pb.price(tk, d_iso)
                if p:
                    v += sh * p * fx
        return v

    for d in cal:
        fx = pb.price(FX_SYMBOL, d) or 1.0
        if d[:7] != cur_ym:                         # first trading day of a month
            cur_ym = d[:7]
            nav = nav_now(d, fx) if started else float(CAPITAL_NOK)
            w = {tk: wt for tk, wt in weight_at(d).items() if pb.price(tk, d)}
            sw = sum(w.values())
            if sw > 0 and nav > 0:
                w = {tk: wt / sw for tk, wt in w.items()}
                target = {tk: wt * nav for tk, wt in w.items()}            # NOK
                cur = {}
                for tk in set(list(shares) + list(w)):
                    p = pb.price(tk, d)
                    cur[tk] = (shares[tk] * p * fx) if (p and shares[tk]) else 0.0
                turnover = sum(abs(target.get(tk, 0.0) - cur.get(tk, 0.0))
                               for tk in set(list(cur) + list(target)))
                new = defaultdict(float)
                for tk, notion in target.items():
                    p = pb.price(tk, d)
                    if p:
                        new[tk] = (notion / fx) / p                        # NOK->USD->shares
                shares = new
                scale = (nav - turnover * (TXN_COST + FX_FEE)) / nav        # one-off cost haircut
                for tk in shares:
                    shares[tk] *= scale
                started = True
        for tk in list(shares):
            shares[tk] *= daily_drag
        series.append((d, round(nav_now(d, fx) if started else float(CAPITAL_NOK), 2)))
    return series


def dnb_series(cal, pb):
    """Blended buy-and-hold of the user's actual DNB funds, valued daily in NOK.
    Index sleeves use Yahoo (with TER drag); the Aktiv Rente bond sleeve is a
    steady fixed-rate approximation (no free NAV series exists for it)."""
    d0 = date.fromisoformat(cal[0])
    sleeves = []
    for f in DNB_FUNDS:
        nav0 = CAPITAL_NOK * f["amount"] / DNB_TOTAL
        if f["symbol"] is None:
            sleeves.append({"bond": True, "nav0": nav0, "r": f.get("fixed_annual", 0.03)})
        else:
            p0 = pb.price(f["symbol"], cal[0])
            fx0 = pb.price(FX_SYMBOL, cal[0]) if f["ccy"] == "USD" else 1.0
            sleeves.append({"bond": False, "units": nav0 / (p0 * fx0), "sym": f["symbol"],
                            "ccy": f["ccy"], "drag": 1.0,
                            "dter": (1 - f["ter"]) ** (1 / TRADING_DAYS),
                            "ddiv": (1 + f.get("div_addback", 0.0)) ** (1 / TRADING_DAYS)})
    series = []
    for d in cal:
        fx = pb.price(FX_SYMBOL, d) or 1.0
        tot = 0.0
        for s in sleeves:
            if s["bond"]:
                days = (date.fromisoformat(d) - d0).days
                tot += s["nav0"] * ((1 + s["r"]) ** (days / 365.0))
            else:
                p = pb.price(s["sym"], d)
                if not p:
                    continue
                fxx = fx if s["ccy"] == "USD" else 1.0
                s["drag"] *= s["dter"] * s["ddiv"]
                tot += s["units"] * p * fxx * s["drag"]
        series.append((d, round(tot, 2)))
    return series


def simulate(trades, pb, end):
    sig = build_signal_index(trades)
    cal = pb.calendar("SPY", START.isoformat(), end.isoformat())
    if not cal:
        raise RuntimeError("no trading calendar (SPY prices missing)")

    # ---- benchmarks: buy & hold from first day, daily fee drag ----
    bench_series = {}
    for name, cfg in BENCHMARKS.items():
        sym = cfg["symbol"]
        daily_ter = (1 - cfg["ter"]) ** (1 / TRADING_DAYS)
        daily_div = (1 + cfg["div_addback"]) ** (1 / TRADING_DAYS)
        p0 = pb.price(sym, cal[0])
        fx0 = pb.price(FX_SYMBOL, cal[0]) if cfg["ccy"] == "USD" else 1.0
        units = CAPITAL_NOK / (p0 * fx0)
        series, drag = [], 1.0
        for d in cal:
            p = pb.price(sym, d) or p0
            fx = pb.price(FX_SYMBOL, d) if cfg["ccy"] == "USD" else 1.0
            drag *= daily_ter * daily_div
            series.append((d, round(units * p * fx * drag, 2)))
        bench_series[name] = series

    daily_wht = (1 - WHT_DRAG_ANNUAL) ** (1 / TRADING_DAYS)

    def agg_weight(d_iso):
        lookback = (date.fromisoformat(d_iso) - timedelta(days=LOOKBACK_DAYS)).isoformat()
        return weights_as_of(sig, d_iso, lookback)

    cong = run_basket(cal, pb, agg_weight, daily_wht)
    dnb = dnb_series(cal, pb)

    out = {CONGRESS_NAME: cong, DNB_NAME: dnb}
    out.update(bench_series)
    return out


# ------------------------------ metrics ------------------------------------
def _slice(series, years, end_iso):
    if years is None:
        return series
    cutoff = (date.fromisoformat(end_iso) - timedelta(days=int(365.25 * years))).isoformat()
    i = bisect.bisect_left([d for d, _ in series], cutoff)
    return series[i:] if i < len(series) else series[-2:]


def _stats(s, end_iso):
    """Risk/return stats for a sub-series, rebased to CAPITAL_NOK at its start."""
    if len(s) < 2:
        v = s[-1][1] if s else CAPITAL_NOK
        d = s[-1][0] if s else end_iso
        return {"start_value": CAPITAL_NOK, "end_value": CAPITAL_NOK,
                "total_return": 0.0, "cagr": 0.0, "vol": 0.0,
                "max_drawdown": 0.0, "sharpe": 0.0, "from": d, "to": d}
    navs = [v for _, v in s]
    start_v, end_v = navs[0], navs[-1]
    n_days = (date.fromisoformat(s[-1][0]) - date.fromisoformat(s[0][0])).days or 1
    yrs_act = n_days / 365.25
    total_ret = end_v / start_v - 1
    cagr = (end_v / start_v) ** (1 / yrs_act) - 1 if start_v > 0 else 0
    scale = CAPITAL_NOK / start_v if start_v > 0 else 1.0   # rebase to 1.5 MNOK
    rets = [navs[i] / navs[i - 1] - 1 for i in range(1, len(navs)) if navs[i - 1] > 0]
    mean = sum(rets) / len(rets) if rets else 0
    var = sum((r - mean) ** 2 for r in rets) / len(rets) if rets else 0
    vol = (var ** 0.5) * (TRADING_DAYS ** 0.5)
    peak, mdd = navs[0], 0.0
    for v in navs:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    sharpe = (cagr - RF_ANNUAL) / vol if vol > 0 else 0
    return {"start_value": CAPITAL_NOK, "end_value": round(end_v * scale, 0),
            "total_return": round(total_ret, 4), "cagr": round(cagr, 4),
            "vol": round(vol, 4), "max_drawdown": round(mdd, 4),
            "sharpe": round(sharpe, 2), "from": s[0][0], "to": s[-1][0]}


def metrics(series, end_iso, launch_iso=None):
    res = {}
    for label, yrs in (("1y", 1), ("3y", 3), ("5y", 5), ("max", None)):
        s = _slice(series, yrs, end_iso)
        if len(s) >= 5:
            res[label] = _stats(s, end_iso)
    if launch_iso:
        res["live"] = _stats([p for p in series if p[0] >= launch_iso], end_iso)
    return res


def downsample(series, step=5):
    """Weekly-ish points for the chart, always keep last."""
    out = series[::step]
    if out and out[-1] != series[-1]:
        out.append(series[-1])
    return out


def run():
    trades = load_json(os.path.join(DATA_DIR, "trades.json"))
    if not trades:
        trades = fetch_trades.fetch()
    latest_trade = max(t["pub_date"] for t in trades)
    end = date.today()                      # value the book with the latest prices

    # fixed launch date for the live "from today" paper portfolio
    launch_path = os.path.join(DATA_DIR, "launch.json")
    launch = load_json(launch_path)
    if not launch:
        launch = {"date": end.isoformat()}
        save_json(launch_path, launch)
    launch_iso = launch["date"]

    sig = build_signal_index(trades)
    print("Building universe of held tickers...")
    universe = build_universe(sig, START, end)
    print(f"  {len(universe)} tickers ever held")

    pb = PriceBook()
    need = list(dict.fromkeys(
        sorted(universe) + DNB_SYMBOLS
        + [c["symbol"] for c in BENCHMARKS.values()] + [FX_SYMBOL]))
    print(f"Fetching prices for {len(need)} symbols (cached after first run)...")
    missing = []
    for i, sym in enumerate(need, 1):
        ser = fetch_prices.fetch_series(sym, START, end)
        if ser:
            pb.add(sym, ser)
        else:
            missing.append(sym)
        if i % 25 == 0:
            print(f"  {i}/{len(need)}")
    if missing:
        print(f"  no price data for {len(missing)} (likely delisted): {missing[:12]}")

    print("Simulating...")
    series = simulate(trades, pb, end)

    strategies = {}
    for name, s in series.items():
        strategies[name] = {"series": downsample(s),
                            "metrics": metrics(s, end.isoformat(), launch_iso)}

    result = {
        "generated_at": date.today().isoformat(),
        "data_through": end.isoformat(),
        "latest_trade": latest_trade,
        "launch": launch_iso,
        "capital_nok": CAPITAL_NOK,
        "start": START.isoformat(),
        "congress_name": CONGRESS_NAME,
        "dnb_name": DNB_NAME,
        "dnb_total": DNB_TOTAL,
        "dnb_funds": [{"name": f["name"], "weight": round(f["amount"] / DNB_TOTAL, 4),
                       "amount": f["amount"]} for f in DNB_FUNDS],
        "config": {
            "top_n": TOP_N, "lookback_days": LOOKBACK_DAYS, "max_weight": MAX_WEIGHT,
            "txn_cost": TXN_COST, "fx_fee": FX_FEE, "wht_drag": WHT_DRAG_ANNUAL,
        },
        "n_trades": len(trades),
        "strategies": strategies,
    }
    save_json(RESULTS_PATH, result)
    print(f"\nSaved {RESULTS_PATH}")
    _print_summary(result)
    return result


def _print_summary(result):
    name_w = max(len(n) for n in result["strategies"])
    for label, title in (("max", "SIDEN 2019"), ("5y", "SISTE 5 AR"),
                         ("3y", "SISTE 3 AR"), ("1y", "SISTE 1 AR")):
        rows = [(n, d["metrics"][label]) for n, d in result["strategies"].items()
                if label in d["metrics"]]
        if not rows:
            continue
        rows.sort(key=lambda r: r[1]["end_value"], reverse=True)
        span = f"{rows[0][1]['from']} -> {rows[0][1]['to']}"
        print(f"\n=== {title}  ({span}) — start {CAPITAL_NOK:,.0f} kr ===")
        for name, m in rows:
            print(f"  {name:{name_w}s} {m['end_value']:>13,.0f} kr  "
                  f"ret={m['total_return']*100:6.1f}%  CAGR={m['cagr']*100:5.1f}%  "
                  f"vol={m['vol']*100:4.1f}%  MDD={m['max_drawdown']*100:6.1f}%  "
                  f"Sharpe={m['sharpe']:.2f}")


if __name__ == "__main__":
    run()
