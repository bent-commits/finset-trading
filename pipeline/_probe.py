"""Probe Capitol Trades data sources to decide ingestion strategy."""
import urllib.request
import json

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.capitoltrades.com",
    "Referer": "https://www.capitoltrades.com/",
}


def get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def main():
    url = "https://bff.capitoltrades.com/trades?page=1&pageSize=5&sortBy=-pubDate"
    print("=== Capitol Trades BFF /trades ===")
    try:
        status, body = get(url, HEADERS)
        print("HTTP", status, "bytes", len(body))
        data = json.loads(body)
        rows = data.get("data", data if isinstance(data, list) else [])
        print("rows:", len(rows))
        if rows:
            print("--- sample keys ---")
            print(list(rows[0].keys()))
            print("--- sample row (trimmed) ---")
            print(json.dumps(rows[0], indent=2)[:1500])
        print("--- meta ---")
        print(json.dumps(data.get("meta", {}), indent=2)[:600])
    except Exception as e:
        print("BFF failed:", type(e).__name__, str(e)[:300])


if __name__ == "__main__":
    main()
