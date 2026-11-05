"""Keyword Planner tools using the Google Ads KeywordPlanIdeaService."""

import os
from .shared_utils import get_google_ads_client, get_customer_id, micros_to_currency


def generate_keyword_ideas(
    seed_keywords: list[str],
    url: str = "",
    language_id: str = "1000",
    geo_target_id: str = "2840",
    num_results: int = 20,
) -> dict:
    """Generate keyword ideas from seed keywords using Google Ads Keyword Planner.
    Returns keyword suggestions with search volume, competition, and bid estimates.

    Args:
        seed_keywords: List of seed keywords to generate ideas from.
        url: Optional landing page URL for content-based suggestions.
        language_id: Language criterion ID (default '1000' for English).
        geo_target_id: Geographic target ID (default '2840' for United States).
        num_results: Number of keyword ideas to return (default 20).

    Returns:
        dict: status and list of keyword ideas with metrics.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        request.language = f"languageConstants/{language_id}"
        request.geo_target_constants.append(f"geoTargetConstants/{geo_target_id}")
        request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

        if seed_keywords:
            request.keyword_seed.keywords.extend(seed_keywords)
        if url:
            request.url_seed.url = url

        response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

        ideas = []
        for idx, result in enumerate(response.results):
            if idx >= num_results:
                break
            metrics = result.keyword_idea_metrics
            ideas.append({
                "keyword": result.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": metrics.competition.name if metrics.competition else "UNKNOWN",
                "competition_index": metrics.competition_index,
                "low_top_of_page_bid": micros_to_currency(metrics.low_top_of_page_bid_micros),
                "high_top_of_page_bid": micros_to_currency(metrics.high_top_of_page_bid_micros),
            })

        return {"status": "success", "seed_keywords": seed_keywords, "ideas": ideas}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_keyword_forecasts(
    keywords: list[str],
    monthly_budget: float = 1000.0,
    geo_target_id: str = "2840",
    language_id: str = "1000",
) -> dict:
    """Get forecast metrics for a set of keywords at a given budget level.
    Returns projected clicks, impressions, cost, and CPC.

    Args:
        keywords: List of keywords to forecast.
        monthly_budget: Monthly budget in USD for the forecast.
        geo_target_id: Geographic target ID (default '2840' for US).
        language_id: Language ID (default '1000' for English).

    Returns:
        dict: status and forecast metrics per keyword.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordForecastMetricsRequest")
        request.customer_id = customer_id

        campaign = request.campaign
        campaign.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        campaign.geo_targets.append(
            client.get_type("CriterionBidModifier")(
                geo_target_constant=f"geoTargetConstants/{geo_target_id}"
            )
        )
        campaign.language_constants.append(f"languageConstants/{language_id}")

        for kw in keywords:
            biddable_keyword = campaign.ad_groups.add().biddable_keywords.add()
            biddable_keyword.keyword.text = kw
            biddable_keyword.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            biddable_keyword.max_cpc_bid_micros = int(monthly_budget / len(keywords) / 30 * 1_000_000)

        response = keyword_plan_idea_service.generate_keyword_forecast_metrics(request=request)

        forecasts = []
        for idx, forecast in enumerate(response.keyword_forecasts):
            metrics = forecast.keyword_forecast
            forecasts.append({
                "keyword": keywords[idx] if idx < len(keywords) else f"keyword_{idx}",
                "clicks": round(metrics.clicks, 1) if metrics.clicks else 0,
                "impressions": round(metrics.impressions, 1) if metrics.impressions else 0,
                "cost": micros_to_currency(int(metrics.cost_micros)) if metrics.cost_micros else 0,
                "ctr": round(metrics.ctr * 100, 2) if metrics.ctr else 0,
                "avg_cpc": micros_to_currency(int(metrics.average_cpc_micros)) if metrics.average_cpc_micros else 0,
            })

        overall = response.campaign_forecast_metrics
        summary = {
            "total_clicks": round(overall.clicks, 1) if overall.clicks else 0,
            "total_impressions": round(overall.impressions, 1) if overall.impressions else 0,
            "total_cost": micros_to_currency(int(overall.cost_micros)) if overall.cost_micros else 0,
            "avg_cpc": micros_to_currency(int(overall.average_cpc_micros)) if overall.average_cpc_micros else 0,
        }

        return {"status": "success", "monthly_budget": monthly_budget, "summary": summary, "keyword_forecasts": forecasts}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_search_volume(
    keywords: list[str],
    geo_target_id: str = "2840",
    language_id: str = "1000",
) -> dict:
    """Get historical search volume and metrics for specific keywords.

    Args:
        keywords: List of keywords to get volume for.
        geo_target_id: Geographic target ID (default '2840' for US).
        language_id: Language ID (default '1000' for English).

    Returns:
        dict: status and search volume data per keyword.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        request.customer_id = customer_id
        request.keywords.extend(keywords)
        request.language = f"languageConstants/{language_id}"
        request.geo_target_constants.append(f"geoTargetConstants/{geo_target_id}")
        request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

        response = keyword_plan_idea_service.generate_keyword_historical_metrics(request=request)

        results = []
        for result in response.results:
            metrics = result.keyword_metrics
            monthly_volumes = []
            if metrics.monthly_search_volumes:
                for vol in metrics.monthly_search_volumes:
                    monthly_volumes.append({
                        "year": vol.year,
                        "month": vol.month.name,
                        "searches": vol.monthly_searches,
                    })

            results.append({
                "keyword": result.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": metrics.competition.name if metrics.competition else "UNKNOWN",
                "monthly_search_volumes": monthly_volumes[-12:],
            })

        return {"status": "success", "keywords": results}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
