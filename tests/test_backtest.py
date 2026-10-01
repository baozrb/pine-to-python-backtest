"""Offline tests on synthetic data: indicator correctness, no look-ahead, engine agreement."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine_backtrader
import engine_pandas
from run import check_engines_agree
from supertrend import rma, supertrend


def random_ohlc(n=800, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n)))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.01, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.01, n))
    idx = pd.bdate_range("2020-01-01", periods=n, name="date")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1e6}, index=idx)


def test_rma_matches_wilder_definition():
    x = pd.Series([1.0, 2, 3, 4, 5, 6])
    out = rma(x, 3)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == pytest.approx(2.0)  # SMA seed of 1, 2, 3
    assert out.iloc[3] == pytest.approx(4 / 3 + 2 * 2 / 3)
    assert out.iloc[5] == pytest.approx((6 + 2 * ((5 + 2 * out.iloc[3]) / 3)) / 3)


def test_supertrend_line_sits_on_the_correct_side_of_price():
    df = random_ohlc()
    st = supertrend(df).dropna()
    up = st["direction"] == -1
    close = df.loc[st.index, "close"]
    assert set(st["direction"].unique()) <= {-1.0, 1.0}
    assert (st.loc[up, "supertrend"] <= close[up]).all()
    assert (st.loc[~up, "supertrend"] >= close[~up]).all()


def test_supertrend_has_no_lookahead():
    df = random_ohlc()
    full = supertrend(df)
    cut = 500
    future_changed = df.copy()
    future_changed.iloc[cut:] *= 1.5  # scramble everything after the cut
    partial = supertrend(future_changed)
    pd.testing.assert_frame_equal(full.iloc[:cut], partial.iloc[:cut])


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_backtrader_and_pandas_engines_agree(seed):
    df = random_ohlc(seed=seed)
    direction = supertrend(df)["direction"]
    cfg = engine_pandas.Config()
    eq_pd, tr_pd = engine_pandas.run(df, direction, cfg)
    eq_bt, tr_bt = engine_backtrader.run(df, direction, cfg)
    assert len(tr_pd) > 5
    check_engines_agree(eq_pd, tr_pd, eq_bt, tr_bt)
    np.testing.assert_allclose(tr_pd["pnl"], tr_bt["pnl"], rtol=1e-9)


def test_orders_fill_at_next_open():
    df = random_ohlc()
    direction = supertrend(df)["direction"]
    _, trades = engine_pandas.run(df, direction, engine_pandas.Config())
    flips_up = direction.index[direction.diff() < 0]
    first = trades.iloc[0]
    signal_bar = df.index.get_loc(flips_up[0])
    assert first["entry_date"] == df.index[signal_bar + 1]
    assert first["entry_price"] == df["open"].iloc[signal_bar + 1]
