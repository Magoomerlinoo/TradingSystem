# data_sources/mt5_data.py

import MetaTrader5 as mt5
import pandas as pd
import settings
from .fake_mt5_reader import FakeMT5Reader

def initialize_mt5():
    """
    Ensures MT5 is initialized. Call this once at bot startup (though bot.py already does it).
    """
    if not mt5.initialize():
        raise ConnectionError("Failed to initialize MT5.")
    return True

def get_ohlc_data(symbol, timeframe=settings.DEFAULT_TIMEFRAME, bars=None): # configurable
    """
    Fetches OHLCV data from MetaTrader5 for a given symbol and timeframe.
    Returns a pandas DataFrame with columns: time, open, high, low, close, tick_volume
    Bars default to 'settings.BAR_COUNT' if not specified.
    """
    if bars is None:
        bars = settings.BAR_COUNT

    # Ensure symbol is selected
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol {symbol} not found or not available in MT5.")

    # Copy rates from position 0 to 'bars'
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No data returned for symbol {symbol}.")

    df = pd.DataFrame(rates)
    return df.dropna()

def get_account_info():
    """
    Retrieves MetaTrader 5 account info. 
    Returns 'None' if not available.
    """
    return mt5.account_info()

def shutdown_mt5():
    """
    Cleanly shuts down MetaTrader5 connection.
    """
    mt5.shutdown()
