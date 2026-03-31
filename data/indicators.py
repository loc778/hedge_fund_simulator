# data/indicators.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import ta
import time

from config import TICKERS, TABLES
from data.db import get_engine, save_to_db

engine = get_engine()

def calculate_indicators(df):
    """
    Calculate all technical indicators for a single stock DataFrame.
    Keeping this as a separate function means you can easily add
    or remove indicators later without touching the main loop.
    """

    # ── Moving Averages ───────────────────────────────────────────────
    df["SMA_20"]  = ta.trend.sma_indicator(df["Close"], window=20)
    df["SMA_50"]  = ta.trend.sma_indicator(df["Close"], window=50)
    df["SMA_200"] = ta.trend.sma_indicator(df["Close"], window=200)
    df["EMA_9"]   = ta.trend.ema_indicator(df["Close"], window=9)
    df["EMA_21"]  = ta.trend.ema_indicator(df["Close"], window=21)

    # ── MACD ──────────────────────────────────────────────────────────
    macd          = ta.trend.MACD(df["Close"], window_fast=12,
                                   window_slow=26, window_sign=9)
    df["MACD"]        = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"]   = macd.macd_diff()

    # ── RSI ───────────────────────────────────────────────────────────
    df["RSI_14"] = ta.momentum.rsi(df["Close"], window=14)

    # ── Bollinger Bands ───────────────────────────────────────────────
    bb            = ta.volatility.BollingerBands(df["Close"],
                                                  window=20, window_dev=2)
    df["BB_Upper"]  = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"]  = bb.bollinger_lband()

    # ── ATR ───────────────────────────────────────────────────────────
    df["ATR_14"] = ta.volatility.average_true_range(
        df["High"], df["Low"], df["Close"], window=14
    )

    # ── Stochastic ────────────────────────────────────────────────────
    stoch         = ta.momentum.StochasticOscillator(
        df["High"], df["Low"], df["Close"], window=14, smooth_window=3
    )
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # ── ADX ───────────────────────────────────────────────────────────
    df["ADX_14"] = ta.trend.adx(df["High"], df["Low"], df["Close"], window=14)

    # ── OBV ───────────────────────────────────────────────────────────
    df["OBV"] = ta.volume.on_balance_volume(df["Close"], df["Volume"])

    # ── VWAP Deviation ────────────────────────────────────────────────
    df["VWAP_Dev"] = (
        (df["Close"] - df["VWAP_Daily"]) / df["VWAP_Daily"] * 100
    )

    return df


def process_ticker(df, ticker):
    """
    Process a single ticker — calculate indicators,
    round values, drop incomplete rows, return clean result.
    Isolated here so adding a new stock type later is easy.
    """
    if len(df) < 30:
        return None, "not enough rows"

    df = calculate_indicators(df)

    indicator_cols = [
        "Date", "Ticker",
        "SMA_20", "SMA_50", "SMA_200", "EMA_9", "EMA_21",
        "MACD", "MACD_Signal", "MACD_Hist", "RSI_14",
        "BB_Upper", "BB_Middle", "BB_Lower", "ATR_14",
        "Stoch_K", "Stoch_D", "ADX_14",
        "OBV", "VWAP_Dev"
    ]

    result = df[indicator_cols].copy()

    # Round all numeric columns to 4 decimal places
    numeric_cols = result.select_dtypes(include="number").columns
    result[numeric_cols] = result[numeric_cols].round(4)

    # Drop rows where core indicators are still NaN
    # These are the warmup rows at the start of each series
    result.dropna(subset=["RSI_14", "MACD"], inplace=True)

    return result, None


# ── Main ──────────────────────────────────────────────────────────────
print("📥 Loading OHLCV data from MySQL...")

ohlcv = pd.read_sql(
    f"SELECT * FROM {TABLES['ohlcv']}",   # ← reads table name from config
    con=engine
)
ohlcv["Date"] = pd.to_datetime(ohlcv["Date"])
ohlcv = ohlcv.sort_values(["Ticker", "Date"]).reset_index(drop=True)

tickers_in_db = ohlcv["Ticker"].unique()
print(f"✅ Loaded {len(ohlcv):,} rows across {len(tickers_in_db)} stocks\n")

all_data = []
failed   = []

for ticker in tickers_in_db:
    df = ohlcv[ohlcv["Ticker"] == ticker].copy().reset_index(drop=True)

    result, error = process_ticker(df, ticker)

    if error:
        print(f"  ⚠️  {ticker} — {error}")
        failed.append(ticker)
        continue

    all_data.append(result)
    print(f"  ✅ {ticker} — {len(result)} rows")

if all_data:
    combined = pd.concat(all_data).reset_index(drop=True)
    save_to_db(combined, TABLES["indicators"], engine)   # ← reads from config

if failed:
    print(f"\n⚠️  {len(failed)} failed: {failed}")