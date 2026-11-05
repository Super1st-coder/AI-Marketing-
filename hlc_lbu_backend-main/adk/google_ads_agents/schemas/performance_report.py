"""Pydantic schema for performance reports."""

from pydantic import BaseModel, Field


class CampaignMetrics(BaseModel):
    campaign_name: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    cpa: float = 0.0
    conversion_rate: float = 0.0


class KeywordMetrics(BaseModel):
    keyword: str
    match_type: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    ctr: float = 0.0
    avg_cpc: float = 0.0
    quality_score: int = 0


class PerformanceReport(BaseModel):
    date_range: str = Field(description="Report date range")
    total_spend: float = Field(default=0.0)
    total_conversions: float = Field(default=0.0)
    overall_cpa: float = Field(default=0.0)
    overall_ctr: float = Field(default=0.0)
    campaigns: list[CampaignMetrics] = Field(default_factory=list)
    top_keywords: list[KeywordMetrics] = Field(default_factory=list)
    issues_found: list[str] = Field(default_factory=list, description="Problems detected")
    recommendations: list[str] = Field(default_factory=list, description="Suggested actions")
