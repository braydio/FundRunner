# Minimal mplfinance trade plotter

import mplfinance as mpf
import pandas as pd


def plot_trades(df, trades=None, title="Trade Chart"):
    """
    df: pd.DataFrame with datetime index, OHLCV
    trades: optional list of dicts with 'date', 'profit'
    """
    addplots = []
    if trades:
        profit_series = pd.Series({t["date"]: t["profit"] for t in trades})
        addplots.append(mpf.make_addplot(profit_series, panel=1, color="g"))

    mpf.plot(df, type="candle", style="charles", title=title, addplot=addplots)
