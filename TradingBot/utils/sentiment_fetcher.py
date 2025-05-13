import feedparser
from models.modello_sett import SentimentModel

RSS_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.forexlive.com/feed/"
]

SYMBOL_KEYWORDS = {
    "EURUSD": ["eur", "euro", "usd", "dollar", "ecb", "fed"],
    "USDJPY": ["yen", "jpy", "boj", "usd", "fed", "bank of japan"],
    "GOLD": ["gold"]
}

def fetch_sentiment_for(symbol: str, max_headlines: int = 10) -> float:
    model = SentimentModel()
    all_scores = []
    keywords = SYMBOL_KEYWORDS.get(symbol, [])
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_headlines]:
                headline = entry.get("title", "")
                if any(k in headline.lower() for k in keywords):
                    score = model.analyze(headline)
                    all_scores.append(score)
        except Exception as e:
            print(f"[SentimentFetcher] Error parsing {feed_url}: {e}")

    if not all_scores:
        return 0.0

    avg_score = round(sum(all_scores) / len(all_scores), 3)
    print(f"[SentimentFetcher] Avg sentiment for {symbol}: {avg_score}")
    return avg_score
