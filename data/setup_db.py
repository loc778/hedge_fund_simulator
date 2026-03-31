# data/setup_db.py
# ═══════════════════════════════════════════════════════════
# ONE-TIME DATABASE SETUP SCRIPT
# Run once on any new machine to create all tables.
# 
# HOW TO ADD A NEW TABLE LATER:
# Simply add a new entry to the TABLES dictionary below.
# Follow the exact same format as existing tables.
# IF NOT EXISTS means running this again never breaks anything.
# ═══════════════════════════════════════════════════════════

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import get_engine
from sqlalchemy import text

engine = get_engine()

# ═══════════════════════════════════════════════════════════
# TABLE DEFINITIONS
# To add a new table: copy any existing block, paste at
# the bottom of this dictionary, change the name and columns.
# To edit a table: modify the columns here, then run
# ALTER TABLE in MySQL Workbench for existing machines.
# ═══════════════════════════════════════════════════════════

TABLES = {

    # ── Layer 1: Price & Volume ───────────────────────────────────────
    # Source: yfinance (testing) → Bhavcopy (production)
    # Script: data/ingestion.py
    "nifty100_ohlcv": """
        CREATE TABLE IF NOT EXISTS nifty100_ohlcv (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            Date            DATETIME        NOT NULL,
            Ticker          VARCHAR(20)     NOT NULL,
            Open            DECIMAL(10,4),
            High            DECIMAL(10,4),
            Low             DECIMAL(10,4),
            `Close`         DECIMAL(10,4),
            `Adj Close`     DECIMAL(10,4),
            Volume          BIGINT,
            Typical_Price   DECIMAL(10,4),
            VWAP_Daily      DECIMAL(10,4),
            UNIQUE KEY unique_ticker_date (Ticker, Date)
        )
    """,

    # ── Layer 4: Technical Indicators ────────────────────────────────
    # Source: calculated from nifty100_ohlcv
    # Script: data/indicators.py
    "nifty100_indicators": """
        CREATE TABLE IF NOT EXISTS nifty100_indicators (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            Date            DATETIME        NOT NULL,
            Ticker          VARCHAR(20)     NOT NULL,
            SMA_20          DECIMAL(10,4),
            SMA_50          DECIMAL(10,4),
            SMA_200         DECIMAL(10,4),
            EMA_9           DECIMAL(10,4),
            EMA_21          DECIMAL(10,4),
            MACD            DECIMAL(10,4),
            MACD_Signal     DECIMAL(10,4),
            MACD_Hist       DECIMAL(10,4),
            RSI_14          DECIMAL(10,4),
            BB_Upper        DECIMAL(10,4),
            BB_Middle       DECIMAL(10,4),
            BB_Lower        DECIMAL(10,4),
            ATR_14          DECIMAL(10,4),
            Stoch_K         DECIMAL(10,4),
            Stoch_D         DECIMAL(10,4),
            ADX_14          DECIMAL(10,4),
            OBV             DECIMAL(20,4),
            VWAP_Dev        DECIMAL(10,4),
            UNIQUE KEY unique_ticker_date (Ticker, Date)
        )
    """,

    # ── Layer 2: Fundamental Data ─────────────────────────────────────
    # Source: yfinance (testing) → Screener.in (production)
    # Script: data/fundamentals.py
    # FII_Holding and DII_Holding: populated later via Zerodha Kite API
    "nifty100_fundamentals": """
        CREATE TABLE IF NOT EXISTS nifty100_fundamentals (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            Ticker              VARCHAR(20)     NOT NULL,
            Period              DATE            NOT NULL,
            Revenue             BIGINT,
            Gross_Profit        BIGINT,
            EBITDA              BIGINT,
            Net_Income          BIGINT,
            EPS_Basic           DECIMAL(10,4),
            EPS_Diluted         DECIMAL(10,4),
            Total_Assets        BIGINT,
            Total_Liabilities   BIGINT,
            Total_Equity        BIGINT,
            Cash                BIGINT,
            Total_Debt          BIGINT,
            Book_Value_PS       DECIMAL(10,4),
            Operating_CF        BIGINT,
            Capex               BIGINT,
            Free_Cash_Flow      BIGINT,
            Debt_to_Equity      DECIMAL(10,4),
            FCF_Yield           DECIMAL(10,4),
            ROCE                DECIMAL(10,4),
            PE_Ratio            DECIMAL(10,4),
            PB_Ratio            DECIMAL(10,4),
            EV_EBITDA           DECIMAL(10,4),
            Dividend_Yield      DECIMAL(10,4),
            ROE                 DECIMAL(10,4),
            ROA                 DECIMAL(10,4),
            FII_Holding         DECIMAL(10,4),   -- populated later via Zerodha
            DII_Holding         DECIMAL(10,4),   -- populated later via Zerodha
            UNIQUE KEY unique_ticker_period (Ticker, Period)
        )
    """,

    # ── Layer 3A: Macro & Economic Indicators ─────────────────────────
    # Source: yfinance (VIX, USDINR, Oil, Gold) + FRED API (macro)
    # Script: data/macro.py
    "macro_indicators": """
        CREATE TABLE IF NOT EXISTS macro_indicators (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            Date                DATE        NOT NULL UNIQUE,
            India_VIX           DECIMAL(10,4),
            USDINR              DECIMAL(10,4),
            Crude_Oil           DECIMAL(10,4),
            Gold                DECIMAL(10,4),
            CPI_India           DECIMAL(10,4),
            GDP_India           DECIMAL(20,4),
            Fed_Funds_Rate      DECIMAL(10,4),
            US_CPI              DECIMAL(10,4),
            US_10Y_Bond         DECIMAL(10,4)
        )
    """,

    # ── Layer 3B: Sentiment Data ──────────────────────────────────────
    # Source: GDELT + NewsAPI + ET RSS → FinBERT via HuggingFace API
    # Script: data/sentiment.py
    "nifty100_sentiment": """
        CREATE TABLE IF NOT EXISTS nifty100_sentiment (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            Date            DATE            NOT NULL,
            Ticker          VARCHAR(20)     NOT NULL,
            Sentiment_Score DECIMAL(10,4),
            Positive_Score  DECIMAL(10,4),
            Negative_Score  DECIMAL(10,4),
            Neutral_Score   DECIMAL(10,4),
            Headlines_Count INT,
            Source          VARCHAR(50),
            UNIQUE KEY unique_ticker_date (Ticker, Date)
        )
    """,

    # ── ADD NEW TABLES BELOW THIS LINE ────────────────────────────────
    # ── Feature Engineering: Unified ML Training Dataset ─────────────
    # Source: combined from all 5 data layers
    # Script: data/features.py
    # One row per stock per day — direct input to ML models
    # Target_Return_21d = 21-day forward return (regression target)
    # Target_Direction  = 1 if price up, 0 if down (classification target)
    "features_master": """
        CREATE TABLE IF NOT EXISTS features_master (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            Date                DATE            NOT NULL,
            Ticker              VARCHAR(20)     NOT NULL,

            -- From Layer 1 (OHLCV)
            Open                DECIMAL(10,4),
            High                DECIMAL(10,4),
            Low                 DECIMAL(10,4),
            Close               DECIMAL(10,4),
            Adj_Close           DECIMAL(10,4),
            Volume              BIGINT,
            VWAP_Daily          DECIMAL(10,4),

            -- Price derived features
            Return_1d           DECIMAL(10,4),
            Return_5d           DECIMAL(10,4),
            Return_21d          DECIMAL(10,4),
            Volatility_20d      DECIMAL(10,4),
            High_52w_Ratio      DECIMAL(10,4),
            Low_52w_Ratio       DECIMAL(10,4),
            Volume_Ratio_20d    DECIMAL(10,4),

            -- From Layer 4 (Technical Indicators)
            SMA_20              DECIMAL(10,4),
            SMA_50              DECIMAL(10,4),
            SMA_200             DECIMAL(10,4),
            EMA_9               DECIMAL(10,4),
            EMA_21              DECIMAL(10,4),
            MACD                DECIMAL(10,4),
            MACD_Signal         DECIMAL(10,4),
            MACD_Hist           DECIMAL(10,4),
            RSI_14              DECIMAL(10,4),
            BB_Upper            DECIMAL(10,4),
            BB_Middle           DECIMAL(10,4),
            BB_Lower            DECIMAL(10,4),
            BB_Width            DECIMAL(10,4),
            ATR_14              DECIMAL(10,4),
            Stoch_K             DECIMAL(10,4),
            Stoch_D             DECIMAL(10,4),
            ADX_14              DECIMAL(10,4),
            OBV                 DECIMAL(20,4),
            VWAP_Dev            DECIMAL(10,4),

            -- From Layer 2 (Fundamentals — forward filled quarterly)
            PE_Ratio            DECIMAL(10,4),
            PB_Ratio            DECIMAL(10,4),
            EV_EBITDA           DECIMAL(10,4),
            ROE                 DECIMAL(10,4),
            ROA                 DECIMAL(10,4),
            ROCE                DECIMAL(10,4),
            Debt_to_Equity      DECIMAL(10,4),
            FCF_Yield           DECIMAL(10,4),
            Dividend_Yield      DECIMAL(10,4),
            EPS_Basic           DECIMAL(10,4),

            -- From Layer 3B (Sentiment — forward filled daily)
            Sentiment_Score     DECIMAL(10,4),
            Positive_Score      DECIMAL(10,4),
            Negative_Score      DECIMAL(10,4),

            -- From Layer 3A (Macro — daily)
            India_VIX           DECIMAL(10,4),
            USDINR              DECIMAL(10,4),
            Crude_Oil           DECIMAL(10,4),
            Gold                DECIMAL(10,4),
            CPI_India           DECIMAL(10,4),
            GDP_India           DECIMAL(20,4),
            Fed_Funds_Rate      DECIMAL(10,4),
            US_CPI              DECIMAL(10,4),
            US_10Y_Bond         DECIMAL(10,4),

            -- Target variables (what the ML model predicts)
            Target_Return_21d   DECIMAL(10,4),
            Target_Direction    TINYINT,

            UNIQUE KEY unique_ticker_date (Ticker, Date)
        )
    """,
    # Copy the format above exactly.
    # Example structure:
    #
    # "your_table_name": """
    #     CREATE TABLE IF NOT EXISTS your_table_name (
    #         id      INT AUTO_INCREMENT PRIMARY KEY,
    #         Date    DATE NOT NULL,
    #         Ticker  VARCHAR(20) NOT NULL,
    #         Col1    DECIMAL(10,4),
    #         Col2    BIGINT,
    #         UNIQUE KEY unique_ticker_date (Ticker, Date)
    #     )
    # """,

}

# ═══════════════════════════════════════════════════════════
# DO NOT EDIT BELOW THIS LINE
# ═══════════════════════════════════════════════════════════

print("🔧 Setting up hedge_fund_db tables...\n")

created = []
skipped = []
failed  = []

with engine.connect() as conn:
    for table_name, ddl in TABLES.items():
        try:
            # Check if table already exists
            exists = conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema = DATABASE() "
                f"AND table_name = '{table_name}'"
            )).scalar()

            conn.execute(text(ddl))
            conn.commit()

            if exists:
                skipped.append(table_name)
                print(f"  ⏭️  {table_name} — already exists, skipped")
            else:
                created.append(table_name)
                print(f"  ✅ {table_name} — created")

        except Exception as e:
            failed.append(table_name)
            print(f"  ❌ {table_name} — {e}")

# ── Summary ───────────────────────────────────────────────────────────
print(f"""
{'='*50}
Setup Complete
{'='*50}
  Created : {len(created)} tables  → {created if created else 'none'}
  Skipped : {len(skipped)} tables  → already existed
  Failed  : {len(failed)}  tables  → {failed if failed else 'none'}
{'='*50}
""")

if not failed:
    print("Run scripts in this order:")
    print("  1. python data/ingestion.py")
    print("  2. python data/indicators.py")
    print("  3. python data/fundamentals.py")
    print("  4. python data/macro.py")
    print("  5. python data/sentiment.py")
else:
    print("⚠️  Fix the failed tables before running data scripts")