"""Trend detection tools using SerpAPI Google Trends and NewsAPI."""

import os
import requests


def get_google_trends(keyword: str, timeframe: str = "today 3-m") -> dict:
    """Get Google Trends data for a keyword showing interest over time and related queries.

    Args:
        keyword: The keyword to check trends for.
        timeframe: Time range - 'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y'.

    Returns:
        dict: status with interest over time data and related queries.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"status": "error", "error_message": "SERPAPI_KEY not set in .env file."}

    try:
        # Use requests with timeout instead of serpapi library (which has no timeout)
        params = {
            "engine": "google_trends",
            "q": keyword,
            "data_type": "TIMESERIES",
            "date": timeframe,
            "api_key": api_key,
        }
        resp = requests.get(
            "https://serpapi.com/search.json", params=params, timeout=15
        )
        resp.raise_for_status()
        results = resp.json()

        interest_over_time = []
        for point in results.get("interest_over_time", {}).get("timeline_data", []):
            interest_over_time.append({
                "date": point.get("date", ""),
                "value": point.get("values", [{}])[0].get("extracted_value", 0) if point.get("values") else 0,
            })

        # Get related queries in a second call (also with timeout)
        params["data_type"] = "RELATED_QUERIES"
        resp2 = requests.get(
            "https://serpapi.com/search.json", params=params, timeout=15
        )
        resp2.raise_for_status()
        related = resp2.json()

        rising_queries = []
        top_queries = []
        for item in related.get("related_queries", {}).get("rising", []):
            rising_queries.append({
                "query": item.get("query", ""),
                "value": item.get("extracted_value", ""),
            })
        for item in related.get("related_queries", {}).get("top", []):
            top_queries.append({
                "query": item.get("query", ""),
                "value": item.get("extracted_value", 0),
            })

        return {
            "status": "success",
            "keyword": keyword,
            "interest_over_time": interest_over_time[-12:],
            "rising_queries": rising_queries[:5],
            "top_related_queries": top_queries[:5],
        }
    except requests.exceptions.Timeout:
        return {"status": "error", "error_message": f"Timeout fetching trends for '{keyword}'. Try again later."}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_industry_news(topic: str, num_articles: int = 5) -> dict:
    """Fetch the latest news articles for a topic. Useful for finding trending
    content ideas and staying on top of industry developments.

    Args:
        topic: Topic or keyword to search news for.
        num_articles: Number of articles to return (default 5, max 5).

    Returns:
        dict: status and list of articles with title, source, date, and URL.
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return {"status": "error", "error_message": "NEWSAPI_KEY not set in .env file."}

    # Cap at 5 to keep payloads small
    num_articles = min(num_articles, 5)

    try:
        # Use requests directly with timeout instead of newsapi library
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": topic,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": num_articles,
                "apiKey": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        articles = [
            {
                "title": a.get("title"),
                "source": a.get("source", {}).get("name"),
                "published_at": a.get("publishedAt"),
                "description": (a.get("description") or "")[:150],
            }
            for a in data.get("articles", [])[:num_articles]
        ]
        return {"status": "success", "topic": topic, "articles": articles}
    except requests.exceptions.Timeout:
        return {"status": "error", "error_message": f"Timeout fetching news for '{topic}'. Try again later."}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
