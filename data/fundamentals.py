# data/fundamentals.py
# ⚠️  SCALE-UP NOTE:
# This script uses yfinance — suitable for testing only.
# When scaling to 500 stocks / 10 years:
# Replace with data/bhavcopy_ingestion.py (Layer 1)
# Replace with data/screener_fundamentals.py (Layer 2)
# Config flag: set DATA_SOURCE = "bhavcopy" in config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
import time

from config import TICKERS, STOCK_DELAY, TABLES
from data.db import get_engine, save_to_db

engine = get_engine()

# ── Helper Functions ──────────────────────────────────────────────────

def safe_col(df, col):
    """Return column if exists, else None series. Handles missing fields
    gracefully across different stock types (banks vs manufacturing etc.)"""
    if df is not None and col in df.columns:
        return df[col]
    return pd.Series([None] * len(df), index=df.index) if df is not None else None

def safe_divide(a, b):
    """Divide two series safely — returns None where division fails
    or where denominator is zero. Prevents inf values entering the DB."""
    try:
        result = a / b
        return result.replace([float("inf"), float("-inf")], None)
    except Exception:
        return pd.Series([None] * len(a), index=a.index)

def normalize_index(raw_df):
    """
    Normalize financial statement dates to month-end.
    Fixes yfinance quirk where income statement dates (Sep-29)
    and balance sheet dates (Sep-30) don't align for the same quarter.
    Without this, joins produce NaN-filled rows.
    """
    if raw_df is None or raw_df.empty:
        return None
    df = raw_df.T.copy()
    df.index = pd.to_datetime(df.index)
    df.index = df.index + pd.offsets.MonthEnd(0)   # Sep-29 → Sep-30
    df = df[~df.index.duplicated(keep="first")]
    df.index.name = "Period"
    return df

def fetch_fundamentals(ticker):
    """
    Fetch and process all fundamental data for one ticker.
    Returns a clean DataFrame or raises an exception.
    Structured as a standalone function so it can be parallelized
    later when scaling to 500 stocks.
    """
    stock    = yf.Ticker(ticker)
    income   = normalize_index(stock.quarterly_financials)
    balance  = normalize_index(stock.quarterly_balance_sheet)
    cashflow = normalize_index(stock.quarterly_cashflow)

    if income is None and balance is None:
        raise ValueError("no financial data available")

    # ── Income Statement ──────────────────────────────────────────────
    inc_index = income.index if income is not None else balance.index
    inc = pd.DataFrame(index=inc_index)
    inc["Revenue"]      = safe_col(income, "Total Revenue")
    inc["Gross_Profit"] = safe_col(income, "Gross Profit")
    inc["EBITDA"]       = safe_col(income, "EBITDA")
    inc["Net_Income"]   = safe_col(income, "Net Income")
    inc["EPS_Basic"]    = safe_col(income, "Basic EPS")
    inc["EPS_Diluted"]  = safe_col(income, "Diluted EPS")

    # ── Balance Sheet ─────────────────────────────────────────────────
    bal_index = balance.index if balance is not None else income.index
    bal = pd.DataFrame(index=bal_index)
    bal["Total_Assets"]      = safe_col(balance, "Total Assets")
    bal["Total_Liabilities"] = safe_col(balance,
                                "Total Liabilities Net Minority Interest")
    bal["Total_Equity"]      = safe_col(balance, "Stockholders Equity")
    bal["Cash"]              = safe_col(balance, "Cash And Cash Equivalents")
    bal["Total_Debt"]        = safe_col(balance, "Total Debt")
    bal["Book_Value_PS"]     = safe_col(balance, "Tangible Book Value")
    bal["Current_Liab"]      = safe_col(balance, "Current Liabilities")

    # ── Cash Flow ─────────────────────────────────────────────────────
    cf_index = cashflow.index if cashflow is not None else income.index
    cf = pd.DataFrame(index=cf_index)
    cf["Operating_CF"]   = safe_col(cashflow, "Operating Cash Flow")
    cf["Capex"]          = safe_col(cashflow, "Capital Expenditure")
    cf["Free_Cash_Flow"] = safe_col(cashflow, "Free Cash Flow")

    # ── Merge — inner join keeps only fully matched quarters ──────────
    if cashflow is not None and not cashflow.empty:
        df = inc.join(bal, how="inner").join(cf, how="inner")
    else:
        df = inc.join(bal, how="inner")
        # Add cashflow columns as None if cashflow was empty
        for col in ["Operating_CF", "Capex", "Free_Cash_Flow"]:
            df[col] = None

    if df.empty:
        raise ValueError("no overlapping quarters between statements")

    df["Ticker"] = ticker

    # ── Calculated Metrics ────────────────────────────────────────────
    df["Debt_to_Equity"] = safe_divide(
        df["Total_Debt"], df["Total_Equity"]
    ).round(4)

    df["FCF_Yield"] = safe_divide(
        df["Free_Cash_Flow"], df["Total_Assets"]
    ).round(4)

    capital_employed = df["Total_Assets"] - df["Current_Liab"]
    df["ROCE"] = safe_divide(
        df["Net_Income"], capital_employed
    ).round(4)

    df.drop(columns=["Current_Liab"], inplace=True, errors="ignore")

    # ── Valuation Ratios (current snapshot) ───────────────────────────
    info = stock.info
    def safe_round(key):
        val = info.get(key)
        try:
            return round(float(val), 4) if val else None
        except Exception:
            return None

    df["PE_Ratio"]       = safe_round("trailingPE")
    df["PB_Ratio"]       = safe_round("priceToBook")
    df["EV_EBITDA"]      = safe_round("enterpriseToEbitda")
    df["Dividend_Yield"] = safe_round("dividendYield")
    df["ROE"]            = safe_round("returnOnEquity")
    df["ROA"]            = safe_round("returnOnAssets")

    # ── Clean and type-cast ───────────────────────────────────────────
    df.reset_index(inplace=True)
    df["Period"] = pd.to_datetime(df["Period"]).dt.date

    bigint_cols = ["Revenue", "Gross_Profit", "EBITDA", "Net_Income",
                   "Total_Assets", "Total_Liabilities", "Total_Equity",
                   "Cash", "Total_Debt", "Operating_CF", "Capex",
                   "Free_Cash_Flow"]
    for col in bigint_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    decimal_cols = ["EPS_Basic", "EPS_Diluted", "Book_Value_PS",
                    "Debt_to_Equity", "FCF_Yield", "ROCE",
                    "PE_Ratio", "PB_Ratio", "EV_EBITDA",
                    "Dividend_Yield", "ROE", "ROA"]
    for col in decimal_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(4)

    # Enforce column order to match DB schema exactly
    col_order = [
        "Ticker", "Period",
        "Revenue", "Gross_Profit", "EBITDA", "Net_Income",
        "EPS_Basic", "EPS_Diluted",
        "Total_Assets", "Total_Liabilities", "Total_Equity",
        "Cash", "Total_Debt", "Book_Value_PS",
        "Operating_CF", "Capex", "Free_Cash_Flow",
        "Debt_to_Equity", "FCF_Yield", "ROCE",
        "PE_Ratio", "PB_Ratio", "EV_EBITDA",
        "Dividend_Yield", "ROE", "ROA"
    ]
    df = df[[c for c in col_order if c in df.columns]]

    return df


# ── Main ──────────────────────────────────────────────────────────────
all_data = []
failed   = []

# Use TICKERS from config — automatically scales with whatever you add
print(f"📥 Fetching fundamentals for {len(TICKERS)} stocks...\n")

for ticker in TICKERS:
    try:
        df = fetch_fundamentals(ticker)
        all_data.append(df)
        assets_ok = df["Total_Assets"].notna().sum()
        print(f"  ✅ {ticker} — {len(df)} quarters | Assets: {assets_ok}/{len(df)}")

    except Exception as e:
        print(f"  ❌ {ticker} — {e}")
        failed.append(ticker)

    time.sleep(STOCK_DELAY)     # ← reads from config

if all_data:
    combined = pd.concat(all_data, ignore_index=True)
    save_to_db(combined, TABLES["fundamentals"], engine)

if failed:
    print(f"\n⚠️  {len(failed)} failed: {failed}")