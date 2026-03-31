import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import feedparser
import time
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from dotenv import load_dotenv

load_dotenv()
newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))

# Test with 3 different stocks
test_companies = {
    "RELIANCE.NS"  : "Reliance Industries",
    "COFORGE.NS"   : "Coforge IT",          # Was in failed list
    "APLAPOLLO.NS" : "APL Apollo Tubes",    # Was in failed list
}

ET_RSS_FEEDS = {
    "markets": "https://economictimes.indiatimes.com/markets/rss.cms",
    "stocks" : "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
}

def fetch_newsapi(company_name):
    try:
        from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        articles  = newsapi.get_everything(
            q=company_name, language="en",
            from_param=from_date, sort_by="relevancy", page_size=10
        )
        headlines = [a["title"] for a in articles.get("articles", [])
                    if a.get("title")]
        return headlines
    except Exception as e:
        return []

def fetch_et_rss(company_name):
    headlines = []
    for feed_name, url in ET_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                if any(word.lower() in title.lower()
                       for word in company_name.split()):
                    headlines.append(title)
        except Exception:
            continue
    return headlines[:10]

def fetch_gdelt(company_name):
    try:
        query   = company_name.split()[0]
        from_dt = (datetime.now() - timedelta(days=3)
                   ).strftime("%Y%m%d%H%M%S")
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={query}%20India%20stock"
            f"&mode=artlist&maxrecords=10"
            f"&startdatetime={from_dt}"
            f"&format=json"
        )
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data     = response.json()
            articles = data.get("articles", [])
            return [a.get("title", "") for a in articles if a.get("title")]
    except Exception as e:
        pass
    return []

# ── Run diagnostic ────────────────────────────────────────────────────
for ticker, company in test_companies.items():
    print(f"\n{'='*60}")
    print(f"Ticker: {ticker} | Company: {company}")
    print(f"{'='*60}")

    newsapi_h = fetch_newsapi(company)
    print(f"\n📰 NewsAPI     : {len(newsapi_h)} headlines")
    for h in newsapi_h[:3]:
        print(f"   → {h[:80]}")

    et_h = fetch_et_rss(company)
    print(f"\n📰 ET RSS      : {len(et_h)} headlines")
    for h in et_h[:3]:
        print(f"   → {h[:80]}")

    gdelt_h = fetch_gdelt(company)
    print(f"\n📰 GDELT       : {len(gdelt_h)} headlines")
    for h in gdelt_h[:3]:
        print(f"   → {h[:80]}")

    total = list(dict.fromkeys(newsapi_h + et_h + gdelt_h))
    print(f"\n✅ Total unique : {len(total)} headlines")
    time.sleep(1)