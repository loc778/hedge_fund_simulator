import pandas as pd
from nsepython import nse_eq
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import time

load_dotenv()

engine = create_engine(
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

nifty100_tickers = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "TITAN.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "HCLTECH.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "HAL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
    "COALINDIA.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "M&M.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "TECHM.NS",
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
    "LTIM.NS", "COFORGE.NS", "TATACOMM.NS", "INDUSTOWER.NS", "AUROPHARMA.NS"
]

def get_fii_dii(ticker):
    """
    Fetch latest FII and DII holding % using nsepython.
    Returns dict with FII_Holding and DII_Holding or None.
    """
    # Strip .NS for NSE
    symbol = ticker.replace(".NS", "").replace(".BO", "")

    try:
        data = nse_eq(symbol)

        # nsepython returns shareholding under 'shareholdingPatterns'
        patterns = data.get("shareholdingPatterns", {})
        data_list = patterns.get("data", [])

        if not data_list:
            return None

        # Take the most recent quarter (first entry)
        latest = data_list[0]
        holders = latest.get("shareholderDetails", [])

        fii_holding = 0.0
        dii_holding = 0.0

        fii_keywords = ["FPI", "FII", "FOREIGN PORTFOLIO"]
        dii_keywords = ["MUTUAL FUND", "INSURANCE", "DII",
                        "DOMESTIC INSTITUTIONAL"]

        for holder in holders:
            name = holder.get("shareholderType", "").upper()
            pct  = float(holder.get("percentageOfShareHolding", 0) or 0)

            if any(k in name for k in fii_keywords):
                fii_holding += pct
            elif any(k in name for k in dii_keywords):
                dii_holding += pct

        return {
            "FII_Holding": round(fii_holding, 4),
            "DII_Holding": round(dii_holding, 4)
        }

    except Exception as e:
        raise e


# ── Main ──────────────────────────────────────────────────────────────
all_data = []
failed   = []

print(f"📥 Fetching FII/DII data for {len(nifty100_tickers)} stocks...\n")

for ticker in nifty100_tickers:
    try:
        result = get_fii_dii(ticker)

        if result and (result["FII_Holding"] > 0 or result["DII_Holding"] > 0):
            all_data.append({
                "Ticker":      ticker,
                "FII_Holding": result["FII_Holding"],
                "DII_Holding": result["DII_Holding"]
            })
            print(f"  ✅ {ticker} — FII: {result['FII_Holding']}% | DII: {result['DII_Holding']}%")
        else:
            print(f"  ⚠️  {ticker} — no shareholding data")
            failed.append(ticker)

    except Exception as e:
        print(f"  ❌ {ticker} — {e}")
        failed.append(ticker)

    time.sleep(1.5)

# ── Update MySQL ──────────────────────────────────────────────────────
if all_data:
    print(f"\n💾 Updating MySQL with FII/DII data...")

    updated = 0
    with engine.connect() as conn:
        for row in all_data:
            result = conn.execute(
                "UPDATE nifty100_fundamentals "
                "SET FII_Holding = %s, DII_Holding = %s "
                "WHERE Ticker = %s",
                (row["FII_Holding"], row["DII_Holding"], row["Ticker"])
            )
            updated += result.rowcount
        conn.commit()

    print(f"✅ Updated {updated} rows across {len(all_data)} stocks")

else:
    print("❌ No data fetched at all")

if failed:
    print(f"\n⚠️  {len(failed)} tickers failed: {failed}")