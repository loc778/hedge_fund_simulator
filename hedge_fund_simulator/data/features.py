# data/features.py
# ═══════════════════════════════════════════════════════════
# FEATURE ENGINEERING PIPELINE
# Combines all 5 data layers into one unified feature set.
# One row per stock per day — ready for ML model training.
# ═══════════════════════════════════════════════════════════

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sqlalchemy import text
from data.db import get_engine, save_to_db
from config import TABLES

engine = get_engine()

# ── Step 1: Load all tables from MySQL ───────────────────────────────
print("📥 Loading all data layers from MySQL...\n")

ohlcv = pd.read_sql(
    f"SELECT * FROM {TABLES['ohlcv']}", con=engine
)
indicators = pd.read_sql(
    f"SELECT * FROM {TABLES['indicators']}", con=engine
)
fundamentals = pd.read_sql(
    f"SELECT * FROM {TABLES['fundamentals']}", con=engine
)
sentiment = pd.read_sql(
    f"SELECT * FROM {TABLES['sentiment']}", con=engine
)
macro = pd.read_sql(
    f"SELECT * FROM {TABLES['macro']}", con=engine
)

# Convert date columns
ohlcv["Date"]         = pd.to_datetime(ohlcv["Date"]).dt.date
indicators["Date"]    = pd.to_datetime(indicators["Date"]).dt.date
sentiment["Date"]     = pd.to_datetime(sentiment["Date"]).dt.date
macro["Date"]         = pd.to_datetime(macro["Date"]).dt.date
fundamentals["Period"]= pd.to_datetime(fundamentals["Period"]).dt.date

print(f"  ✅ OHLCV:        {len(ohlcv):,} rows")
print(f"  ✅ Indicators:   {len(indicators):,} rows")
print(f"  ✅ Fundamentals: {len(fundamentals):,} rows")
print(f"  ✅ Sentiment:    {len(sentiment):,} rows")
print(f"  ✅ Macro:        {len(macro):,} rows")

# ── Step 2: Build base — OHLCV + Indicators ───────────────────────────
print("\n🔧 Merging layers...")

# Rename Adj Close to avoid space issues
ohlcv.rename(columns={"Adj Close": "Adj_Close"}, inplace=True)

# Select only needed OHLCV columns
ohlcv_cols = ["Date", "Ticker", "Open", "High", "Low",
              "Close", "Adj_Close", "Volume", "VWAP_Daily"]
base = ohlcv[ohlcv_cols].copy()

# Merge indicators
ind_cols = ["Date", "Ticker",
            "SMA_20", "SMA_50", "SMA_200", "EMA_9", "EMA_21",
            "MACD", "MACD_Signal", "MACD_Hist", "RSI_14",
            "BB_Upper", "BB_Middle", "BB_Lower", "ATR_14",
            "Stoch_K", "Stoch_D", "ADX_14", "OBV", "VWAP_Dev"]
base = base.merge(indicators[ind_cols], on=["Date", "Ticker"], how="left")
print(f"  ✅ OHLCV + Indicators merged: {len(base):,} rows")

# ── Step 3: Add price-derived features ───────────────────────────────
print("  🔧 Computing price features per stock...")

all_stocks = []

for ticker in base["Ticker"].unique():
    df = base[base["Ticker"] == ticker].copy()
    df = df.sort_values("Date").reset_index(drop=True)

    # Returns
    df["Return_1d"]  = df["Close"].pct_change(1).round(4)
    df["Return_5d"]  = df["Close"].pct_change(5).round(4)
    df["Return_21d"] = df["Close"].pct_change(21).round(4)

    # Rolling volatility (20-day std of daily returns)
    df["Volatility_20d"] = (
        df["Return_1d"].rolling(20).std().round(4)
    )

    # 52-week high/low proximity ratios
    df["High_52w_Ratio"] = (
        df["Close"] / df["High"].rolling(252).max()
    ).round(4)
    df["Low_52w_Ratio"] = (
        df["Close"] / df["Low"].rolling(252).min()
    ).round(4)

    # Volume ratio vs 20-day average
    df["Volume_Ratio_20d"] = (
        df["Volume"] / df["Volume"].rolling(20).mean()
    ).round(4)

    # Bollinger Band width (measures squeeze/expansion)
    df["BB_Width"] = (
        (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]
    ).round(4)

    # Target variable — 21-day FORWARD return
    # shift(-21) looks ahead 21 days
    # This is what the model learns to predict
    df["Target_Return_21d"] = (
        df["Close"].pct_change(21).shift(-21).round(4)
    )

    # Target direction — 1 if price goes up, 0 if down
    df["Target_Direction"] = (
        (df["Target_Return_21d"] > 0).astype(int)
    )

    all_stocks.append(df)

base = pd.concat(all_stocks).reset_index(drop=True)
print(f"  ✅ Price features computed: {len(base):,} rows")

# ── Step 4: Merge Fundamentals (forward fill quarterly) ───────────────
print("  🔧 Merging fundamentals...")

fund_cols = ["Ticker", "Period",
             "PE_Ratio", "PB_Ratio", "EV_EBITDA", "ROE", "ROA",
             "ROCE", "Debt_to_Equity", "FCF_Yield",
             "Dividend_Yield", "EPS_Basic"]
fund = fundamentals[fund_cols].copy()
fund.rename(columns={"Period": "Date"}, inplace=True)
fund = fund.sort_values(["Ticker", "Date"])

# Merge and forward fill — each trading day gets last known quarter
base = base.merge(fund, on=["Date", "Ticker"], how="left")

# Forward fill fundamentals within each stock
fund_feature_cols = ["PE_Ratio", "PB_Ratio", "EV_EBITDA", "ROE",
                     "ROA", "ROCE", "Debt_to_Equity", "FCF_Yield",
                     "Dividend_Yield", "EPS_Basic"]
base = base.sort_values(["Ticker", "Date"])
base[fund_feature_cols] = (
    base.groupby("Ticker")[fund_feature_cols]
    .transform(lambda x: x.ffill())
)
print(f"  ✅ Fundamentals merged and forward filled")

# ── Step 5: Merge Sentiment (forward fill daily) ──────────────────────
print("  🔧 Merging sentiment...")

sent_cols = ["Date", "Ticker",
             "Sentiment_Score", "Positive_Score", "Negative_Score"]
sent = sentiment[sent_cols].copy()
sent = sent.sort_values(["Ticker", "Date"])

base = base.merge(sent, on=["Date", "Ticker"], how="left")

# Forward fill sentiment — last known score carries forward
# Missing sentiment treated as neutral (0) after ffill exhausted
sent_cols_fill = ["Sentiment_Score", "Positive_Score", "Negative_Score"]
base[sent_cols_fill] = (
    base.groupby("Ticker")[sent_cols_fill]
    .transform(lambda x: x.ffill())
)
base[sent_cols_fill] = base[sent_cols_fill].fillna(0)
print(f"  ✅ Sentiment merged")

# ── Step 6: Merge Macro (daily — direct join) ─────────────────────────
print("  🔧 Merging macro data...")

macro_cols = ["Date", "India_VIX", "USDINR", "Crude_Oil", "Gold",
              "CPI_India", "GDP_India", "Fed_Funds_Rate",
              "US_CPI", "US_10Y_Bond"]
base = base.merge(macro[macro_cols], on="Date", how="left")

# Forward fill macro for any missing trading days
macro_feature_cols = ["India_VIX", "USDINR", "Crude_Oil", "Gold",
                      "CPI_India", "GDP_India", "Fed_Funds_Rate",
                      "US_CPI", "US_10Y_Bond"]
base[macro_feature_cols] = base[macro_feature_cols].ffill()
print(f"  ✅ Macro merged")

# ── Step 7: Final cleanup ─────────────────────────────────────────────
print("\n🔧 Final cleanup...")

# Drop rows where target is null
# (last 21 days of each stock — no future data to compute target)
base = base.dropna(subset=["Target_Return_21d"])

# Drop rows where core features are null
# (warmup period at start of each stock)
core_features = ["RSI_14", "MACD", "SMA_20", "Close"]
base = base.dropna(subset=core_features)

# Enforce column order
col_order = [
    "Date", "Ticker",
    "Open", "High", "Low", "Close", "Adj_Close",
    "Volume", "VWAP_Daily",
    "Return_1d", "Return_5d", "Return_21d",
    "Volatility_20d", "High_52w_Ratio", "Low_52w_Ratio",
    "Volume_Ratio_20d",
    "SMA_20", "SMA_50", "SMA_200", "EMA_9", "EMA_21",
    "MACD", "MACD_Signal", "MACD_Hist", "RSI_14",
    "BB_Upper", "BB_Middle", "BB_Lower", "BB_Width",
    "ATR_14", "Stoch_K", "Stoch_D", "ADX_14",
    "OBV", "VWAP_Dev",
    "PE_Ratio", "PB_Ratio", "EV_EBITDA", "ROE", "ROA",
    "ROCE", "Debt_to_Equity", "FCF_Yield",
    "Dividend_Yield", "EPS_Basic",
    "Sentiment_Score", "Positive_Score", "Negative_Score",
    "India_VIX", "USDINR", "Crude_Oil", "Gold",
    "CPI_India", "GDP_India", "Fed_Funds_Rate",
    "US_CPI", "US_10Y_Bond",
    "Target_Return_21d", "Target_Direction"
]
base = base[[c for c in col_order if c in base.columns]]

print(f"  ✅ Final shape: {len(base):,} rows × {len(base.columns)} columns")
print(f"  ✅ Stocks: {base['Ticker'].nunique()}")
print(f"  ✅ Date range: {base['Date'].min()} → {base['Date'].max()}")
print(f"  ✅ Target distribution:")
print(f"     Up days:   {base['Target_Direction'].sum():,}")
print(f"     Down days: {(base['Target_Direction']==0).sum():,}")

# ── Step 8: Save to MySQL ─────────────────────────────────────────────
save_to_db(base, TABLES["features"], engine)

print("\n🎯 Feature engineering complete — ready for ML training")