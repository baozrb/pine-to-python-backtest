"""The same strategy in backtrader, fed with the precomputed SuperTrend direction."""
import backtrader as bt
import pandas as pd

from engine_pandas import Config


class SuperTrendFeed(bt.feeds.PandasData):
    lines = ("direction",)
    params = (("direction", -1),)  # -1 = find the column by name


class SuperTrendLongOnly(bt.Strategy):
    params = dict(position_pct=0.95)

    def __init__(self):
        self.equity, self.trades = [], []
        self._entry = None

    def next(self):
        self.equity.append((self.data.datetime.date(0), self.broker.getvalue()))
        if len(self) < 2:
            return
        change = self.data.direction[0] - self.data.direction[-1]
        if not self.position and change < 0:
            size = int(self.p.position_pct * self.broker.getvalue() / self.data.close[0])
            self.buy(size=size)  # market order: fills at the next bar's open
        elif self.position and change > 0:
            self.close()

    def notify_order(self, order):
        if order.status != order.Completed:
            return
        ex = order.executed
        date = bt.num2date(ex.dt).date()
        if order.isbuy():
            self._entry = (date, ex.price, ex.size * ex.price + ex.comm)
        else:
            size = -ex.size
            self.trades.append({
                "entry_date": self._entry[0], "entry_price": self._entry[1],
                "exit_date": date, "exit_price": ex.price,
                "shares": size, "pnl": size * ex.price - ex.comm - self._entry[2],
            })


def run(df: pd.DataFrame, direction: pd.Series, cfg: Config) -> tuple[pd.Series, pd.DataFrame]:
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(SuperTrendFeed(dataname=df.assign(direction=direction)))
    cerebro.addstrategy(SuperTrendLongOnly, position_pct=cfg.position_pct)
    cerebro.broker.setcash(cfg.initial_cash)
    cerebro.broker.setcommission(commission=cfg.commission)
    strat = cerebro.run()[0]

    dates, values = zip(*strat.equity)
    equity = pd.Series(values, index=pd.to_datetime(dates), name="equity")
    equity.index.name = df.index.name
    trades = pd.DataFrame(strat.trades)
    for col in ("entry_date", "exit_date"):
        if col in trades:
            trades[col] = pd.to_datetime(trades[col])
    return equity, trades
