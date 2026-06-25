"""Daily pipeline orchestrator.

Steps: refresh House trades -> fetch prices + run backtest -> build dashboard.
Run locally:   python run.py
In CI (GitHub Actions) this is the single entrypoint executed each morning.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline"))

import fetch_trades        # noqa: E402
import backtest            # noqa: E402
import build_dashboard     # noqa: E402


def main():
    t0 = time.time()
    print("=" * 60)
    print("CONGRESS vs INDEX — daily pipeline")
    print("=" * 60)

    print("\n[1/3] Refreshing congressional trades...")
    fetch_trades.fetch()

    print("\n[2/3] Fetching prices + running backtest...")
    backtest.run()

    print("\n[3/3] Building dashboard...")
    build_dashboard.build()

    print(f"\nDone in {time.time() - t0:.0f}s.")


if __name__ == "__main__":
    main()
