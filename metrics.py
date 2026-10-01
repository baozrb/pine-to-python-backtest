"""Performance statistics for an equity curve and its trades."""
import math

import pandas as pd


def summarize(equity: pd.Series, trades: pd.DataFrame | None = None) -> dict:
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    growth = equity.iloc[-1] / equity.iloc[0]
    stats = {
        "Total return": f"{growth - 1:.1%}",
        "CAGR": f"{growth ** (1 / years) - 1:.2%}",
        "Max drawdown": f"{(equity / equity.cummax() - 1).min():.1%}",
        "Sharpe (rf=0)": f"{rets.mean() / rets.std() * math.sqrt(252):.2f}",
        "Trades": "-", "Win rate": "-", "Profit factor": "-",
    }
    if trades is not None and len(trades):
        wins = trades["pnl"] > 0
        losses = -trades.loc[~wins, "pnl"].sum()
        stats["Trades"] = str(len(trades))
        stats["Win rate"] = f"{wins.mean():.1%}"
        stats["Profit factor"] = f"{trades.loc[wins, 'pnl'].sum() / losses:.2f}" if losses else "inf"
    return stats
