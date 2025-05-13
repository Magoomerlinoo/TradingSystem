# data_sources/yahoo_data.py

import yfinance as yf
import pandas as pd

def download_yahoo_data(symbol, start="2020-01-01", end="2021-01-01"):
    """
    Returns a pandas DataFrame of daily OHLCV data from Yahoo Finance.
    Columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    """
    df = yf.download(symbol, start=start, end=end)
    if df.empty:
        raise RuntimeError(f"No Yahoo data returned for {symbol}.")
    df.reset_index(inplace=True)
    df.rename(columns={'Date':'time','Open':'open','High':'high','Low':'low',
                       'Close':'close','Volume':'volume'}, inplace=True)
    return df

def unify_for_bot(df):
    """
    Optional helper: unify columns to match your bot's expected 
    structure (like 'time', 'close', etc.). 
    For instance, if your code wants 'tick_volume' or 5-min intervals, 
    you might resample the data here.
    """
    # Example: rename 'volume' to 'tick_volume' if your indicators rely on 'tick_volume'
    df.rename(columns={'volume':'tick_volume'}, inplace=True)
    return df
