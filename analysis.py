"""
MAG7 vs S&P 500 project: step 2, analysis.

Reads the CSV files in data/ and writes charts and tables to output/.
Run:  py -m pip install pandas matplotlib   then   py analysis.py

Method notes (repeat these in the report):
- Market cap = split-adjusted shares outstanding x closing price (full, not float-adjusted).
- Total S&P 500 float-adjusted market cap = index level x S&P divisor
  (quarter-end divisor values, linearly interpolated, held flat after the last value).
- Alphabet is counted once (total shares x GOOGL price).
- Tesla is excluded before it joined the S&P 500 on 21 Dec 2020.
- Meta share counts before June 2022 are back-filled from the earliest available value.
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA, OUT = "data", "output"
os.makedirs(OUT, exist_ok=True)
STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
NAMES = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon",
         "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla"}
TSLA_JOIN = pd.Timestamp("2020-12-21")

# S&P 500 divisor, millions, quarter-end (source: YCharts, S&P 500 Divisor)
DIVISOR = {
    "2014-12-31": 8861.60, "2015-03-31": 8851.25, "2015-06-30": 8830.99, "2015-09-30": 8810.57,
    "2015-12-31": 8757.39, "2016-03-31": 8718.72, "2016-06-30": 8667.94, "2016-09-30": 8643.59,
    "2016-12-31": 8606.26, "2017-03-31": 8581.63, "2017-06-30": 8567.30, "2017-09-30": 8565.26,
    "2017-12-31": 8535.74, "2018-03-31": 8518.41, "2018-06-30": 8474.31, "2018-09-30": 8434.96,
    "2018-12-31": 8387.79, "2019-03-31": 8332.84, "2019-06-30": 8302.34, "2019-09-30": 8300.00,
    "2019-12-31": 8282.73, "2020-03-31": 8289.27, "2020-06-30": 8269.11, "2020-09-30": 8286.67,
    "2020-12-31": 8428.67, "2021-03-31": 8462.19, "2021-06-30": 8452.53, "2021-09-30": 8482.43,
    "2021-12-31": 8467.26, "2022-03-31": 8451.33, "2022-06-30": 8427.99, "2022-09-30": 8399.95,
    "2022-12-31": 8369.04, "2023-03-31": 8357.13, "2023-06-30": 8350.37, "2023-09-30": 8380.85,
    "2023-12-31": 8394.13, "2024-03-31": 8388.77, "2024-06-30": 8395.39, "2024-09-30": 8451.34,
    "2024-12-31": 8467.89, "2025-03-31": 8473.83, "2025-06-30": 8461.08, "2025-09-30": 8529.16,
    "2025-12-31": 8536.69,
}

INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
C_MAG, C_REST, C_SPX = "#2563eb", "#9ca3af", "#111827"
STOCK_COL = dict(zip(STOCKS, ["#2563eb", "#0891b2", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#db2777"]))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def save(fig, name, title, subtitle):
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold", color=INK, y=1.02)
    fig.text(0.01, 0.955, subtitle, ha="left", fontsize=9, color=MUTED)
    fig.text(0.01, -0.02, "Source: Yahoo Finance, S&P divisor via YCharts. Author's calculations.",
             fontsize=7.5, color=MUTED)
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)


# ---------- load ----------
close = pd.read_csv(f"{DATA}/prices_close.csv", index_col=0, parse_dates=True)
adj = pd.read_csv(f"{DATA}/prices_adj_close.csv", index_col=0, parse_dates=True)
spy = pd.read_csv(f"{DATA}/spy_prices.csv", index_col=0, parse_dates=True)
shares = pd.read_csv(f"{DATA}/shares_outstanding.csv", index_col=0, parse_dates=True)
splits = pd.read_csv(f"{DATA}/splits.csv", parse_dates=["date"])
adj["SPY"] = spy["Adj Close"].reindex(adj.index)
dates = close.index

# ---------- clean shares ----------
sh = pd.DataFrame(index=dates)
for t in STOCKS:
    s = shares[t].dropna()
    s = s[s > 0]
    for _, r in splits[splits.ticker == t].iterrows():   # put every count on today's split basis
        s.loc[s.index < r.date] *= r.ratio
    med = s.rolling(15, center=True, min_periods=3).median()
    s = s[(s / med - 1).abs() < 0.10]                       # drop data spikes
    sh[t] = s.reindex(dates.union(s.index)).ffill().reindex(dates).bfill()

mcap = sh * close[STOCKS]
mcap.loc[mcap.index < TSLA_JOIN, "TSLA"] = 0.0

div = pd.Series(DIVISOR)
div.index = pd.to_datetime(div.index)
div = div.reindex(div.index.union(dates)).interpolate("time").ffill().reindex(dates)
total = close["^GSPC"] * div * 1e6
w = mcap.div(total, axis=0)
W = w.sum(axis=1)

# ---------- 1. weight over time ----------
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.stackplot(w.index, [w[t] * 100 for t in STOCKS], colors=[STOCK_COL[t] for t in STOCKS],
             labels=[NAMES[t] for t in STOCKS], alpha=0.9, linewidth=0)
ax.set_ylabel("Share of S&P 500 market cap (%)")
ax.set_xlim(dates[0], dates[-1])
ax.legend(loc="upper left", ncol=4, frameon=False, fontsize=8.5)
ax.annotate(f"{W.iloc[-1]*100:.0f}%", (dates[-1], W.iloc[-1] * 100), xytext=(-30, 8),
            textcoords="offset points", fontweight="bold", color=INK)
ax.annotate(f"{W.iloc[0]*100:.0f}%", (dates[0], W.iloc[0] * 100), xytext=(4, 8),
            textcoords="offset points", fontweight="bold", color=INK)
save(fig, "1_mag7_weight.png", "Seven stocks now make up more than a third of the S&P 500",
     "Combined MAG7 weight in the S&P 500, 2015 to 2026 (Tesla included from Dec 2020)")

# ---------- 2. annual return attribution ----------
ye = close.groupby(close.index.year).tail(1).index
starts = [dates[0]] + list(ye[:-1])
rows = []
for s, e in zip(starts, ye):
    spx_r = close.loc[e, "^GSPC"] / close.loc[s, "^GSPC"] - 1
    contrib = {t: w.loc[s, t] * (close.loc[e, t] / close.loc[s, t] - 1) for t in STOCKS}
    if s < TSLA_JOIN <= e:   # Tesla contributes only from its join date
        contrib["TSLA"] = w.loc[TSLA_JOIN:, "TSLA"].iloc[0] * (close.loc[e, "TSLA"] / close.loc[TSLA_JOIN:, "TSLA"].iloc[0] - 1)
    mag = sum(contrib.values())
    rows.append({"year": e.year, "sp500_return": spx_r, "mag7_contribution": mag,
                 "rest_contribution": spx_r - mag, "mag7_weight_start": w.loc[s].sum(),
                 **{f"{t}_contribution": v for t, v in contrib.items()}})
attr = pd.DataFrame(rows).set_index("year")
attr["mag7_share_of_return"] = attr.mag7_contribution / attr.sp500_return
attr.round(4).to_csv(f"{OUT}/annual_attribution.csv")

fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(attr))
ax.bar(x, attr.mag7_contribution * 100, color=C_MAG, label="MAG7 contribution", width=0.62)
ax.bar(x, attr.rest_contribution * 100, bottom=np.where((attr.rest_contribution > 0) == (attr.mag7_contribution > 0),
       attr.mag7_contribution * 100, 0), color=C_REST, label="Other ~493 stocks", width=0.62)
ax.scatter(x, attr.sp500_return * 100, color=C_SPX, zorder=3, s=22, label="S&P 500 price return")
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(x, [str(y) if y != dates[-1].year else f"{y} YTD" for y in attr.index])
ax.set_ylabel("Percentage points")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
save(fig, "2_return_attribution.png", "Where the S&P 500's annual return came from",
     "Contribution to S&P 500 price return, MAG7 versus the rest of the index")

# ---------- 3. MAG7 basket vs the other 493 ----------
r = close.pct_change()
r_mag_contrib = (w.shift(1)[STOCKS] * r[STOCKS]).sum(axis=1)
r_spx = r["^GSPC"]
r_rest = (r_spx - r_mag_contrib) / (1 - W.shift(1))
r_mag = r_mag_contrib / W.shift(1)
idx = pd.DataFrame({"S&P 500": (1 + r_spx).cumprod(), "MAG7 (cap-weighted)": (1 + r_mag).cumprod(),
                    "S&P 500 ex-MAG7": (1 + r_rest).cumprod()}).fillna(1) * 100
idx.to_csv(f"{OUT}/growth_index.csv")
fig, ax = plt.subplots(figsize=(9, 4.6))
for col, c in zip(idx, [C_SPX, C_MAG, C_REST]):
    ax.plot(idx.index, idx[col], color=c, lw=1.8, label=col)
    ax.annotate(f"{idx[col].iloc[-1]:.0f}", (idx.index[-1], idx[col].iloc[-1]), xytext=(4, -3),
                textcoords="offset points", color=c, fontweight="bold", fontsize=9)
ax.set_yscale("log")
ax.set_yticks([100, 200, 400, 800, 1600], ["100", "200", "400", "800", "1,600"])
ax.set_ylabel("Growth of 100 (log scale, price only)")
ax.legend(frameon=False, fontsize=8.5)
save(fig, "3_mag7_vs_rest.png", "The MAG7 pulled away from the rest of the market",
     "Price growth of 100 invested in January 2015")

# ---------- 4. SPY vs RSP ----------
tr = adj[["SPY", "RSP"]].dropna()
tr = tr / tr.iloc[0] * 100
roll = adj[["SPY", "RSP"]].pct_change(252).dropna()
spread = (roll["SPY"] - roll["RSP"]) * 100
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
a1.plot(tr.index, tr.SPY, color=C_MAG, lw=1.8, label="SPY (cap-weighted)")
a1.plot(tr.index, tr.RSP, color=C_REST, lw=1.8, label="RSP (equal-weighted)")
for col, c in [("SPY", C_MAG), ("RSP", C_REST)]:
    a1.annotate(f"{tr[col].iloc[-1]:.0f}", (tr.index[-1], tr[col].iloc[-1]), xytext=(4, -3),
                textcoords="offset points", color=c, fontweight="bold", fontsize=9)
a1.set_ylabel("Total return, start = 100")
a1.legend(frameon=False, fontsize=8.5)
a2.fill_between(spread.index, spread, 0, where=spread >= 0, color=C_MAG, alpha=0.8, lw=0)
a2.fill_between(spread.index, spread, 0, where=spread < 0, color=C_REST, alpha=0.9, lw=0)
a2.axhline(0, color=INK, lw=0.8)
a2.set_ylabel("12m return gap (pp)")
save(fig, "4_spy_vs_rsp.png", "Cap-weighted beat equal-weighted, mostly because of seven stocks",
     "SPY versus RSP total return including dividends, and the rolling 12-month gap")

# ---------- 5. stress test ----------
Wn = W.iloc[-1]
shocks = [-10, -20, -30, -40, -50]
stress = pd.DataFrame({"mag7_fall_pct": shocks,
                       "sp500_impact_rest_flat_pct": [s * Wn for s in shocks]})
# 2022 episode: peak-to-trough contribution
p, t_ = pd.Timestamp("2022-01-03"), close.loc["2022", "^GSPC"].idxmin()
spx22 = close.loc[t_, "^GSPC"] / close.loc[p, "^GSPC"] - 1
mag22 = (w.loc[p, STOCKS] * (close.loc[t_, STOCKS] / close.loc[p, STOCKS] - 1)).sum()
stress.to_csv(f"{OUT}/stress_test.csv", index=False)
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh([f"MAG7 fall {abs(s)}%" for s in shocks][::-1], stress.sp500_impact_rest_flat_pct[::-1],
        color=C_MAG, height=0.55)
for i, v in enumerate(stress.sp500_impact_rest_flat_pct[::-1]):
    ax.text(v - 0.3, i, f"{v:.1f}%", va="center", ha="right", color=INK, fontsize=9)
ax.set_xlabel("Impact on the S&P 500 if the other stocks are flat (%)")
ax.set_xlim(min(stress.sp500_impact_rest_flat_pct) * 1.2, 0)
ax.grid(axis="y", visible=False)
save(fig, "5_stress_test.png", "A MAG7 sell-off now hits the whole index hard",
     f"Mechanical index impact at today's {Wn*100:.0f}% MAG7 weight")

# ---------- summary ----------
cagr = lambda s: (s.iloc[-1] / s.iloc[0]) ** (365.25 / (s.index[-1] - s.index[0]).days) - 1
summary = {
    "data_end": str(dates[-1].date()),
    "mag7_weight_start_pct": round(W.iloc[0] * 100, 1),
    "mag7_weight_now_pct": round(Wn * 100, 1),
    "mag7_weight_peak_pct": round(W.max() * 100, 1), "peak_date": str(W.idxmax().date()),
    "largest_single_weight_now": f"{NAMES[w.iloc[-1].idxmax()]} {w.iloc[-1].max()*100:.1f}%",
    "cagr_sp500_price_pct": round(cagr(idx["S&P 500"]) * 100, 1),
    "cagr_mag7_pct": round(cagr(idx["MAG7 (cap-weighted)"]) * 100, 1),
    "cagr_ex_mag7_pct": round(cagr(idx["S&P 500 ex-MAG7"]) * 100, 1),
    "spy_total_return_pct": round(tr.SPY.iloc[-1] - 100, 0),
    "rsp_total_return_pct": round(tr.RSP.iloc[-1] - 100, 0),
    "mag7_share_of_return_2023_2025_pct": round(attr.loc[2023:2025, "mag7_contribution"].sum()
                                               / attr.loc[2023:2025, "sp500_return"].sum() * 100, 0),
    "drawdown_2022_sp500_pct": round(spx22 * 100, 1),
    "drawdown_2022_mag7_contribution_pp": round(mag22 * 100, 1),
}
pd.Series(summary).to_csv(f"{OUT}/summary.csv", header=["value"])
print(pd.Series(summary).to_string())
print(attr[["sp500_return", "mag7_contribution", "rest_contribution", "mag7_weight_start"]].mul(100).round(1).to_string())
