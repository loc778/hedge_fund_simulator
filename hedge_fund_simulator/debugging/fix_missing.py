import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import time

load_dotenv()

engine = create_engine(
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)

missing = ["ZOMATO.NS", "TATAMOTORS.NS"]

for ticker in missing:
    time.sleep(3)
    df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=False, progress=False)

    if df.empty:
        print(f"❌ {ticker} still failed")
        continue

    df["Ticker"] = ticker
    df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP_Daily"] = df["Typical_Price"]
    df.dropna(inplace=True)
    df.reset_index(inplace=True)

    # Round to 4 decimal places
    price_cols = ["Open", "High", "Low", "Close", "Adj Close", "Typical_Price", "VWAP_Daily"]
    for col in price_cols:
        if col in df.columns:
            df[col] = df[col].round(4)

    df.to_sql("nifty100_ohlcv", con=engine, if_exists="append", index=False)
    print(f"✅ {ticker} — {len(df)} rows added to OHLCV")