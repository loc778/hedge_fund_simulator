# data/sentiment.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
import feedparser
import json
import time
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from dotenv import load_dotenv

from config import TICKERS, TABLES, SENTIMENT, ET_RSS_FEEDS
from data.db import get_engine, save_to_db

load_dotenv()
engine   = get_engine()
newsapi  = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")

# ── Company name map for better news search ───────────────────────────
# Ticker symbols don't work well in news searches
# Company names give much better results
COMPANY_NAMES = {
    "RELIANCE.NS"  : "Reliance Industries",
    "TCS.NS"       : "TCS Tata Consultancy",
    "HDFCBANK.NS"  : "HDFC Bank",
    "ICICIBANK.NS" : "ICICI Bank",
    "INFY.NS"      : "Infosys",
    "HINDUNILVR.NS": "Hindustan Unilever HUL",
    "ITC.NS"       : "ITC Limited",
    "SBIN.NS"      : "State Bank India SBI",
    "BHARTIARTL.NS": "Bharti Airtel",
    "KOTAKBANK.NS" : "Kotak Mahindra Bank",
    "LT.NS"        : "Larsen Toubro",
    "AXISBANK.NS"  : "Axis Bank",
    "ASIANPAINT.NS": "Asian Paints",
    "MARUTI.NS"    : "Maruti Suzuki",
    "SUNPHARMA.NS" : "Sun Pharmaceutical",
    "TITAN.NS"     : "Titan Company",
    "BAJFINANCE.NS": "Bajaj Finance",
    "WIPRO.NS"     : "Wipro",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "HCLTECH.NS"   : "HCL Technologies",
    "NESTLEIND.NS" : "Nestle India",
    "POWERGRID.NS" : "Power Grid India",
    "NTPC.NS"      : "NTPC Limited",
    "ONGC.NS"      : "ONGC Oil Gas",
    "HAL.NS"       : "Hindustan Aeronautics HAL",
    "ADANIENT.NS"  : "Adani Enterprises",
    "ADANIPORTS.NS": "Adani Ports",
    "JSWSTEEL.NS"  : "JSW Steel",
    "TATASTEEL.NS" : "Tata Steel",
    "HINDALCO.NS"  : "Hindalco Industries",
    "COALINDIA.NS" : "Coal India",
    "BAJAJ-AUTO.NS": "Bajaj Auto",
    "EICHERMOT.NS" : "Eicher Motors Royal Enfield",
    "HEROMOTOCO.NS": "Hero MotoCorp",
    "M&M.NS"       : "Mahindra Mahindra",
    "DRREDDY.NS"   : "Dr Reddys Laboratories",
    "CIPLA.NS"     : "Cipla Pharma",
    "DIVISLAB.NS"  : "Divi Laboratories",
    "APOLLOHOSP.NS": "Apollo Hospitals",
    "TECHM.NS"     : "Tech Mahindra",
    "HDFCLIFE.NS"  : "HDFC Life Insurance",
    "SBILIFE.NS"   : "SBI Life Insurance",
    "ICICIPRULI.NS": "ICICI Prudential",
    "BAJAJFINSV.NS": "Bajaj Finserv",
    "BRITANNIA.NS" : "Britannia Industries",
    "DABUR.NS"     : "Dabur India",
    "GODREJCP.NS"  : "Godrej Consumer Products",
    "MARICO.NS"    : "Marico Limited",
    "PIDILITIND.NS": "Pidilite Fevicol",
    "BERGEPAINT.NS": "Berger Paints",
    "HAVELLS.NS"   : "Havells India",
    "VOLTAS.NS"    : "Voltas Limited",
    "DMART.NS"     : "DMart Avenue Supermarts",
    "TRENT.NS"     : "Trent Zara Westside",
    "SIEMENS.NS"   : "Siemens India",
    "NYKAA.NS"     : "Nykaa FSN Ecommerce",
    "PAYTM.NS"     : "Paytm One97 Communications",
    "POLICYBZR.NS" : "PolicyBazaar PB Fintech",
    "INDHOTEL.NS"  : "Indian Hotels Taj",
    "IRCTC.NS"     : "IRCTC Indian Railway",
    "BANDHANBNK.NS": "Bandhan Bank",
    "FEDERALBNK.NS": "Federal Bank",
    "IDFCFIRSTB.NS": "IDFC First Bank",
    "PNB.NS"       : "Punjab National Bank PNB",
    "BANKBARODA.NS": "Bank of Baroda",
    "CANBK.NS"     : "Canara Bank",
    "UNIONBANK.NS" : "Union Bank India",
    "IOC.NS"       : "Indian Oil Corporation",
    "BPCL.NS"      : "Bharat Petroleum BPCL",
    "GAIL.NS"      : "GAIL India Gas",
    "VEDL.NS"      : "Vedanta Limited",
    "NMDC.NS"      : "NMDC Steel Mining",
    "SAIL.NS"      : "SAIL Steel Authority",
    "JINDALSTEL.NS": "Jindal Steel Power",
    "APLAPOLLO.NS" : "APL Apollo Tubes",
    "GRASIM.NS"    : "Grasim Industries",
    "AMBUJACEM.NS" : "Ambuja Cements",
    "ACC.NS"       : "ACC Limited Cement",
    "SHREECEM.NS"  : "Shree Cement",
    "RAMCOCEM.NS"  : "Ramco Cements",
    "OBEROIRLTY.NS": "Oberoi Realty",
    "DLF.NS"       : "DLF Limited",
    "GODREJPROP.NS": "Godrej Properties",
    "PRESTIGE.NS"  : "Prestige Estates",
    "PHOENIXLTD.NS": "Phoenix Mills",
    "MUTHOOTFIN.NS": "Muthoot Finance Gold",
    "CHOLAFIN.NS"  : "Cholamandalam Finance",
    "M&MFIN.NS"    : "Mahindra Finance",
    "MANAPPURAM.NS": "Manappuram Finance Gold",
    "RECLTD.NS"    : "REC Limited Power",
    "PFC.NS"       : "Power Finance Corporation",
    "IRFC.NS"      : "IRFC Indian Railway Finance",
    "NAUKRI.NS"    : "Naukri Info Edge",
    "PERSISTENT.NS": "Persistent Systems",
    "MPHASIS.NS"   : "Mphasis IT",
    "LTIM.NS"      : "LTIMindtree",
    "COFORGE.NS"   : "Coforge IT",
    "TATACOMM.NS"  : "Tata Communications",
    "INDUSTOWER.NS": "Indus Towers",
    "AUROPHARMA.NS": "Aurobindo Pharma",
}

# ── FinBERT via HuggingFace Inference API ─────────────────────────────
def get_finbert_sentiment(headlines):
    """
    Batched FinBERT — sends ALL headlines in ONE API call.
    10x faster than one call per headline.
    Falls back to VADER if HuggingFace unavailable.
    """
    if not headlines:
        return None

    API_URL = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    # Limit to max headlines from config
    batch = headlines[:SENTIMENT["max_headlines_per_stock"]]

    try:
        # Send ALL headlines in ONE API call instead of one per headline
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": batch},
            timeout=30
        )

        if response.status_code == 503:
            print(f"    ⏳ Model warming up, waiting 20s...")
            time.sleep(20)
            response = requests.post(
                API_URL, headers=headers,
                json={"inputs": batch}, timeout=30
            )

        if response.status_code == 200:
            results = response.json()

            # Results is a list of lists — one inner list per headline
            all_scores = []
            for result in results:
                if isinstance(result, list):
                    scores = {item["label"]: item["score"] for item in result}
                    all_scores.append(scores)

            if all_scores:
                avg_positive = sum(s.get("positive", 0) for s in all_scores) / len(all_scores)
                avg_negative = sum(s.get("negative", 0) for s in all_scores) / len(all_scores)
                avg_neutral  = sum(s.get("neutral",  0) for s in all_scores) / len(all_scores)
                composite    = avg_positive - avg_negative

                return {
                    "Sentiment_Score": round(composite,    4),
                    "Positive_Score":  round(avg_positive, 4),
                    "Negative_Score":  round(avg_negative, 4),
                    "Neutral_Score":   round(avg_neutral,  4),
                    "Headlines_Count": len(all_scores)
                }

    except Exception:
        pass

    # ── VADER fallback ────────────────────────────────────────────────
    print(f"    ⚠️  HuggingFace unavailable — using VADER fallback")
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer     = SentimentIntensityAnalyzer()
        vader_scores = [analyzer.polarity_scores(h) for h in batch]

        if not vader_scores:
            return None

        avg_compound = sum(s["compound"] for s in vader_scores) / len(vader_scores)
        avg_positive = sum(s["pos"]      for s in vader_scores) / len(vader_scores)
        avg_negative = sum(s["neg"]      for s in vader_scores) / len(vader_scores)
        avg_neutral  = sum(s["neu"]      for s in vader_scores) / len(vader_scores)

        return {
            "Sentiment_Score": round(avg_compound,  4),
            "Positive_Score":  round(avg_positive,  4),
            "Negative_Score":  round(avg_negative,  4),
            "Neutral_Score":   round(avg_neutral,   4),
            "Headlines_Count": len(vader_scores)
        }

    except Exception as e:
        print(f"    ❌ VADER also failed: {e}")
        return None

# ── Source 1: NewsAPI ─────────────────────────────────────────────────
def fetch_newsapi(company_name, days_back=3):
    """Fetch recent headlines from NewsAPI"""
    try:
        from_date = (datetime.now() - timedelta(days=days_back)
                     ).strftime("%Y-%m-%d")

        articles = newsapi.get_everything(
            q=company_name,
            language="en",
            from_param=from_date,
            sort_by="relevancy",
            page_size=10
        )

        return [a["title"] for a in articles.get("articles", [])
                if a.get("title")]

    except Exception as e:
        return []


# ── Source 2: Economic Times RSS ─────────────────────────────────────
def fetch_et_rss(company_name):
    """
    Economic Times RSS — secondary source.
    Uses multiple feed URLs to maximize coverage.
    """
    headlines = []
    
    # Updated ET RSS feed URLs
    rss_urls = [
        "https://economictimes.indiatimes.com/markets/rss.cms",
        "https://economictimes.indiatimes.com/markets/stocks/news/rss.cms",
        "https://economictimes.indiatimes.com/news/economy/rss.cms",
        "https://economictimes.indiatimes.com/markets/earnings/rss.cms",
        "https://economictimes.indiatimes.com/news/company/corporate-trends/rss.cms",
    ]
    
    search_words = company_name.lower().split()
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                # Match if ANY word from company name appears in headline
                if any(word in title.lower() for word in search_words
                       if len(word) > 3):   # Skip short words like "of", "the"
                    headlines.append(title)
        except Exception:
            continue
    
    return list(dict.fromkeys(headlines))[:10]

# ── Source 3: GDELT ───────────────────────────────────────────────────
def fetch_gdelt(company_name, days_back=3):
    """
    Primary news source — completely free, no rate limits.
    Best India coverage of all three sources.
    Tries multiple query variations for better coverage.
    """
    headlines = []
    
    # Try multiple query variations to maximize coverage
    queries = [
        f"{company_name.split()[0]} India stock",
        f"{company_name.split()[0]} NSE earnings",
        f"{' '.join(company_name.split()[:2])} India",
    ]
    
    for query in queries:
        try:
            query_encoded = query.replace(" ", "+")
            url = (
                f"https://api.gdeltproject.org/api/v2/doc/doc"
                f"?query={query_encoded}"
                f"&mode=artlist&maxrecords=10"
                f"&format=json"
            )
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data     = response.json()
                articles = data.get("articles", [])
                new_headlines = [
                    a.get("title", "") for a in articles
                    if a.get("title")
                ]
                headlines.extend(new_headlines)
                
            time.sleep(0.5)   # Respectful delay between GDELT calls
            
        except Exception:
            continue
    
    # Deduplicate
    return list(dict.fromkeys(headlines))[:15]


# ── Main ──────────────────────────────────────────────────────────────
today    = datetime.now().date()
all_data = []
failed   = []

print(f"📰 Fetching sentiment for {len(TICKERS)} stocks...\n")

for ticker in TICKERS:
    company = COMPANY_NAMES.get(ticker, ticker.replace(".NS", ""))

    try:
        # NEW — GDELT is primary, ET RSS is secondary, NewsAPI is optional
        gdelt_headlines   = fetch_gdelt(company)
        et_headlines      = fetch_et_rss(company)

        # Only use NewsAPI if we have requests remaining
        # Check by trying once — if rate limited, skip entirely
        newsapi_headlines = []
        try:
            from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            articles  = newsapi.get_everything(
                q=company, language="en",
                from_param=from_date,
                sort_by="relevancy", page_size=5
            )
            newsapi_headlines = [a["title"] for a in articles.get("articles", [])
                                if a.get("title")]
        except Exception:
            pass   # Rate limited or unavailable — silently skip

        headlines = list(dict.fromkeys(
            gdelt_headlines + et_headlines + newsapi_headlines
        ))

        # Determine dominant source
        if gdelt_headlines:
            source = "gdelt"
        elif et_headlines:
            source = "et_rss"
        elif newsapi_headlines:
            source = "newsapi"
        else:
            source = "none"
        # Run through FinBERT
        sentiment = get_finbert_sentiment(headlines)

        if not sentiment:
            print(f"  ⚠️  {ticker} — FinBERT returned no scores")
            failed.append(ticker)
            continue

        all_data.append({
            "Date"           : today,
            "Ticker"         : ticker,
            "Sentiment_Score": sentiment["Sentiment_Score"],
            "Positive_Score" : sentiment["Positive_Score"],
            "Negative_Score" : sentiment["Negative_Score"],
            "Neutral_Score"  : sentiment["Neutral_Score"],
            "Headlines_Count": sentiment["Headlines_Count"],
            "Source"         : source
        })

        print(f"  ✅ {ticker} — {sentiment['Headlines_Count']} headlines "
              f"| Score: {sentiment['Sentiment_Score']:+.4f} "
              f"| Source: {source}")

    except Exception as e:
        print(f"  ❌ {ticker} — {e}")
        failed.append(ticker)

    time.sleep(0.3)

# ── Save to MySQL ─────────────────────────────────────────────────────
if all_data:
    df = pd.DataFrame(all_data)
    save_to_db(df, TABLES["sentiment"], engine)

if failed:
    print(f"\n⚠️  {len(failed)} tickers had no sentiment data: {failed}")

print(f"\n✅ Sentiment complete — {len(all_data)} stocks scored for {today}")