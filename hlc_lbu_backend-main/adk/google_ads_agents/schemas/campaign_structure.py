"""Pydantic schema for campaign structure produced by the strategy agent."""

from pydantic import BaseModel, Field


class KeywordEntry(BaseModel):
    text: str = Field(description="Keyword text")
    match_type: str = Field(description="BROAD, PHRASE, or EXACT")


class AdGroupPlan(BaseModel):
    name: str = Field(description="Ad group name")
    theme: str = Field(description="Theme/intent this ad group targets")
    keywords: list[KeywordEntry] = Field(description="Keywords for this ad group")
    cpc_bid: float = Field(description="Max CPC bid in USD")


class CampaignPlan(BaseModel):
    name: str = Field(description="Campaign name")
    daily_budget: float = Field(description="Daily budget in USD")
    bidding_strategy: str = Field(description="MAXIMIZE_CONVERSIONS, TARGET_CPA, MANUAL_CPC, etc.")
    bidding_target_value: float = Field(default=0.0, description="Target CPA or ROAS value if applicable")
    network: str = Field(default="SEARCH", description="SEARCH or SEARCH_WITH_DISPLAY_SELECT")
    geo_targets: list[str] = Field(description="Location targeting")
    ad_schedule: str = Field(default="all_day", description="Ad schedule")
    ad_groups: list[AdGroupPlan] = Field(description="Ad groups within this campaign")
    negative_keywords: list[str] = Field(default_factory=list, description="Campaign-level negatives")


class CampaignStructure(BaseModel):
    campaigns: list[CampaignPlan] = Field(description="List of campaigns to create")
    rationale: str = Field(description="Brief explanation of the campaign structure strategy")
