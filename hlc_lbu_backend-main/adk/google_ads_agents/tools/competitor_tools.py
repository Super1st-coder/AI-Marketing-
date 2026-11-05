"""Competitor research tools using SerpAPI and Google Ads Auction Insights."""

import os
import requests
from .shared_utils import get_google_ads_client, get_customer_id


def analyze_competitor_ads(query: str, num_results: int = 5) -> dict:
    """Search Google and extract competitor ads (paid results) for a query.
    Shows what competitors are bidding on and their ad copy.

    Args:
        query: Search query to analyze competitor ads for.
        num_results: Number of competitor ads to return.

    Returns:
        dict: status and list of competitor ads with headlines, descriptions, and display URLs.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"status": "error", "error_message": "SERPAPI_KEY not set in .env file."}

    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={
                "q": query,
                "api_key": api_key,
                "num": 10,
                "hl": "en",
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()

        ads = []
        for ad in results.get("ads", [])[:num_results]:
            ads.append({
                "position": ad.get("block_position", "unknown"),
                "title": ad.get("title", ""),
                "description": (ad.get("description", ""))[:200],
                "displayed_link": ad.get("displayed_link", ""),
                "sitelinks": [s.get("title", "") for s in ad.get("sitelinks", [])][:3],
            })

        return {"status": "success", "query": query, "competitor_ads": ads}
    except requests.exceptions.Timeout:
        return {"status": "error", "error_message": f"Timeout analyzing ads for '{query}'. Try again later."}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_auction_insights(campaign_id: str) -> dict:
    """Get auction insights showing how you compare to competitors for a campaign.
    Shows impression share, overlap rate, and outranking share.

    Args:
        campaign_id: Campaign ID to get auction insights for.

    Returns:
        dict: status and competitor metrics (impression share, overlap rate, etc.).
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                auction_insight.display_domain,
                metrics.auction_insight_search_impression_share,
                metrics.auction_insight_search_overlap_rate,
                metrics.auction_insight_search_outranking_share,
                metrics.auction_insight_search_position_above_rate,
                metrics.auction_insight_search_top_impression_percentage
            FROM auction_insight
            WHERE campaign.id = '{campaign_id}'
            AND segments.date DURING LAST_30_DAYS
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        competitors = []
        for batch in response:
            for row in batch.results:
                competitors.append({
                    "domain": row.auction_insight.display_domain,
                    "impression_share": round(row.metrics.auction_insight_search_impression_share * 100, 1),
                    "overlap_rate": round(row.metrics.auction_insight_search_overlap_rate * 100, 1),
                    "outranking_share": round(row.metrics.auction_insight_search_outranking_share * 100, 1),
                    "position_above_rate": round(row.metrics.auction_insight_search_position_above_rate * 100, 1),
                    "top_impression_pct": round(row.metrics.auction_insight_search_top_impression_percentage * 100, 1),
                })

        return {"status": "success", "campaign_id": campaign_id, "competitors": competitors}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def competitor_landing_pages(query: str, num_results: int = 5) -> dict:
    """Get top organic search results for a query to understand competitor positioning.
    Useful for analyzing how competitors position themselves.

    Args:
        query: Search query to analyze organic results for.
        num_results: Number of results to return.

    Returns:
        dict: status and list of competitor pages with title, URL, and snippet.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"status": "error", "error_message": "SERPAPI_KEY not set in .env file."}

    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={
                "q": query,
                "api_key": api_key,
                "num": num_results,
                "hl": "en",
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()

        pages = []
        for result in results.get("organic_results", [])[:num_results]:
            pages.append({
                "position": result.get("position"),
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": (result.get("snippet", ""))[:200],
            })

        return {"status": "success", "query": query, "landing_pages": pages}
    except requests.exceptions.Timeout:
        return {"status": "error", "error_message": f"Timeout fetching landing pages for '{query}'. Try again later."}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
