# utils/plotter.py

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

def plot_candlestick(df, symbol="Unknown Symbol", show=True):
    """
    Plots a candlestick chart using 'mplfinance' from a DataFrame with 
    columns [time, open, high, low, close, ...].
    """
    df2 = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df2['time']):
        df2['time'] = pd.to_datetime(df2['time'], unit='s', utc=True)
    df2.set_index('time', inplace=True)
    df2.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','tick_volume':'Volume'}, inplace=True)

    mpf.plot(
        df2,
        type='candle',
        title=f"Candlestick - {symbol}",
        style='yahoo',
        mav=(50,200),
        volume=True,
        show_nontrading=True
    )
    if show:
        plt.show()

def plot_equity_curve(equity_series, title="Equity Curve", show=True):
    """
    equity_series => list or pd.Series of equity values over time or trades
    """
    plt.figure()
    plt.plot(equity_series, label="Equity")
    plt.title(title)
    plt.xlabel("Time/Trades")
    plt.ylabel("Equity")
    plt.legend()
    if show:
        plt.show()

def plot_trades(df: pd.DataFrame, symbol: str, save_path: str = None):
    """
    Overlays trade entries on the price chart using directional markers.
    """
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])
    plt.figure(figsize=(12, 6))
    plt.plot(df['time'], df['close'], label="Price", color='black')
    longs = df[df['direction'] == 'long']
    shorts = df[df['direction'] == 'short']
    plt.scatter(longs['time'], longs['entry'], label="Longs", marker="^", color="green")
    plt.scatter(shorts['time'], shorts['entry'], label="Shorts", marker="v", color="red")
    plt.title(f"Trades on {symbol}")
    plt.legend()
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()