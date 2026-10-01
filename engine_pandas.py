"""A minimal bar-by-bar backtester written from scratch, used to cross-check backtrader."""
import math
from dataclasses import dataclass

import pandas as pd


@dataclass
class Config:
    initial_cash: float = 10_000.0
    commission: float = 0.0005  # 0.05% per side
    position_pct: float = 0.95  # share of equity committed on each entry


def run(df: pd.DataFrame, direction: pd.Series, cfg: Config) -> tuple[pd.Series, pd.DataFrame]:
    """Long-only SuperTrend. Signals are evaluated on the bar's close and filled at the
    next bar's open, like TradingView's default. Returns (equity at each close, closed trades)."""
    opens, closes = df["open"].to_numpy(), df["close"].to_numpy()
    change = direction.diff().to_numpy()

    cash, shares = cfg.initial_cash, 0
    order = None  # (side, size) waiting for the next open
    entry = None
    equity, trades = [], []

    for i, date in enumerate(df.index):
        if order is not None:
            side, size = order
            price = opens[i]
            if side == "buy":
                cost = size * price * (1 + cfg.commission)
                if 0 < size and cost <= cash:  # rejected if a gap up makes it unaffordable
                    cash -= cost
                    shares = size
                    entry = (date, price, cost)
            else:
                proceeds = shares * price * (1 - cfg.commission)
                cash += proceeds
                trades.append({
                    "entry_date": entry[0], "entry_price": entry[1],
                    "exit_date": date, "exit_price": price,
                    "shares": shares, "pnl": proceeds - entry[2],
                })
                shares = 0
            order = None

        if shares == 0 and change[i] < 0:
            order = ("buy", math.floor(cfg.position_pct * cash / closes[i]))
        elif shares > 0 and change[i] > 0:
            order = ("sell", shares)

        equity.append(cash + shares * closes[i])

    return pd.Series(equity, index=df.index, name="equity"), pd.DataFrame(trades)
