"""Pydantic schema for the structured campaign brief produced by the intake pipeline."""

from pydantic import BaseModel, Field


class TargetAudience(BaseModel):
    age_range: str = Field(description="Target age range, e.g. '25-45'")
    locations: list[str] = Field(description="Target geographic locations")
    pain_points: str = Field(description="Main problems the audience faces")
    demographics_notes: str = Field(default="", description="Additional demographic details")


class CampaignBrief(BaseModel):
    business_name: str = Field(description="Name of the business")
    product_description: str = Field(description="What the business sells or offers")
    website_url: str = Field(description="Landing page URL for ad traffic")
    competitors: list[str] = Field(description="Top 2-3 competitor names or URLs")
    target_audience: TargetAudience = Field(description="Ideal customer profile")
    primary_goal: str = Field(description="Main campaign goal: leads, sales, calls, or other")
    monthly_budget: float = Field(description="Monthly Google Ads budget in USD")
    cac_target: float = Field(description="Maximum cost per customer acquisition in USD")
    cpa_target: float = Field(description="Maximum cost per lead/action in USD")
    seed_keywords: list[str] = Field(description="Initial keywords the client suggests")
    negative_keywords: list[str] = Field(default_factory=list, description="Terms to exclude from targeting")
    geo_targets: list[str] = Field(description="Locations to target")
    geo_exclusions: list[str] = Field(default_factory=list, description="Locations to exclude")
    ad_schedule: str = Field(default="all_day", description="Days and hours for ads, e.g. 'weekdays 9am-6pm'")
    unique_selling_point: str = Field(description="Main USP for ad messaging")
    current_offers: str = Field(default="", description="Active promotions or offers")
    desired_action: str = Field(description="What user should do after clicking: form, call, buy")
