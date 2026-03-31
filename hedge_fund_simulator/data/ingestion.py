# data/ingestion.py
# ⚠️  SCALE-UP NOTE:
# This script uses yfinance — suitable for testing only.
# When scaling to 500 stocks / 10 years:
# Replace with data/bhavcopy_ingestion.py (Layer 1)
# Replace with data/screener_fundamentals.py (Layer 2)
# Config flag: set DATA_SOURCE = "bhavcopy" in config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ssl
import urllib3
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── SSL fix for corporate proxy (self-signed cert in chain) ──────────
os.environ["CURL_CA_BUNDLE"] = ""          # disables curl SSL verification
os.environ["REQUESTS_CA_BUNDLE"] = ""     # disables requests SSL verification
_orig_create_default = ssl.create_default_context
def _no_verify_ssl(*args, **kwargs):
    ctx = _orig_create_default(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
ssl.create_default_context = _no_verify_ssl

import yfinance as yf
import pandas as pd
import time

from config import TICKERS, BATCH_SIZE, BATCH_DELAY, DATA_PERIOD, TABLES
from data.db import get_engine, save_to_db

engine = get_engine()

def split_batches(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

all_data    = []
failed      = []
total_batch = (len(TICKERS) + BATCH_SIZE - 1) // BATCH_SIZE

print(f"📥 Downloading {len(TICKERS)} stocks | Period: {DATA_PERIOD} | Batch size: {BATCH_SIZE}\n")

for batch_num, batch in enumerate(split_batches(TICKERS, BATCH_SIZE), 1):
    print(f"🔄 Batch {batch_num}/{total_batch}: {batch}")

    try:
        raw = yf.download(
            tickers=batch,
            period=DATA_PERIOD,
            interval="1d",
            auto_adjust=False,
            group_by="ticker",
            progress=False
        )

        # raw is None when SSL/network blocks the entire batch
        if raw is None or (hasattr(raw, 'empty') and raw.empty):
            print(f"  ⚠️  Batch returned no data — retrying individually")
            batch_to_retry = batch
        else:
            batch_to_retry = []
            for ticker in batch:
                try:
                    df = raw[ticker].copy() if len(batch) > 1 else raw.copy()

                    if df.empty:
                        print(f"  ⚠️  {ticker} — empty, will retry solo")
                        batch_to_retry.append(ticker)
                        continue

                    df["Ticker"]        = ticker
                    df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3
                    df["VWAP_Daily"]    = df["Typical_Price"]

                    price_cols = ["Open", "High", "Low", "Close",
                                  "Adj Close", "Typical_Price", "VWAP_Daily"]
                    for col in price_cols:
                        if col in df.columns:
                            df[col] = df[col].round(4)

                    df.dropna(inplace=True)
                    all_data.append(df)
                    print(f"  ✅ {ticker} — {len(df)} rows")

                except Exception as e:
                    print(f"  ❌ {ticker} — {e}, will retry solo")
                    batch_to_retry.append(ticker)

        # Retry failed tickers one by one
        for ticker in batch_to_retry:
            try:
                df = yf.download(
                    tickers=ticker,
                    period=DATA_PERIOD,
                    interval="1d",
                    auto_adjust=False,
                    progress=False
                )
                if df is None or df.empty:
                    print(f"  ⚠️  {ticker} — empty after solo retry")
                    failed.append(ticker)
                    continue

                df["Ticker"]        = ticker
                df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3
                df["VWAP_Daily"]    = df["Typical_Price"]

                price_cols = ["Open", "High", "Low", "Close",
                              "Adj Close", "Typical_Price", "VWAP_Daily"]
                for col in price_cols:
                    if col in df.columns:
                        df[col] = df[col].round(4)

                df.dropna(inplace=True)
                all_data.append(df)
                print(f"  ✅ {ticker} — {len(df)} rows (solo retry)")
                time.sleep(1)

            except Exception as e:
                print(f"  ❌ {ticker} — {e}")
                failed.append(ticker)

    except Exception as e:
        print(f"  ❌ Batch failed: {e}")
        failed.extend(batch)

    time.sleep(BATCH_DELAY)     # ← reads from config

if all_data:
    combined = pd.concat(all_data)
    combined.reset_index(inplace=True)
    save_to_db(combined, TABLES["ohlcv"], engine)

if failed:
    print(f"\n⚠️  {len(failed)} failed: {failed}")
