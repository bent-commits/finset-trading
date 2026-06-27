"""Daily pipeline orchestrator.

Steps: House trades + Senate trades -> merge -> backtest -> dashboard.
Run locally:   python run.py
In CI (GitHub Actions) this is the single entrypoint executed each morning.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))

import fetch_trades        # noqa: E402  (House)
import fetch_senate        # noqa: E402  (Senate)
import backtest            # noqa: E402
import build_dashboard     # noqa: E402
from common import save_json, DATA_DIR  # noqa: E402


def main():
    t0 = time.time()
    print("=" * 60)
    print("FINSET TRADING — daily pipeline (House + Senate)")
    print("=" * 60)

    print("\n[1/4] House trades...")
    house = fetch_trades.fetch()

    print("\n[2/4] Senate trades...")
    try:
        senate = fetch_senate.fetch()
    except Exception as e:
        print(f"  ! Senate step failed ({type(e).__name__}); continuing House-only")
        senate = []

    merged = sorted(house + senate, key=lambda t: t["pub_date"])
    save_json(os.path.join(DATA_DIR, "trades.json"), merged)
    print(f"  merged: {len(merged):,} trades "
          f"(House {len(house):,} + Senate {len(senate):,})")

    print("\n[3/4] Fetching prices + running backtest...")
    backtest.run()

    print("\n[4/4] Building dashboard...")
    build_dashboard.build()

    print(f"\nDone in {time.time() - t0:.0f}s.")


if __name__ == "__main__":
    main()
