"""SuperTrend, ported from TradingView's built-in ta.supertrend (Pine v6)."""
import numpy as np
import pandas as pd


def rma(x: pd.Series, length: int) -> pd.Series:
    """Pine ta.rma: seeded with the SMA of the first `length` values, then Wilder smoothing."""
    values = x.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) >= length:
        out[length - 1] = values[:length].mean()
        alpha = 1.0 / length
        for i in range(length, len(values)):
            out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return pd.Series(out, index=x.index)


def atr(df: pd.DataFrame, length: int) -> pd.Series:
    """Pine ta.atr. On the first bar there is no previous close, so TR = high - low."""
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)  # max() skips the NaNs on the first bar
    return rma(tr, length)


def supertrend(df: pd.DataFrame, factor: float = 3.0, atr_period: int = 10) -> pd.DataFrame:
    """Returns columns `supertrend` and `direction`.

    direction follows Pine's convention: -1 = uptrend (line below price), 1 = downtrend.
    """
    hl2 = ((df["high"] + df["low"]) / 2).to_numpy()
    close = df["close"].to_numpy()
    a = atr(df, atr_period).to_numpy()
    upper = hl2 + factor * a
    lower = hl2 - factor * a

    n = len(df)
    st = np.full(n, np.nan)
    direction = np.ones(n)  # Pine reports 1 during the ATR warm-up
    start = atr_period - 1  # first bar with a valid ATR
    if n > start:
        st[start] = upper[start]

    for i in range(start + 1, n):
        # Bands only ratchet toward price, unless the previous close broke through them.
        if not (lower[i] > lower[i - 1] or close[i - 1] < lower[i - 1]):
            lower[i] = lower[i - 1]
        if not (upper[i] < upper[i - 1] or close[i - 1] > upper[i - 1]):
            upper[i] = upper[i - 1]

        if direction[i - 1] == 1:  # previous SuperTrend was the upper band
            direction[i] = -1 if close[i] > upper[i] else 1
        else:
            direction[i] = 1 if close[i] < lower[i] else -1
        st[i] = lower[i] if direction[i] == -1 else upper[i]

    return pd.DataFrame({"supertrend": st, "direction": direction}, index=df.index)
