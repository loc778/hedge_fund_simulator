import requests
import feedparser
from newsapi import NewsApiClient
from dotenv import load_dotenv
import os

load_dotenv()

# ── Test 1: NewsAPI raw call ──────────────────────────────────────────
print("=" * 50)
print("TEST 1: NewsAPI")
print("=" * 50)
try:
    newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))
    result  = newsapi.get_everything(
        q="Reliance Industries India stock",
        language="en",
        page_size=3
    )
    print(f"Status: {result.get('status')}")
    print(f"Total results: {result.get('totalResults')}")
    print(f"Articles returned: {len(result.get('articles', []))}")
    for a in result.get("articles", [])[:2]:
        print(f"  → {a['title'][:80]}")
except Exception as e:
    print(f"ERROR: {e}")

# ── Test 2: ET RSS raw call ───────────────────────────────────────────
print("\n" + "=" * 50)
print("TEST 2: Economic Times RSS")
print("=" * 50)
try:
    feed = feedparser.parse(
        "https://economictimes.indiatimes.com/markets/stocks/rss.cms"
    )
    print(f"Feed status: {feed.get('status', 'unknown')}")
    print(f"Entries found: {len(feed.entries)}")
    for e in feed.entries[:3]:
        print(f"  → {e.get('title', 'no title')[:80]}")
except Exception as e:
    print(f"ERROR: {e}")

# ── Test 3: GDELT raw call ────────────────────────────────────────────
print("\n" + "=" * 50)
print("TEST 3: GDELT")
print("=" * 50)
try:
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        "?query=Reliance+India+stock"
        "&mode=artlist&maxrecords=5&format=json"
    )
    response = requests.get(url, timeout=15)
    print(f"Status code: {response.status_code}")
    data     = response.json()
    articles = data.get("articles", [])
    print(f"Articles found: {len(articles)}")
    for a in articles[:2]:
        print(f"  → {a.get('title', 'no title')[:80]}")
except Exception as e:
    print(f"ERROR: {e}")

# ── Test 4: Check NewsAPI key and plan ───────────────────────────────
print("\n" + "=" * 50)
print("TEST 4: NewsAPI Key Status")
print("=" * 50)
try:
    sources = newsapi.get_sources(language="en")
    print(f"API key valid: {sources.get('status') == 'ok'}")
    print(f"Sources available: {len(sources.get('sources', []))}")
except Exception as e:
    print(f"ERROR: {e}")