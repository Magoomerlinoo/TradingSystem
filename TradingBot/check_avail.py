from MetaTrader5 import copy_rates_from_pos, TIMEFRAME_M15
from utils.generate_training_csv import fetch_ohlcv
df = fetch_ohlcv("USDCNH", "M15")
print(len(df))  # zero means “no data available” on your broker