import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# Check yfinance date range
df = yf.download("INR=X", period="6mo", interval="1d", progress=False)
print("yfinance index type:", type(df.index))
print("yfinance date range:", df.index.min(), "→", df.index.max())
print("yfinance index sample:", df.index[:3].tolist())

print()

# Check FRED date range
series = fred.get_series("FEDFUNDS", observation_start="2023-01-01")
print("FRED index type:", type(series.index))
print("FRED date range:", series.index.min(), "→", series.index.max())
print("FRED index sample:", series.index[:3].tolist())

print()

# Try the reindex manually
print("Attempting reindex...")
test = series.reindex(df.index, method="ffill")
print("Result nulls:", test.isna().sum(), "out of", len(test))
print("Result sample:", test.tail(5).tolist())