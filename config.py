# config.py
# ═══════════════════════════════════════════════════════════
# CENTRAL CONFIGURATION — change values here to scale up
# ═══════════════════════════════════════════════════════════

# ── Data Range ───────────────────────────────────────────────────────
# Change "6mo" to "2y", "5y", "10y" when scaling up
DATA_PERIOD = "2y"

# For explicit date ranges (uncomment when scaling to 10 years)
# DATA_START = "2015-01-01"
# DATA_END   = "2025-12-31"

# ── Batch Settings ───────────────────────────────────────────────────
# How many stocks to download at once from yfinance
# Keep at 10 for reliability. Can try 20 when on faster internet.
BATCH_SIZE = 10

# Pause between batches (seconds) — increase if getting rate limited
BATCH_DELAY = 2

# Pause between individual stock fetches (fundamentals)
STOCK_DELAY = 1

MODEL_VERSION = "20260405"   # add this near the top

# ── Database ─────────────────────────────────────────────────────────
DB_NAME = "hedge_fund_db"

# Table names — change here if you ever rename them
TABLES = {
    "ohlcv"        : "nifty100_ohlcv",
    "indicators"   : "nifty100_indicators",
    "fundamentals" : "nifty100_fundamentals",
    "macro"        : "macro_indicators",
    "sentiment"    : "nifty100_sentiment",
    "features"     : "features_master",       # ← new
}

# ── Stock Universe ───────────────────────────────────────────────────
# TIER 1: Current 98 stocks (Nifty 100 minus 2 unavailable)
# To scale: add Nifty Next 50, Midcap 150 etc. to this list
# The rest of the code automatically handles however many you add

TICKERS = [
    # ── Nifty 50 Core ────────────────────────────────────────────
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "TITAN.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "HCLTECH.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "HAL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
    "COALINDIA.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "M&M.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "TECHM.NS",

    # ── Nifty Next 50 ────────────────────────────────────────────
    "HDFCLIFE.NS", "SBILIFE.NS", "ICICIPRULI.NS", "BAJAJFINSV.NS", "BRITANNIA.NS",
    "DABUR.NS", "GODREJCP.NS", "MARICO.NS", "PIDILITIND.NS", "BERGEPAINT.NS",
    "HAVELLS.NS", "VOLTAS.NS", "DMART.NS", "TRENT.NS", "SIEMENS.NS",
    "NYKAA.NS", "PAYTM.NS", "POLICYBZR.NS", "INDHOTEL.NS", "IRCTC.NS",
    "BANDHANBNK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS", "PNB.NS", "BANKBARODA.NS",
    "CANBK.NS", "UNIONBANK.NS", "IOC.NS", "BPCL.NS", "GAIL.NS",
    "VEDL.NS", "NMDC.NS", "SAIL.NS", "JINDALSTEL.NS", "APLAPOLLO.NS",
    "GRASIM.NS", "AMBUJACEM.NS", "ACC.NS", "SHREECEM.NS", "RAMCOCEM.NS",
    "OBEROIRLTY.NS", "DLF.NS", "GODREJPROP.NS", "PRESTIGE.NS", "PHOENIXLTD.NS",
    "MUTHOOTFIN.NS", "CHOLAFIN.NS", "M&MFIN.NS", "MANAPPURAM.NS", "RECLTD.NS",
    "PFC.NS", "IRFC.NS", "NAUKRI.NS", "PERSISTENT.NS", "MPHASIS.NS",
    "LTIM.NS", "COFORGE.NS", "TATACOMM.NS", "INDUSTOWER.NS", "AUROPHARMA.NS",

    # ── Add Nifty Midcap 150 here when scaling to 500 ────────────
    # "ABCAPITAL.NS", "AAVAS.NS", ... (add more here)
]

# ── Sector Map (for sector-level analysis in ML models) ──────────────
# Add new stocks here too when scaling
SECTOR_MAP = {
    "IT":          ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS",
                    "LTIM.NS", "MPHASIS.NS", "COFORGE.NS", "PERSISTENT.NS"],
    "Banking":     ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS",
                    "AXISBANK.NS", "BANDHANBNK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS",
                    "PNB.NS", "BANKBARODA.NS", "CANBK.NS", "UNIONBANK.NS"],
    "Finance":     ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS",
                    "ICICIPRULI.NS", "MUTHOOTFIN.NS", "CHOLAFIN.NS", "M&MFIN.NS",
                    "MANAPPURAM.NS", "RECLTD.NS", "PFC.NS", "IRFC.NS"],
    "Auto":        ["MARUTI.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS",
                    "M&M.NS"],
    "Pharma":      ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
                    "AUROPHARMA.NS"],
    "Energy":      ["RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS", "GAIL.NS",
                    "COALINDIA.NS", "POWERGRID.NS", "NTPC.NS"],
    "Metals":      ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS",
                    "NMDC.NS", "SAIL.NS", "JINDALSTEL.NS"],
    "FMCG":        ["HINDUNILVR.NS", "ITC.NS", "BRITANNIA.NS", "DABUR.NS",
                    "GODREJCP.NS", "MARICO.NS"],
    "Infra":       ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS", "HAL.NS",
                    "SIEMENS.NS", "INDUSTOWER.NS"],
    "RealEstate":  ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS",
                    "PHOENIXLTD.NS"],
    "Consumer":    ["ASIANPAINT.NS", "TITAN.NS", "NESTLEIND.NS", "PIDILITIND.NS",
                    "BERGEPAINT.NS", "HAVELLS.NS", "VOLTAS.NS", "DMART.NS",
                    "TRENT.NS", "INDHOTEL.NS", "IRCTC.NS"],
    "Cement":      ["ULTRACEMCO.NS", "SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS",
                    "RAMCOCEM.NS", "GRASIM.NS"],
    "Telecom":     ["BHARTIARTL.NS", "TATACOMM.NS"],
    "NewAge":      ["NYKAA.NS", "PAYTM.NS", "POLICYBZR.NS", "ZOMATO.NS"],
}

# ── Macro Data Config ─────────────────────────────────────────────────
# yfinance symbols for daily market data
MACRO_YFINANCE = {
    "India_VIX"  : "^INDIAVIX",   # India Volatility Index
    "USDINR"     : "INR=X",        # USD to INR exchange rate
    "Crude_Oil"  : "CL=F",         # Crude oil futures
    "Gold"       : "GC=F",         # Gold futures
}

# FRED series IDs for Indian and US macro data
# Full list at https://fred.stlouisfed.org
MACRO_FRED = {
    "CPI_India"      : "INDCPIALLMINMEI",  # India CPI monthly
    "GDP_India"      : "NGDPRNSAXDCINQ",   # India Real GDP quarterly (IMF)
    "Fed_Funds_Rate" : "FEDFUNDS",         # US Federal Funds Rate monthly
    "US_CPI"         : "CPIAUCSL",         # US CPI monthly
    "US_10Y_Bond"    : "DGS10",            # US 10-Year Treasury yield daily
                                            # Replaces IIP — affects Indian
                                            # capital flows and INR directly
}

# Add macro table to TABLES dict
TABLES["macro"] = "macro_indicators"

# ── Future Data Sources (activate when scaling) ───────────────────────
# NSE Bhavcopy base URL — replace ingestion.py with bhavcopy_ingestion.py
BHAVCOPY_URL = "https://nsearchives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{date}bhav.csv.zip"

# Screener.in base URL — replace fundamentals.py with screener_fundamentals.py
SCREENER_URL = "https://www.screener.in/company/{symbol}/consolidated/"

# Data source flag — change to "bhavcopy" when scaling up
# All ingestion scripts will check this and route accordingly
DATA_SOURCE = "yfinance"   # options: "yfinance", "bhavcopy", "zerodha"

# ── Sentiment Data Config ─────────────────────────────────────────────
SENTIMENT = {
    # News sources — ranked by priority
    "sources": ["gdelt", "newsapi", "et_rss"],

    # How many headlines per stock per day to process
    "max_headlines_per_stock": 10,

    # Sentiment model — huggingface API (doesn't use your RAM)
    "model": "ProsusAI/finbert",
    "hf_api": True,             # True = use HF API, False = run locally

    # Lookback window for sentiment averaging
    "lookback_days": 3,         # Average sentiment over last 3 days
                                # smooths out noise from single headlines
}

# ET RSS feeds per sector (free and legal)
ET_RSS_FEEDS = {
    "markets"    : "https://economictimes.indiatimes.com/markets/rss.cms",
    "stocks"     : "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "economy"    : "https://economictimes.indiatimes.com/news/economy/rss.cms",
    "results"    : "https://economictimes.indiatimes.com/markets/earnings/rss.cms",
}

TABLES["sentiment"] = "nifty100_sentiment"

