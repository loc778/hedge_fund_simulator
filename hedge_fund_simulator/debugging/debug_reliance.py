import yfinance as yf
import pandas as pd

stock = yf.Ticker("RELIANCE.NS")

income   = stock.quarterly_financials
balance  = stock.quarterly_balance_sheet
cashflow = stock.quarterly_cashflow

print("=" * 60)
print(f"INCOME columns (dates): {list(income.columns)}")
print(f"INCOME rows: {len(income.columns)} quarters")

print("\n" + "=" * 60)
print(f"BALANCE columns (dates): {list(balance.columns)}")
print(f"BALANCE rows: {len(balance.columns)} quarters")

print("\n" + "=" * 60)
print(f"CASHFLOW columns (dates): {list(cashflow.columns)}")
print(f"CASHFLOW rows: {len(cashflow.columns)} quarters")

print("\n" + "=" * 60)
print("BALANCE — Total Assets row:")
if "Total Assets" in balance.index:
    print(balance.loc["Total Assets"])
else:
    print("Total Assets NOT found in balance sheet index")

print("\n" + "=" * 60)
print("INCOME — Total Revenue row:")
if "Total Revenue" in income.index:
    print(income.loc["Total Revenue"])
else:
    print("Total Revenue NOT found in income index")