# data/macro.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv
import time

from config import DATA_PERIOD, MACRO_YFINANCE, MACRO_FRED, TABLES
from data.db import get_engine, save_to_db

load_dotenv()
engine = get_engine()
fred   = Fred(api_key=os.getenv("FRED_API_KEY"))

# ── Helper — download with retry ──────────────────────────────────────
def download_with_retry(symbol, period, retries=3, delay=5):
    """
    Retry yfinance downloads up to 3 times.
    Handles connection timeouts which are common with
    Indian market symbols like ^INDIAVIX.
    """
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol, period=period,
                interval="1d", progress=False,
                timeout=20              # Longer timeout for Indian symbols
            )
            if not df.empty:
                return df
            print(f"    Attempt {attempt} — empty response")
        except Exception as e:
            print(f"    Attempt {attempt} failed: {e}")
        time.sleep(delay)
    return None

# ── Step 1: Fetch daily market data via yfinance ──────────────────────
print("📥 Fetching daily macro data from yfinance...\n")

daily_frames = []

for col_name, symbol in MACRO_YFINANCE.items():
    print(f"  Fetching {col_name} ({symbol})...")
    df = download_with_retry(symbol, DATA_PERIOD)

    if df is None or df.empty:
        print(f"  ⚠️  {col_name} — failed after retries, will be NULL in table")
        continue

    # Handle MultiIndex columns from newer yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    series = df["Close"].rename(col_name)
    daily_frames.append(series)
    print(f"  ✅ {col_name} — {len(series)} rows")

# ── Handle case where some or all yfinance fetches failed ─────────────
if daily_frames:
    daily = pd.concat(daily_frames, axis=1,sort=True)
else:
    # Create empty DataFrame with date range so FRED data still saves
    print("\n⚠️  All yfinance fetches failed — creating date scaffold from FRED")
    daily = pd.DataFrame()

daily.index.name = "Date"

# ── Step 2: Fetch monthly macro data via FRED ─────────────────────────
print("\n📥 Fetching macro indicators from FRED...\n")

fred_frames = []

for col_name, series_id in MACRO_FRED.items():
    try:
        series = fred.get_series(
            series_id,
            observation_start="2022-01-01"
        )
        series.name = col_name
        series.index.name = "Date"
        fred_frames.append(series)
        print(f"  ✅ {col_name} ({series_id}) — {len(series)} observations")

    except Exception as e:
        print(f"  ❌ {col_name} ({series_id}) — {e}")

if not fred_frames:
    print("❌ No FRED data fetched — check your FRED_API_KEY in .env")
    exit()

fred_df = pd.concat(fred_frames, axis=1,sort=True).round(4)

# ── Step 3: Build combined daily table ───────────────────────────────
if not daily.empty:

    # Convert both indexes to plain Python date strings
    # then back to datetime — most reliable method across
    # all Python and pandas versions including 3.14
    daily.index = pd.to_datetime(
        [str(d)[:10] for d in daily.index]
    )
    fred_df.index = pd.to_datetime(
        [str(d)[:10] for d in fred_df.index]
    )
    # Forward fill FRED monthly onto daily trading dates
    # Fill gaps within fred_df first (monthly data has nulls on daily bond dates)
    # Then reindex to trading dates
    fred_df = fred_df.ffill()
    fred_daily = fred_df.reindex(daily.index, method="ffill")
    combined = pd.concat([daily, fred_daily], axis=1)
else:
    combined = fred_df.copy()

# Reset index BEFORE any column access
combined.reset_index(inplace=True)
combined.rename(columns={"index": "Date"}, inplace=True)

# Ensure Date column is clean date type
combined["Date"] = pd.to_datetime(
    combined["Date"].astype(str).str[:10]
).dt.date

# Drop rows where ALL market columns are null
market_cols = [c for c in list(MACRO_YFINANCE.keys())
               if c in combined.columns]
if market_cols:
    combined.dropna(how="all", subset=market_cols, inplace=True)

combined = combined.round(4)
# ── Step 4: Save to MySQL ─────────────────────────────────────────────
save_to_db(combined, TABLES["macro"], engine)
