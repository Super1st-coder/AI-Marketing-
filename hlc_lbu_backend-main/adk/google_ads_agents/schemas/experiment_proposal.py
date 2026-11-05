"""Pydantic schema for experiment proposals."""

from pydantic import BaseModel, Field


class ExperimentProposal(BaseModel):
    hypothesis: str = Field(description="If we [change], then [expected outcome] because [reasoning]")
    test_type: str = Field(description="ad_copy, bidding, keyword, targeting, or landing_page")
    changes: list[str] = Field(description="Specific changes to implement in this experiment")
    duration_days: int = Field(default=14, description="How long to run the experiment")
    traffic_split_percent: int = Field(default=50, description="Percentage of traffic for experiment arm")
    success_metric: str = Field(description="Primary metric to measure success (CPA, CTR, conversion_rate)")
    risk_level: str = Field(description="low, medium, or high")
    expected_impact: str = Field(description="Expected improvement if hypothesis is correct")
    base_campaign_id: str = Field(default="", description="Campaign ID to base the experiment on")
