"""Fetch and normalize US Senate stock trades from the official Senate eFD.

The eFD site sits behind a WAF that blocks plain urllib/curl, so we use
curl_cffi (real-browser TLS impersonation). Flow:
  1. accept the prohibition agreement (sets a session cookie)
  2. page through the PTR (Periodic Transaction Report) list since the last run
  3. fetch + parse each new electronic PTR's transaction table

Output is the SAME normalized schema as House (chamber='senate'), so the rest
of the pipeline treats House + Senate uniformly. Parsed trades + processed PTR
ids are persisted (committed) as a seed, so daily runs only fetch new filings.
"""
import os
import re
import html
import time

from common import save_json, load_json, parse_mdy, iso, DATA_DIR, today
from fetch_trades import _side, _clean_ticker, _parse_amount

BASE = "https://efdsearch.senate.gov"
SENATE_PATH = os.path.join(DATA_DIR, "senate_trades.json")
SEEN_PATH = os.path.join(DATA_DIR, "senate_seen.json")
SEED_START = "01/01/2019"          # earliest filing date to seed from


def _session():
    from curl_cffi import requests as cr
    s = cr.Session(impersonate="chrome")
    s.get(BASE + "/search/home/", timeout=40)
    tok = s.cookies.get("csrftoken")
    s.post(BASE + "/search/home/",
           data={"prohibition_agreement": "1", "csrfmiddlewaretoken": tok},
           headers={"Referer": BASE + "/search/home/"}, timeout=40)
    return s


def _list_ptrs(s, start_date):
    """Return [(name, ptr_id, ptr_url, filing_date)] for electronic PTRs filed
    on/after start_date (MM/DD/YYYY)."""
    out, start, length, total = [], 0, 100, None
    while True:
        tok = s.cookies.get("csrftoken")
        payload = {
            "draw": "1", "start": str(start), "length": str(length),
            "report_types": "[11]", "filer_types": "[]",
            "submitted_start_date": start_date + " 00:00:00",
            "submitted_end_date": "", "candidate_state": "", "senator_state": "",
            "office_id": "", "first_name": "", "last_name": "",
            "csrfmiddlewaretoken": tok,
        }
        r = s.post(BASE + "/search/report/data/", data=payload, timeout=40,
                   headers={"Referer": BASE + "/search/home/",
                            "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": tok})
        d = r.json()
        if total is None:
            total = d.get("recordsTotal", 0)
        rows = d.get("data", [])
        if not rows:
            break
        for row in rows:
            name = html.unescape(re.sub(r"<[^>]+>", " ", row[0] + " " + row[1])).strip()
            name = re.sub(r"\s+", " ", name)
            m = re.search(r'href="(/search/view/ptr/([^/"]+)/?)"', row[3])
            if not m:
                continue                          # paper filing -> not parseable
            fdate = html.unescape(re.sub(r"<[^>]+>", " ", row[4] if len(row) > 4 else row[-1])).strip()
            out.append((name, m.group(2), BASE + m.group(1), fdate))
        start += length
        if start >= total:
            break
        time.sleep(0.25)
    return out


def _parse_ptr(s, ptr_url, name, filing_date):
    pubd = parse_mdy(filing_date)
    if not pubd:
        return []
    try:
        ph = s.get(ptr_url, headers={"Referer": BASE + "/search/"}, timeout=40).text
    except Exception:
        return []
    trades = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", ph, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 8:
            continue
        c = [html.unescape(re.sub(r"<[^>]+>", " ", x)).strip() for x in tds]
        # cols: 0:# 1:date 2:owner 3:ticker 4:asset 5:asset_type 6:type 7:amount
        if c[5].strip() != "Stock":
            continue
        side = _side(c[6])
        tk = _clean_ticker(c[3])
        if not side or not tk:
            continue
        txd = parse_mdy(c[1]) or pubd
        if txd > pubd:
            txd = pubd
        amid = _parse_amount(c[7])
        if not amid:
            continue
        trades.append({
            "chamber": "senate", "politician": name, "ticker": tk,
            "tx_date": iso(txd), "pub_date": iso(pubd), "side": side,
            "amount_mid": amid, "amount_range": c[7].strip(), "owner": c[2],
        })
    return trades


def fetch():
    existing = load_json(SENATE_PATH, []) or []
    seen = load_json(SEEN_PATH, {}) or {}
    seen_ids = set(seen.get("ptr_ids", []))
    since = seen.get("last_filing_date") or SEED_START
    print(f"  Senate: listing PTRs filed since {since} ...")
    try:
        s = _session()
        ptrs = _list_ptrs(s, since)
    except Exception as e:
        print(f"  ! Senate eFD unavailable ({type(e).__name__}); keeping {len(existing)} cached trades")
        return existing
    new = [p for p in ptrs if p[1] not in seen_ids]
    print(f"  {len(ptrs)} PTRs in window, {len(new)} new")
    all_trades = list(existing)
    max_date = parse_mdy(since)

    def _checkpoint(lfd_str):
        save_json(SENATE_PATH, sorted(all_trades, key=lambda t: t["pub_date"]))
        save_json(SEEN_PATH, {"ptr_ids": sorted(seen_ids), "last_filing_date": lfd_str})

    for i, (name, pid, url, fdate) in enumerate(new, 1):
        all_trades.extend(_parse_ptr(s, url, name, fdate))
        seen_ids.add(pid)
        fd = parse_mdy(fdate)
        if fd and (max_date is None or fd > max_date):
            max_date = fd
        if i % 200 == 0:
            print(f"    parsed {i}/{len(new)} ...")
            _checkpoint(since)          # keep 'since' until full pass completes (safe resume)
        time.sleep(0.25)
    # full pass done: advance the watermark to the newest filing seen
    _checkpoint((max_date or today()).strftime("%m/%d/%Y"))
    print(f"  Senate trades total: {len(all_trades):,} (from {len(seen_ids):,} PTRs)")
    return all_trades


if __name__ == "__main__":
    tr = fetch()
    if tr:
        buys = sum(1 for t in tr if t["side"] == "buy")
        pols = len(set(t["politician"] for t in tr))
        print(f"  range {tr[0]['pub_date']}..{tr[-1]['pub_date']} | buys={buys} senators={pols}")
