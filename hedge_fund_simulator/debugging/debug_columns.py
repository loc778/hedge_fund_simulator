import yfinance as yf

# Test on one reliable stock
stock = yf.Ticker("TCS.NS")

print("=" * 60)
print("INCOME STATEMENT COLUMNS:")
print("=" * 60)
print(list(stock.quarterly_financials.index))

print("\n" + "=" * 60)
print("BALANCE SHEET COLUMNS:")
print("=" * 60)
print(list(stock.quarterly_balance_sheet.index))

print("\n" + "=" * 60)
print("CASH FLOW COLUMNS:")
print("=" * 60)
print(list(stock.quarterly_cashflow.index))

print("\n" + "=" * 60)
print("INFO KEYS (valuation):")
print("=" * 60)
info = stock.info
valuation_keys = ["trailingPE", "priceToBook", "enterpriseToEbitda",
                  "dividendYield", "returnOnEquity", "returnOnAssets",
                  "trailingEps", "forwardPE"]
for key in valuation_keys:
    print(f"  {key}: {info.get(key)}")