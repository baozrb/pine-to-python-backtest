"""Download daily OHLCV from Yahoo Finance and cache it as Parquet."""
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).parent / "data"


def load_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Split-adjusted (not dividend-adjusted) prices, matching TradingView's default chart."""
    path = DATA_DIR / f"{symbol}_{start}_{end}.parquet"
    if path.exists():
        return pd.read_parquet(path)

    raw = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if raw.empty:
        raise RuntimeError(f"No data returned for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.xs(symbol, axis=1, level="Ticker")

    df = raw[["Open", "High", "Low", "Close", "Volume"]].rename(columns=str.lower)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(path)
    return df
