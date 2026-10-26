"""
MAG7 vs S&P 500 project: step 1, data download.

How to run (in the VS Code terminal):
    pip install -r requirements.txt
    python download_data.py

It creates a folder called "data" next to this file with three CSV files.
Send those three files back to Claude.
"""

import os
import pandas as pd
import yfinance as yf

START = "2015-01-01"
OUT = "data"

# Alphabet has two share classes in the index, so both are pulled.
MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA"]
# SPY = cap-weighted S&P 500 ETF, RSP = equal-weighted S&P 500 ETF, ^GSPC = the index itself.
BENCH = ["SPY", "RSP", "^GSPC"]


def strip_tz(index):
    idx = pd.to_datetime(index)
    return idx.tz_localize(None) if idx.tz is not None else idx


def main():
    os.makedirs(OUT, exist_ok=True)
    tickers = MAG7 + BENCH

    print("Downloading daily prices...")
    px = yf.download(tickers, start=START, auto_adjust=False, progress=False)
    if px.empty:
        raise SystemExit("No price data returned. Check your internet connection and try again.")

    adj = px["Adj Close"]  # includes dividends, used for total returns
    close = px["Close"]    # raw price, used with shares outstanding for market cap
    adj.index = strip_tz(adj.index)
    close.index = strip_tz(close.index)
    adj.to_csv(os.path.join(OUT, "prices_adj_close.csv"))
    close.to_csv(os.path.join(OUT, "prices_close.csv"))
    print(f"  Prices saved: {adj.shape[0]} days, {adj.shape[1]} tickers")

    print("Downloading shares outstanding history...")
    shares = {}
    for t in MAG7:
        try:
            s = yf.Ticker(t).get_shares_full(start=START)
            if s is None or s.empty:
                print(f"  {t}: no shares data returned")
                continue
            s.index = strip_tz(s.index)
            s = s[~s.index.duplicated(keep="last")].sort_index()
            shares[t] = s
            print(f"  {t}: {len(s)} data points")
        except Exception as e:
            print(f"  {t}: failed ({e})")

    if shares:
        pd.DataFrame(shares).sort_index().to_csv(os.path.join(OUT, "shares_outstanding.csv"))

    # Quick sanity check so you can see it worked.
    missing = [t for t in tickers if t not in adj.columns or adj[t].dropna().empty]
    print("\nDone. Files are in the 'data' folder.")
    if missing:
        print("Warning, no prices for:", ", ".join(missing))
    print("First valid date per ticker:")
    print(adj.apply(lambda c: c.first_valid_index()).to_string())


if __name__ == "__main__":
    main()
