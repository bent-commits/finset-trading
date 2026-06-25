"""Shared utilities: HTTP, paths, date helpers. Pure stdlib (no pip deps)."""
import os
import json
import time
import gzip
import urllib.request
import urllib.error
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PRICES_DIR = os.path.join(DATA_DIR, "prices")
DOCS_DIR = os.path.join(ROOT, "docs")

for _d in (DATA_DIR, PRICES_DIR, DOCS_DIR):
    os.makedirs(_d, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BASE_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


def http_get(url, headers=None, timeout=60, retries=3, backoff=2.0):
    """GET a URL with browser-like headers, gzip-aware, with retries."""
    h = dict(BASE_HEADERS)
    if headers:
        h.update(headers)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except urllib.error.HTTPError as e:
            last_err = e
            # 404/401 won't fix on retry
            if e.code in (401, 403, 404):
                raise
            time.sleep(backoff * (attempt + 1))
        except Exception as e:
            last_err = e
            time.sleep(backoff * (attempt + 1))
    raise last_err


def http_get_json(url, headers=None, timeout=60, retries=3):
    return json.loads(http_get(url, headers=headers, timeout=timeout, retries=retries))


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_mdy(s):
    """Parse 'MM/DD/YYYY' -> date, tolerant of junk. Returns None on failure."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def iso(d):
    return d.isoformat() if isinstance(d, (date, datetime)) else d


def today():
    return date.today()
