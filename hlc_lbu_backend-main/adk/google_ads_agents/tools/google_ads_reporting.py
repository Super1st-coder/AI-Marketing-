"""Reporting tools using Google Ads GAQL queries."""

from .shared_utils import get_google_ads_client, get_customer_id, micros_to_currency


def get_campaign_performance(
    campaign_ids: list[str],
    date_range: str = "LAST_7_DAYS",
) -> dict:
    """Get performance metrics for specified campaigns.

    Args:
        campaign_ids: List of campaign IDs to report on.
        date_range: Date range - LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH, or custom YYYY-MM-DD,YYYY-MM-DD.

    Returns:
        dict: status and per-campaign performance metrics.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        ids_filter = ", ".join(f"'{cid}'" for cid in campaign_ids) if campaign_ids else ""

        if "," in date_range and "-" in date_range:
            start, end = date_range.split(",")
            date_clause = f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'"
        else:
            date_clause = f"segments.date DURING {date_range}"

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_per_conversion
            FROM campaign
            WHERE {date_clause}
            {"AND campaign.id IN (" + ids_filter + ")" if ids_filter else ""}
            AND campaign.advertising_channel_type = 'SEARCH'
            ORDER BY metrics.cost_micros DESC
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        campaigns = []
        for batch in response:
            for row in batch.results:
                campaigns.append({
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "status": row.campaign.status.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": micros_to_currency(row.metrics.cost_micros),
                    "conversions": round(row.metrics.conversions, 1),
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc": micros_to_currency(row.metrics.average_cpc),
                    "cpa": micros_to_currency(row.metrics.cost_per_conversion) if row.metrics.conversions > 0 else 0,
                })

        return {"status": "success", "date_range": date_range, "campaigns": campaigns}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_keyword_performance(
    campaign_id: str,
    date_range: str = "LAST_7_DAYS",
    limit: int = 50,
) -> dict:
    """Get keyword-level performance metrics for a campaign.

    Args:
        campaign_id: Campaign ID to report on.
        date_range: LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, etc.
        limit: Max number of keywords to return (default 50).

    Returns:
        dict: status and per-keyword performance metrics including quality score.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        if "," in date_range and "-" in date_range:
            start, end = date_range.split(",")
            date_clause = f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'"
        else:
            date_clause = f"segments.date DURING {date_range}"

        query = f"""
            SELECT
                ad_group.name,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.quality_info.quality_score,
                ad_group_criterion.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_per_conversion
            FROM keyword_view
            WHERE campaign.id = '{campaign_id}'
            AND {date_clause}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        keywords = []
        for batch in response:
            for row in batch.results:
                keywords.append({
                    "ad_group": row.ad_group.name,
                    "keyword": row.ad_group_criterion.keyword.text,
                    "match_type": row.ad_group_criterion.keyword.match_type.name,
                    "quality_score": row.ad_group_criterion.quality_info.quality_score,
                    "status": row.ad_group_criterion.status.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": micros_to_currency(row.metrics.cost_micros),
                    "conversions": round(row.metrics.conversions, 1),
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc": micros_to_currency(row.metrics.average_cpc),
                    "cpa": micros_to_currency(row.metrics.cost_per_conversion) if row.metrics.conversions > 0 else 0,
                })

        return {"status": "success", "campaign_id": campaign_id, "keywords": keywords}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_search_term_report(
    campaign_id: str,
    date_range: str = "LAST_7_DAYS",
    limit: int = 50,
) -> dict:
    """Get actual search terms that triggered ads, with their performance.
    Critical for finding negative keywords and new keyword opportunities.

    Args:
        campaign_id: Campaign ID to report on.
        date_range: LAST_7_DAYS, LAST_30_DAYS, etc.
        limit: Max number of search terms to return.

    Returns:
        dict: status and search term metrics.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        if "," in date_range and "-" in date_range:
            start, end = date_range.split(",")
            date_clause = f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'"
        else:
            date_clause = f"segments.date DURING {date_range}"

        query = f"""
            SELECT
                search_term_view.search_term,
                search_term_view.status,
                ad_group.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM search_term_view
            WHERE campaign.id = '{campaign_id}'
            AND {date_clause}
            ORDER BY metrics.impressions DESC
            LIMIT {limit}
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        search_terms = []
        for batch in response:
            for row in batch.results:
                search_terms.append({
                    "search_term": row.search_term_view.search_term,
                    "status": row.search_term_view.status.name,
                    "ad_group": row.ad_group.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": micros_to_currency(row.metrics.cost_micros),
                    "conversions": round(row.metrics.conversions, 1),
                    "ctr": round(row.metrics.ctr * 100, 2),
                })

        return {"status": "success", "campaign_id": campaign_id, "search_terms": search_terms}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_ad_performance(
    ad_group_id: str,
    date_range: str = "LAST_7_DAYS",
) -> dict:
    """Get ad-level performance metrics for an ad group.
    Useful for evaluating RSA performance and deciding which ads to refresh.

    Args:
        ad_group_id: Ad group ID to report on.
        date_range: LAST_7_DAYS, LAST_30_DAYS, etc.

    Returns:
        dict: status and per-ad metrics.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        if "," in date_range and "-" in date_range:
            start, end = date_range.split(",")
            date_clause = f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'"
        else:
            date_clause = f"segments.date DURING {date_range}"

        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.status,
                ad_group_ad.ad.responsive_search_ad.headlines,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group_ad
            WHERE ad_group.id = '{ad_group_id}'
            AND {date_clause}
            ORDER BY metrics.impressions DESC
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        ads = []
        for batch in response:
            for row in batch.results:
                ads.append({
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_type": row.ad_group_ad.ad.type_.name,
                    "status": row.ad_group_ad.status.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": micros_to_currency(row.metrics.cost_micros),
                    "conversions": round(row.metrics.conversions, 1),
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc": micros_to_currency(row.metrics.average_cpc),
                })

        return {"status": "success", "ad_group_id": ad_group_id, "ads": ads}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
