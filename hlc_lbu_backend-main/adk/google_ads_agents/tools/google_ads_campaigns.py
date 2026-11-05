"""Campaign management tools using the Google Ads API."""

import os
from .shared_utils import get_google_ads_client, get_customer_id, currency_to_micros


def create_campaign(
    name: str,
    daily_budget: float,
    bidding_strategy: str = "MANUAL_CPC",
    bidding_target_value: float = 0.0,
    network: str = "SEARCH",
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """Create a new Google Ads Search campaign with a budget and bidding strategy.

    Args:
        name: Campaign name.
        daily_budget: Daily budget in USD.
        bidding_strategy: One of MANUAL_CPC, MAXIMIZE_CONVERSIONS, TARGET_CPA, MAXIMIZE_CONVERSION_VALUE, TARGET_ROAS.
            NOTE: MANUAL_CPC is recommended for new accounts without conversion tracking.
            MAXIMIZE_CONVERSIONS, TARGET_CPA, TARGET_ROAS require conversion tracking to be enabled in the account.
        bidding_target_value: Target CPA in USD or Target ROAS multiplier (if applicable).
        network: SEARCH or SEARCH_WITH_DISPLAY_SELECT.
        start_date: Start date as YYYY-MM-DD (optional, defaults to today).
        end_date: End date as YYYY-MM-DD (optional).

    Returns:
        dict: status and the created campaign resource name and ID.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        campaign_service = client.get_service("CampaignService")
        campaign_budget_service = client.get_service("CampaignBudgetService")

        # Create budget first
        budget_operation = client.get_type("CampaignBudgetOperation")
        budget = budget_operation.create
        budget.name = f"Budget for {name}"
        budget.amount_micros = currency_to_micros(daily_budget)
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget.explicitly_shared = False  # Not a shared budget

        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_operation]
        )
        budget_resource = budget_response.results[0].resource_name

        # Create campaign
        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = name
        campaign.campaign_budget = budget_resource
        campaign.status = client.enums.CampaignStatusEnum.PAUSED  # Start paused for review

        # Set network
        if network == "SEARCH":
            campaign.network_settings.target_search_network = True
            campaign.network_settings.target_content_network = False
        else:
            campaign.network_settings.target_search_network = True
            campaign.network_settings.target_content_network = True

        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH

        # Set bidding strategy
        if bidding_strategy == "MAXIMIZE_CONVERSIONS":
            campaign.maximize_conversions.target_cpa_micros = 0
        elif bidding_strategy == "TARGET_CPA":
            campaign.maximize_conversions.target_cpa_micros = currency_to_micros(bidding_target_value)
        elif bidding_strategy == "MANUAL_CPC":
            campaign.manual_cpc.enhanced_cpc_enabled = False
        elif bidding_strategy == "MAXIMIZE_CONVERSION_VALUE":
            campaign.maximize_conversion_value.target_roas = 0
        elif bidding_strategy == "TARGET_ROAS":
            campaign.maximize_conversion_value.target_roas = bidding_target_value

        # Required field in Google Ads API v23+ (enum, not boolean)
        campaign.contains_eu_political_advertising = (
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        )

        # Set dates if provided
        if start_date:
            campaign.start_date = start_date.replace("-", "")
        if end_date:
            campaign.end_date = end_date.replace("-", "")

        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_operation]
        )
        resource_name = response.results[0].resource_name
        campaign_id = resource_name.split("/")[-1]

        return {
            "status": "success",
            "campaign_resource_name": resource_name,
            "campaign_id": campaign_id,
            "budget_resource_name": budget_resource,
            "name": name,
            "note": "Campaign created in PAUSED status. Enable when ready.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def create_ad_group(
    campaign_id: str,
    name: str,
    cpc_bid: float = 2.0,
) -> dict:
    """Create an ad group within a campaign.

    Args:
        campaign_id: The campaign ID to add the ad group to.
        name: Ad group name.
        cpc_bid: Default max CPC bid in USD.

    Returns:
        dict: status and the created ad group resource name and ID.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ad_group_service = client.get_service("AdGroupService")

        operation = client.get_type("AdGroupOperation")
        ad_group = operation.create
        ad_group.name = name
        ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = currency_to_micros(cpc_bid)

        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[operation]
        )
        resource_name = response.results[0].resource_name
        ad_group_id = resource_name.split("/")[-1]

        return {
            "status": "success",
            "ad_group_resource_name": resource_name,
            "ad_group_id": ad_group_id,
            "name": name,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def add_keywords(
    ad_group_id: str,
    keywords: list[dict],
) -> dict:
    """Add keywords to an ad group.

    Args:
        ad_group_id: The ad group ID to add keywords to.
        keywords: List of dicts with 'text' and 'match_type' (BROAD, PHRASE, EXACT).

    Returns:
        dict: status and list of created keyword resource names.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")

        match_type_map = {
            "BROAD": client.enums.KeywordMatchTypeEnum.BROAD,
            "PHRASE": client.enums.KeywordMatchTypeEnum.PHRASE,
            "EXACT": client.enums.KeywordMatchTypeEnum.EXACT,
        }

        operations = []
        for kw in keywords:
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = kw["text"]
            criterion.keyword.match_type = match_type_map.get(
                kw.get("match_type", "BROAD").upper(),
                client.enums.KeywordMatchTypeEnum.BROAD,
            )
            operations.append(operation)

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=operations
        )

        created = [r.resource_name for r in response.results]
        return {
            "status": "success",
            "keywords_added": len(created),
            "resource_names": created,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def create_responsive_search_ad(
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    final_url: str,
) -> dict:
    """Create a Responsive Search Ad (RSA) in an ad group.

    Args:
        ad_group_id: The ad group ID to create the ad in.
        headlines: List of up to 15 headline strings (max 30 chars each).
        descriptions: List of up to 4 description strings (max 90 chars each).
        final_url: The landing page URL.

    Returns:
        dict: status and the created ad resource name.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        ad_group_ad_service = client.get_service("AdGroupAdService")

        operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        ad_group_ad.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        ad = ad_group_ad.ad
        ad.final_urls.append(final_url)

        for headline in headlines[:15]:
            asset = client.get_type("AdTextAsset")
            asset.text = headline[:30]
            ad.responsive_search_ad.headlines.append(asset)

        for description in descriptions[:4]:
            asset = client.get_type("AdTextAsset")
            asset.text = description[:90]
            ad.responsive_search_ad.descriptions.append(asset)

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id, operations=[operation]
        )
        resource_name = response.results[0].resource_name

        return {
            "status": "success",
            "ad_resource_name": resource_name,
            "headlines_count": min(len(headlines), 15),
            "descriptions_count": min(len(descriptions), 4),
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def add_negative_keywords(
    campaign_id: str,
    keywords: list[str],
) -> dict:
    """Add negative keywords to a campaign to prevent ads showing for irrelevant searches.

    Args:
        campaign_id: The campaign ID to add negatives to.
        keywords: List of negative keyword strings.

    Returns:
        dict: status and count of negatives added.
    """
    customer_id = get_customer_id()
    if not customer_id:
        return {"status": "error", "error_message": "GOOGLE_ADS_CUSTOMER_ID not set."}

    try:
        client = get_google_ads_client()
        campaign_criterion_service = client.get_service("CampaignCriterionService")

        operations = []
        for kw in keywords:
            operation = client.get_type("CampaignCriterionOperation")
            criterion = operation.create
            criterion.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
            criterion.negative = True
            criterion.keyword.text = kw
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            operations.append(operation)

        response = campaign_criterion_service.mutate_campaign_criteria(
            customer_id=customer_id, operations=operations
        )

        return {
            "status": "success",
            "negatives_added": len(response.results),
            "keywords": keywords,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
