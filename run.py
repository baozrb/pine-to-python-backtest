"""Run the SuperTrend backtest on both engines, verify they agree, and write the report."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import engine_backtrader
import engine_pandas
from data import load_ohlcv
from metrics import summarize
from supertrend import supertrend

SYMBOL, START, END = "SPY", "2015-01-01", "2026-09-30"
FACTOR, ATR_PERIOD = 3.0, 10
OUT = Path(__file__).parent / "output"


def check_engines_agree(eq_a, tr_a, eq_b, tr_b) -> float:
    """Raise if the two engines disagree; return the largest equity difference."""
    if len(tr_a) != len(tr_b):
        raise AssertionError(f"trade count differs: {len(tr_a)} vs {len(tr_b)}")
    cols = ["entry_date", "exit_date", "shares"]
    pd.testing.assert_frame_equal(tr_a[cols].reset_index(drop=True), tr_b[cols].reset_index(drop=True), check_dtype=False)
    diff = float((eq_a - eq_b).abs().max())
    if diff > 1e-6:
        raise AssertionError(f"equity curves differ by up to {diff}")
    return diff


def plot_signals(df, st, trades, path, last_n=500):
    d, s = df.iloc[-last_n:], st.iloc[-last_n:]
    t = trades[trades["entry_date"] >= d.index[0]]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(d.index, d["close"], color="#444", lw=1, label="Close")
    ax.plot(s.index, s["supertrend"].where(s["direction"] < 0), color="#2a9d4b", lw=1.5, label="SuperTrend (up)")
    ax.plot(s.index, s["supertrend"].where(s["direction"] > 0), color="#d1453b", lw=1.5, label="SuperTrend (down)")
    ax.scatter(t["entry_date"], t["entry_price"], marker="^", color="#2a9d4b", s=70, zorder=3, label="Entry")
    ax.scatter(t["exit_date"], t["exit_price"], marker="v", color="#d1453b", s=70, zorder=3, label="Exit")
    ax.set_title(f"{SYMBOL} SuperTrend({ATR_PERIOD}, {FACTOR}) - last {last_n} bars")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_equity(equity, buy_hold, path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(equity.index, equity, color="#2a6fdb", label="SuperTrend")
    ax1.plot(buy_hold.index, buy_hold, color="#999", label="Buy & Hold")
    ax1.set_yscale("log")
    ax1.set_title(f"{SYMBOL} equity curve (log scale)")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    for series, color in ((equity, "#2a6fdb"), (buy_hold, "#999")):
        ax2.plot(series.index, (series / series.cummax() - 1) * 100, color=color)
    ax2.set_ylabel("Drawdown %")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    df = load_ohlcv(SYMBOL, START, END)
    st = supertrend(df, FACTOR, ATR_PERIOD)
    cfg = engine_pandas.Config()

    eq_pd, tr_pd = engine_pandas.run(df, st["direction"], cfg)
    eq_bt, tr_bt = engine_backtrader.run(df, st["direction"], cfg)
    diff = check_engines_agree(eq_pd, tr_pd, eq_bt, tr_bt)
    print(f"Engines agree: {len(tr_pd)} trades, max equity difference {diff:.2e}")

    buy_hold = cfg.initial_cash * df["close"] / df["close"].iloc[0]
    stats = pd.DataFrame({"SuperTrend": summarize(eq_pd, tr_pd), "Buy & Hold": summarize(buy_hold)})
    print(stats.to_string())

    plot_signals(df, st, tr_pd, OUT / "signals.png")
    plot_equity(eq_pd, buy_hold, OUT / "equity.png")
    tr_pd.to_csv(OUT / "trades.csv", index=False, float_format="%.4f")
    df.join(st).to_csv(OUT / "supertrend_values.csv", float_format="%.4f")  # for checking against TradingView
    (OUT / "report.md").write_text(
        f"# {SYMBOL} SuperTrend({ATR_PERIOD}, {FACTOR}) backtest, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}\n\n"
        f"Backtrader and the from-scratch pandas engine produced identical results "
        f"({len(tr_pd)} trades, max equity difference {diff:.1e}).\n\n"
        f"{stats.to_markdown()}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
