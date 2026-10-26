"""
MAG7 vs S&P 500 project: step 1b, fills two gaps in the first download.

How to run (same folder as before, in the VS Code terminal):
    py download_fix.py

It adds two files to the "data" folder:
    spy_prices.csv     SPY prices (failed the first time)
    splits.csv         stock split history for the MAG7, needed to fix share counts
Send both files back to Claude.
"""

import os
import time
import pandas as pd
import yfinance as yf

START = "2015-01-01"
OUT = "data"
MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]


def strip_tz(index):
    idx = pd.to_datetime(index)
    return idx.tz_localize(None) if idx.tz is not None else idx


def main():
    os.makedirs(OUT, exist_ok=True)

    print("Downloading SPY...")
    spy = pd.DataFrame()
    for attempt in range(3):
        spy = yf.Ticker("SPY").history(start=START, auto_adjust=False)
        if not spy.empty:
            break
        print(f"  attempt {attempt + 1} returned nothing, retrying...")
        time.sleep(5)
    if spy.empty:
        print("  SPY still failed. Wait a few minutes and run this file again.")
    else:
        spy.index = strip_tz(spy.index)
        spy[["Close", "Adj Close"]].to_csv(os.path.join(OUT, "spy_prices.csv"))
        print(f"  SPY saved: {len(spy)} days, from {spy.index.min().date()}")

    print("Downloading split history...")
    rows = []
    for t in MAG7:
        s = yf.Ticker(t).splits
        if s is None or s.empty:
            continue
        s.index = strip_tz(s.index)
        for d, r in s[s.index >= START].items():
            rows.append({"ticker": t, "date": d.date(), "ratio": r})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "splits.csv"), index=False)
    print(f"  {len(rows)} splits saved")
    print("\nDone.")


if __name__ == "__main__":
    main()
