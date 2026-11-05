"""Tools for creating and managing Google Ads experiments (A/B tests)."""

import os
from .shared_utils import get_google_ads_client, get_customer_id


def create_campaign_draft(base_campaign_id: str, draft_name: str) -> dict:
    """Create a campaign draft for A/B testing based on an existing campaign.

    Args:
        base_campaign_id: The ID of the base campaign to create a draft from.
        draft_name: A descriptive name for the draft.

    Returns:
        dict: status and draft resource name if successful.
    """
    try:
        client = get_google_ads_client()
        customer_id = get_customer_id()
        campaign_draft_service = client.get_service("CampaignDraftService")
        campaign_service = client.get_service("CampaignService")

        campaign_resource = campaign_service.campaign_path(customer_id, base_campaign_id)

        operation = client.get_type("CampaignDraftOperation")
        draft = operation.create
        draft.base_campaign = campaign_resource
        draft.name = draft_name

        response = campaign_draft_service.mutate_campaign_drafts(
            customer_id=customer_id,
            operations=[operation],
        )
        draft_resource = response.results[0].resource_name
        return {
            "status": "success",
            "draft_resource_name": draft_resource,
            "message": f"Campaign draft '{draft_name}' created from campaign {base_campaign_id}",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def create_experiment(draft_resource_name: str, experiment_name: str, traffic_split_percent: int = 50) -> dict:
    """Create an experiment from a campaign draft to run an A/B test.

    Args:
        draft_resource_name: Resource name of the campaign draft.
        experiment_name: A descriptive name for the experiment.
        traffic_split_percent: Percentage of traffic for the experiment arm (default 50).

    Returns:
        dict: status and experiment resource name if successful.
    """
    try:
        client = get_google_ads_client()
        customer_id = get_customer_id()
        experiment_service = client.get_service("ExperimentService")

        operation = client.get_type("ExperimentOperation")
        experiment = operation.create
        experiment.name = experiment_name
        experiment.description = f"A/B test: {experiment_name}"
        experiment.type_ = client.enums.ExperimentTypeEnum.SEARCH_CUSTOM
        experiment.status = client.enums.ExperimentStatusEnum.SETUP

        # Add experiment arm for the draft
        arm = client.get_type("ExperimentArm")
        arm.name = "Experiment Arm"
        arm.campaign_draft = draft_resource_name
        arm.traffic_share = traffic_split_percent * 100  # micros

        response = experiment_service.mutate_experiments(
            customer_id=customer_id,
            operations=[operation],
        )
        experiment_resource = response.results[0].resource_name
        return {
            "status": "success",
            "experiment_resource_name": experiment_resource,
            "message": f"Experiment '{experiment_name}' created with {traffic_split_percent}% traffic split",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_experiment_results(experiment_resource_name: str) -> dict:
    """Get performance results comparing control vs experiment arms.

    Args:
        experiment_resource_name: Resource name of the experiment to check.

    Returns:
        dict: status and comparison metrics between control and experiment arms.
    """
    try:
        client = get_google_ads_client()
        customer_id = get_customer_id()
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                experiment.name,
                experiment.status,
                experiment_arm.name,
                experiment_arm.control,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.cost_per_conversion
            FROM experiment_arm
            WHERE experiment.resource_name = '{experiment_resource_name}'
        """

        response = ga_service.search_stream(
            customer_id=customer_id, query=query
        )

        arms = []
        for batch in response:
            for row in batch.results:
                arms.append({
                    "arm_name": row.experiment_arm.name,
                    "is_control": row.experiment_arm.control,
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "cost": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions,
                    "cost_per_conversion": row.metrics.cost_per_conversion / 1_000_000
                        if row.metrics.cost_per_conversion else 0,
                })

        return {
            "status": "success",
            "experiment_resource": experiment_resource_name,
            "arms": arms,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
