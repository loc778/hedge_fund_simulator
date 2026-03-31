import yfinance as yf

# Testing alternate formats for both stocks
test_symbols = [
    "ZOMATO.NS",
    "ZOMATO.BO",        # BSE format
    "543320.NS",        # NSE code for Zomato
    "TATAMOTORS.NS",
    "TATAMOTORS.BO",    # BSE format
    "TATAMOTOR.NS",     # Sometimes shortened
]

for symbol in test_symbols:
    df = yf.download(symbol, period="5d", progress=False)
    if not df.empty:
        print(f"✅ {symbol} WORKS — {len(df)} rows")
    else:
        print(f"❌ {symbol} failed")