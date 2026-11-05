"""Optimization tools for adjusting bids, budgets, and applying recommendations."""

from .shared_utils import get_google_ads_client, get_customer_id, currency_to_micros, micros_to_currency


def get_recommendations(
    campaign_id: str,
) -> dict:
    """Get Google Ads optimization recommendations for a campaign.

    Args:
        campaign_id: Campaign ID to get recommendations for.

    Returns:
        dict: status and list of recommendations with type, impact, and details.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                recommendation.resource_name,
                recommendation.type,
                recommendation.impact.base_metrics.impressions,
                recommendation.impact.base_metrics.clicks,
                recommendation.impact.base_metrics.cost_micros,
                recommendation.impact.base_metrics.conversions,
                recommendation.impact.potential_metrics.impressions,
                recommendation.impact.potential_metrics.clicks,
                recommendation.impact.potential_metrics.cost_micros,
                recommendation.impact.potential_metrics.conversions
            FROM recommendation
            WHERE recommendation.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
            AND recommendation.dismissed = FALSE
        """

        response = ga_service.search_stream(customer_id=customer_id, query=query)

        recommendations = []
        for batch in response:
            for row in batch.results:
                rec = row.recommendation
                base = rec.impact.base_metrics
                potential = rec.impact.potential_metrics
                recommendations.append({
                    "resource_name": rec.resource_name,
                    "type": rec.type_.name,
                    "current_impressions": base.impressions,
                    "potential_impressions": potential.impressions,
                    "current_clicks": base.clicks,
                    "potential_clicks": potential.clicks,
                    "current_cost": micros_to_currency(base.cost_micros),
                    "potential_cost": micros_to_currency(potential.cost_micros),
                    "current_conversions": round(base.conversions, 1),
                    "potential_conversions": round(potential.conversions, 1),
                })

        return {"status": "success", "campaign_id": campaign_id, "recommendations": recommendations}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def apply_recommendation(
    recommendation_resource_name: str,
) -> dict:
    """Apply a Google Ads recommendation.

    Args:
        recommendation_resource_name: The full resource name of the recommendation to apply.

    Returns:
        dict: status and confirmation.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        recommendation_service = client.get_service("RecommendationService")

        operation = client.get_type("ApplyRecommendationOperation")
        operation.resource_name = recommendation_resource_name

        response = recommendation_service.apply_recommendation(
            customer_id=customer_id, operations=[operation]
        )

        return {
            "status": "success",
            "applied_resource": response.results[0].resource_name,
            "message": "Recommendation applied successfully.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def update_keyword_bid(
    ad_group_id: str,
    criterion_id: str,
    new_cpc_bid: float,
) -> dict:
    """Update the CPC bid for a specific keyword.

    Args:
        ad_group_id: The ad group ID containing the keyword.
        criterion_id: The criterion (keyword) ID to update.
        new_cpc_bid: New max CPC bid in USD.

    Returns:
        dict: status and confirmation with old and new bid.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        service = client.get_service("AdGroupCriterionService")

        resource_name = f"customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"

        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = resource_name
        criterion.cpc_bid_micros = currency_to_micros(new_cpc_bid)

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("cpc_bid_micros")
        operation.update_mask.CopyFrom(field_mask)

        response = service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=[operation]
        )

        return {
            "status": "success",
            "resource_name": response.results[0].resource_name,
            "new_cpc_bid": new_cpc_bid,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def update_campaign_budget(
    campaign_budget_resource_name: str,
    new_daily_budget: float,
) -> dict:
    """Update the daily budget for a campaign.

    Args:
        campaign_budget_resource_name: Full resource name of the campaign budget.
        new_daily_budget: New daily budget in USD.

    Returns:
        dict: status and confirmation.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        service = client.get_service("CampaignBudgetService")

        operation = client.get_type("CampaignBudgetOperation")
        budget = operation.update
        budget.resource_name = campaign_budget_resource_name
        budget.amount_micros = currency_to_micros(new_daily_budget)

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        operation.update_mask.CopyFrom(field_mask)

        response = service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[operation]
        )

        return {
            "status": "success",
            "resource_name": response.results[0].resource_name,
            "new_daily_budget": new_daily_budget,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def pause_keyword(
    ad_group_id: str,
    criterion_id: str,
) -> dict:
    """Pause a keyword to stop it from triggering ads.

    Args:
        ad_group_id: The ad group ID containing the keyword.
        criterion_id: The criterion (keyword) ID to pause.

    Returns:
        dict: status and confirmation.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        service = client.get_service("AdGroupCriterionService")

        resource_name = f"customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"

        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = resource_name
        criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)

        response = service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=[operation]
        )

        return {
            "status": "success",
            "resource_name": response.results[0].resource_name,
            "message": "Keyword paused successfully.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def update_bidding_strategy(
    campaign_id: str,
    strategy_type: str,
    target_value: float = 0.0,
) -> dict:
    """Update the bidding strategy for a campaign.

    Args:
        campaign_id: Campaign ID to update.
        strategy_type: One of TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, MAXIMIZE_CONVERSION_VALUE, MANUAL_CPC.
        target_value: Target CPA in USD or Target ROAS multiplier.

    Returns:
        dict: status and confirmation.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        service = client.get_service("CampaignService")

        resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"

        operation = client.get_type("CampaignOperation")
        campaign = operation.update
        campaign.resource_name = resource_name

        field_mask = client.get_type("FieldMask")

        if strategy_type == "TARGET_CPA":
            campaign.maximize_conversions.target_cpa_micros = currency_to_micros(target_value)
            field_mask.paths.append("maximize_conversions")
        elif strategy_type == "MAXIMIZE_CONVERSIONS":
            campaign.maximize_conversions.target_cpa_micros = 0
            field_mask.paths.append("maximize_conversions")
        elif strategy_type == "TARGET_ROAS":
            campaign.maximize_conversion_value.target_roas = target_value
            field_mask.paths.append("maximize_conversion_value")
        elif strategy_type == "MAXIMIZE_CONVERSION_VALUE":
            campaign.maximize_conversion_value.target_roas = 0
            field_mask.paths.append("maximize_conversion_value")
        elif strategy_type == "MANUAL_CPC":
            campaign.manual_cpc.enhanced_cpc_enabled = False
            field_mask.paths.append("manual_cpc")

        operation.update_mask.CopyFrom(field_mask)

        response = service.mutate_campaigns(
            customer_id=customer_id, operations=[operation]
        )

        return {
            "status": "success",
            "resource_name": response.results[0].resource_name,
            "new_strategy": strategy_type,
            "target_value": target_value,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
